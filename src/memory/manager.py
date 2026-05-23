from typing import Any
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .working import WorkingMemory


class MemoryManager:
    def __init__(self, session_id: str, user_id: str,
                 redis_url: str | None = None, max_token_limit: int = 2000):
        self.session_id = session_id
        self.user_id = user_id
        self.redis_client = None
        if redis_url:
            import redis
            self.redis_client = redis.from_url(redis_url)
        self.short_term = ShortTermMemory(session_id, self.redis_client, max_token_limit)
        self.long_term = LongTermMemory(user_id, self.redis_client)
        self.working = WorkingMemory(session_id)

    def add_user_message(self, content: str) -> None:
        self.short_term.add_message("user", content)
        self.long_term.add_interaction({"type": "user_message", "content": content})

    def add_assistant_message(self, content: str, tool_calls: list | None = None) -> None:
        self.short_term.add_message("assistant", content,
                                    {"tool_calls": tool_calls} if tool_calls else None)

    def get_context_for_agent(self) -> dict[str, Any]:
        return {
            "chat_history": self.short_term.get_context(),
            "user_preferences": self.long_term.profile.preferences,
            "recent_interactions": self.long_term.get_recent_interactions(5),
            "current_tasks": self.working.get_all_tasks()
        }

    def clear_session(self) -> None:
        self.short_term.clear()
        self.working.clear()

    def close(self) -> None:
        if self.redis_client:
            self.redis_client.close()
