import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from fastapi_users_db_sqlalchemy import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlmodel import TIMESTAMP, Column, Field, Relationship, SQLModel, text


class Base(DeclarativeBase):
    pass


# Share metadata between SQLAlchemy and SQLModel so foreign keys work
SQLModel.metadata = Base.metadata


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_account"

    if TYPE_CHECKING:
        user: "User"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )


class InteractionDocument(SQLModel, table=True):
    """
    Junction table to track which documents were used in each interaction.
    This allows multiple documents to be associated with a single interaction.
    """

    interaction_id: int = Field(foreign_key="interaction.id", primary_key=True)
    document_id: int = Field(foreign_key="document.id", primary_key=True)

    # # Track the relevance or order in which documents were used
    # relevance_score: float | None = None
    # usage_order: int | None = None

    # # Relationships
    # interaction: "Interaction" = Relationship(back_populates="documents")
    # document: "Document" = Relationship(back_populates="interactions")


# Document Models
class DocumentBase(SQLModel):
    filename: str = Field(unique=True, index=True)


class Document(DocumentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uploaded_at: datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    interactions: List["Interaction"] = Relationship(
        back_populates="documents", link_model=InteractionDocument
    )


class DocumentPublic(DocumentBase):
    id: int
    uploaded_at: datetime


# Feedback Models
class FeedbackBase(SQLModel):
    is_positive: bool


class Feedback(FeedbackBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    interaction_id: int | None = Field(default=None, foreign_key="interaction.id")
    interaction: Optional["Interaction"] = Relationship(back_populates="feedback")


class FeedbackCreate(FeedbackBase):
    interaction_id: int


class FeedbackPublic(FeedbackBase):
    id: int
    interaction_id: int


class FeedbackRequest(SQLModel):
    interaction_id: int
    is_positive: bool


# Interaction Models
class Interaction(SQLModel, table=True):
    """Links feedback and document usage to a LangGraph checkpoint."""

    id: int | None = Field(default=None, primary_key=True)
    checkpoint_id: str = Field(index=True, unique=True)
    thread_id: str = Field(index=True)
    response_time: float
    timestamp: datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )

    # Relationships
    documents: List["Document"] = Relationship(
        back_populates="interactions", link_model=InteractionDocument
    )
    feedback: Optional["Feedback"] = Relationship(back_populates="interaction")


class InteractionCreate(SQLModel):
    """Model for creating interactions with document references."""

    checkpoint_id: str
    thread_id: str
    response_time: float
    document_filenames: List[str] = Field(default_factory=list)


class InteractionPublic(SQLModel):
    """Public model for API responses."""

    id: int
    checkpoint_id: str
    thread_id: str
    timestamp: datetime
    response_time: float
    used_documents: List[str] = Field(default_factory=list)


# API Specific Models (not directly tied to a table)
class MessageRequest(SQLModel):
    question: str


class MessageResponse(SQLModel):
    answer: str
    interaction_id: int | None
    source_documents: List[DocumentPublic]


class UploadResponse(SQLModel):
    successful_uploads: List[DocumentPublic]
    failed_uploads: List[Dict[str, str]]


# Conversation Models (for chat threads with checkpointer)
class ConversationBase(SQLModel):
    title: str = Field(default="New Conversation")


class Conversation(ConversationBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationCreate(SQLModel):
    title: str | None = None


class ConversationPublic(ConversationBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ConversationList(SQLModel):
    conversations: List[ConversationPublic]
