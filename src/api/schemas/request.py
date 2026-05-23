from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str
    context: dict[str, Any] | None = None


class SessionRequest(BaseModel):
    session_id: str
    user_id: str
