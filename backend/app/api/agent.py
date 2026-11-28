import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents.gemini_agent import GeminiAgent
from app.core.database import get_db
from app.models.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.agent import AgentChatRequest, AgentChatResponse


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["Agent"],
)


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
):
    profile = UserProfileRepository.get_by_id(
        db=db,
        profile_id=request.profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    conversation: Conversation | None = None

    if request.conversation_id is not None:
        conversation = ConversationRepository.get_by_id(
            db=db,
            conversation_id=request.conversation_id,
            profile_id=request.profile_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    else:
        conversation = ConversationRepository.create(
            db=db,
            profile_id=request.profile_id,
            title=request.message.strip()[:200],
        )

        # Commit the conversation first. ToolRegistry may rollback
        # its own failed database operation during agent execution.
        db.commit()
        db.refresh(conversation)

    try:
        result = GeminiAgent.run(
            message=request.message,
            profile_id=request.profile_id,
            db=db,
            conversation_id=conversation.id,
        )

        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()

        return AgentChatResponse(
            conversation_id=conversation.id,
            message=result["message"],
            tool_calls=result["tool_calls"],
            tool_results=result["tool_results"],
        )

    except Exception:
        db.rollback()
        logger.exception("Agent chat execution failed")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI agent could not complete the request.",
        )
