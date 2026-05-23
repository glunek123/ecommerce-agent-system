from datetime import datetime
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool: str
    input: dict
    output: str


class ChatResponse(BaseModel):
    success: bool
    session_id: str
    message: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionResponse(BaseModel):
    success: bool
    session_id: str
    message: str
