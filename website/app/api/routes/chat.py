from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from structlog.contextvars import bind_contextvars

from app.core.agent import AgentDep
from app.core.auth import CurrentUser
from app.db import SessionDep
from app.models import (
    Conversation,
    Document,
    Feedback,
    FeedbackRequest,
    Interaction,
    MessageRequest,
    MessageResponse,
)

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()


@router.post("/message/{conversation_id}", response_model=MessageResponse)
async def message(
    conversation_id: str,
    msg: MessageRequest,
    db: SessionDep,
    agent: AgentDep,
    user: CurrentUser,
):
    """
    Accepts a natural language question and returns an answer based on documents
    retrieved by the agent. Tracks which documents were actually used.
    """
    bind_contextvars(
        user_id=str(user.id),
        conversation_id=conversation_id,
        question_length=len(msg.question),
    )
    logger.debug("message endpoint called", question=msg.question[:100])

    conversation = await db.get(Conversation, conversation_id)
    logger.debug("conversation lookup", found=conversation is not None)

    if not conversation or conversation.user_id != user.id:
        bind_contextvars(access_denied=True)
        logger.debug("conversation not found or unauthorized")
        raise HTTPException(status_code=404, detail="Conversation not found")

    start_time = datetime.now()

    try:
        logger.debug("invoking agent", question=msg.question[:100])
        agent_response = await agent.ainvoke(msg.question, thread_id=conversation_id)
        logger.debug(
            "agent response received", answer_length=len(agent_response.answer)
        )
    except Exception as e:
        bind_contextvars(error_type=type(e).__name__, error_message=str(e))
        logger.debug("agent failed to process query", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Agent failed to process query: {e}"
        )

    end_time = datetime.now()
    response_time = (end_time - start_time).total_seconds()

    conversation.updated_at = datetime.utcnow()
    db.add(conversation)

    result = await db.execute(
        select(Document).where(Document.filename.in_(agent_response.used_documents))
    )
    used_documents = result.scalars().all()

    interaction = Interaction(
        checkpoint_id=agent_response.checkpoint_id,
        thread_id=conversation_id,
        response_time=response_time,
        documents=list(used_documents),
        timestamp=None,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    bind_contextvars(
        response_time_ms=round(response_time * 1000, 2),
        documents_used=[d.filename for d in used_documents],
        interaction_id=str(interaction.id),
        checkpoint_id=agent_response.checkpoint_id,
    )

    return MessageResponse(
        answer=agent_response.answer,
        interaction_id=interaction.id,
        source_documents=list(used_documents),
    )


@router.post("/feedback")
async def submit_feedback(
    feedback_req: FeedbackRequest, db: SessionDep, user: CurrentUser
):
    """
    Submits user feedback (thumbs up/down) for a specific interaction.
    """
    interaction = await db.get(Interaction, feedback_req.interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    # Query for existing feedback separately to avoid lazy-loading in async context
    result = await db.execute(
        select(Feedback).where(Feedback.interaction_id == feedback_req.interaction_id)
    )
    existing_feedback = result.scalar_one_or_none()

    if existing_feedback:
        existing_feedback.is_positive = feedback_req.is_positive
        db.add(existing_feedback)
        await db.commit()
        await db.refresh(existing_feedback)
        return Response(status_code=status.HTTP_200_OK)
    else:
        new_feedback = Feedback(
            interaction_id=feedback_req.interaction_id,
            is_positive=feedback_req.is_positive,
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)
        return Response(status_code=status.HTTP_201_CREATED)
