from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class AgentToolCall(BaseModel):
    id: str | None = None
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentToolResult(BaseModel):
    id: str | None = None
    name: str
    success: bool
    result: Any = None
    error: str | None = None


class AgentChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    tool_results: list[AgentToolResult] = Field(default_factory=list)
