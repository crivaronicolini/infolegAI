import uuid
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy import select

from app.core.agent import AgentDep
from app.core.auth import CurrentUser
from app.db import SessionDep
from app.models import (
    Conversation,
    ConversationCreate,
    ConversationList,
    ConversationPublic,
    Feedback,
    Interaction,
)

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()


def _extract_ai_content(msg: AIMessage) -> str | None:
    """Extract text content from AIMessage, handling structured output formats."""
    # Direct text content
    if msg.text:
        return msg.text

    # Structured output: extract answer from tool_call blocks
    for block in msg.content_blocks:
        if block.get("type") == "tool_call":
            args = block.get("args", {})
            if isinstance(args, dict) and "answer" in args:
                return args["answer"]

    return None


@router.get("/", response_model=ConversationList)
async def list_conversations(db: SessionDep, user: CurrentUser):
    """List all conversations for the current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return ConversationList(
        conversations=[
            ConversationPublic(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.post("/", response_model=ConversationPublic)
async def create_conversation(
    db: SessionDep,
    user: CurrentUser,
    data: ConversationCreate | None = None,
):
    """Create a new conversation."""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title=data.title if data and data.title else "New Conversation",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationPublic(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationPublic)
async def get_conversation(
    conversation_id: str,
    db: SessionDep,
    user: CurrentUser,
):
    """Get a specific conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationPublic(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    db: SessionDep,
    user: CurrentUser,
    agent: AgentDep,
) -> list[dict[str, Any]]:
    """Get all messages in a conversation from the checkpointer."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await agent.get_history(conversation_id)

    # Get all interactions with their feedback for this conversation
    interactions_result = await db.execute(
        select(Interaction, Feedback)
        .outerjoin(Feedback, Interaction.id == Feedback.interaction_id)
        .where(Interaction.thread_id == conversation_id)
        .order_by(Interaction.timestamp)
    )
    interactions_with_feedback = list(interactions_result.all())
    interaction_idx = 0

    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            content = _extract_ai_content(msg)
            if content:
                # Match assistant messages with interactions by order
                interaction_id = None
                feedback = None
                if interaction_idx < len(interactions_with_feedback):
                    interaction, fb = interactions_with_feedback[interaction_idx]
                    interaction_id = interaction.id
                    if fb is not None:
                        feedback = fb.is_positive
                    interaction_idx += 1
                result.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "interactionId": interaction_id,
                        "feedback": feedback,
                    }
                )
        elif isinstance(msg, ToolMessage):
            continue

    return result


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: SessionDep,
    user: CurrentUser,
):
    """Delete a conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return {"message": "Conversation deleted"}


@router.patch("/{conversation_id}", response_model=ConversationPublic)
async def update_conversation(
    conversation_id: str,
    data: ConversationCreate,
    db: SessionDep,
    user: CurrentUser,
):
    """Update conversation title."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if data.title:
        conversation.title = data.title
        conversation.updated_at = datetime.utcnow()

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationPublic(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
