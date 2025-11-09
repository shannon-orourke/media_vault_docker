"""Chat session models for Azure OpenAI integration."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class ChatSession(Base):
    """AI chat session tracking."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_name = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())
    message_count = Column(Integer, default=0)
    context_summary = Column(Text, nullable=True)
    session_metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="chat_session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual chat messages with database context."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    database_context = Column(JSON, nullable=True)  # Query results injected into prompt
    context_query = Column(Text, nullable=True)  # SQL query that generated context
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    message_metadata = Column(JSON, nullable=True)

    # Relationships
    chat_session = relationship("ChatSession", back_populates="messages")
