from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.auth import CurrentSuperuser
from app.db import SessionDep
from app.models import Document, Feedback, Interaction

router = APIRouter()


@router.get("/")
async def get_analytics(db: SessionDep, admin: CurrentSuperuser) -> dict[str, Any]:
    """
    Provides comprehensive analytics on document usage.
    """
    analytics_data = {}

    # 1. Which documents are queried most frequently?
    query_count = func.count(Interaction.id).label("query_count")
    result = await db.execute(
        select(Document.filename, query_count)
        .select_from(Document)
        .join(Document.interactions)
        .group_by(Document.filename)
        .order_by(query_count.desc())
    )
    document_query_counts = result.all()

    analytics_data["most_frequently_queried_documents"] = [
        {"filename": doc_name, "query_count": count}
        for doc_name, count in document_query_counts
    ]

    # 2. How many queries were answered from each PDF this week?
    seven_days_ago = datetime.now() - timedelta(days=7)
    weekly_query_count = func.count(Interaction.id).label("weekly_query_count")
    result = await db.execute(
        select(Document.filename, weekly_query_count)
        .select_from(Document)
        .join(Document.interactions)
        .where(Interaction.timestamp >= seven_days_ago)
        .group_by(Document.filename)
        .order_by(weekly_query_count.desc())
    )
    weekly_query_counts = result.all()

    analytics_data["weekly_queries_per_document"] = [
        {"filename": doc_name, "weekly_query_count": count}
        for doc_name, count in weekly_query_counts
    ]

    # 3. Average response time
    result = await db.execute(select(func.avg(Interaction.response_time)))
    avg_response_time = result.scalar_one_or_none()

    analytics_data["average_response_time_seconds"] = (
        round(avg_response_time, 3) if avg_response_time else 0
    )

    # 4. Feedback statistics
    result = await db.execute(
        select(
            func.count(Feedback.id).label("total_feedback"),
            func.count(Feedback.id)
            .filter(Feedback.is_positive)
            .label("positive_feedback"),
        )
    )
    feedbacks = result.one()
    total_feedback = feedbacks.total_feedback
    positive_feedback = feedbacks.positive_feedback

    analytics_data["feedback_statistics"] = {
        "total_feedback_count": total_feedback,
        "positive_feedback_count": positive_feedback,
        "negative_feedback_count": total_feedback - positive_feedback,
        "positive_feedback_percentage": (
            round((positive_feedback / total_feedback) * 100, 2)
            if total_feedback > 0
            else 0
        ),
    }

    # 5. Total interactions count
    result = await db.execute(select(func.count(Interaction.id)))
    total_interactions = result.scalar_one() or 0
    analytics_data["total_interactions"] = total_interactions

    return analytics_data


@router.get("/documents/unused")
async def get_unused_documents(
    db: SessionDep, admin: CurrentSuperuser
) -> list[dict[str, Any]]:
    """
    Find documents that have been uploaded but never used in any interaction.
    """
    result = await db.execute(select(Document).where(~Document.interactions.any()))
    unused_documents = result.scalars().all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in unused_documents
    ]
