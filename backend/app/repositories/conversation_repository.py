from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import (
    Conversation,
    ConversationMessage,
)


class ConversationRepository:

    @staticmethod
    def create(
        db: Session,
        profile_id: int,
        title: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            profile_id=profile_id,
            title=title,
        )

        db.add(conversation)
        db.flush()

        return conversation

    @staticmethod
    def get_by_id(
        db: Session,
        conversation_id: UUID,
        profile_id: int,
    ) -> Conversation | None:
        statement = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.profile_id == profile_id,
        )

        return db.scalar(statement)

    @staticmethod
    def get_messages(
        db: Session,
        conversation_id: UUID,
    ) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation_id
            )
            .order_by(ConversationMessage.id.asc())
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def add_message(
        db: Session,
        conversation_id: UUID,
        role: str,
        content: str | None = None,
        gemini_payload: dict | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            gemini_payload=gemini_payload,
        )

        db.add(message)
        db.flush()

        return message
