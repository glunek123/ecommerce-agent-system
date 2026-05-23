from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field
import json


class UserProfile(BaseModel):
    user_id: str
    preferences: dict[str, Any] = Field(default_factory=dict)
    interaction_history: list[dict] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    model_config = {"arbitrary_types_allowed": True}


class LongTermMemory:
    def __init__(self, user_id: str, redis_client=None):
        self.user_id = user_id
        self.redis_client = redis_client
        self._profile: UserProfile | None = None
        if redis_client:
            self._load_profile()

    @property
    def profile(self) -> UserProfile:
        if self._profile is None:
            self._profile = UserProfile(user_id=self.user_id)
        return self._profile

    def update_preference(self, key: str, value: Any) -> None:
        self.profile.preferences[key] = value
        self.profile.last_updated = datetime.now()
        self._save_profile()

    def add_interaction(self, interaction: dict) -> None:
        interaction["timestamp"] = datetime.now().isoformat()
        self.profile.interaction_history.append(interaction)
        if len(self.profile.interaction_history) > 100:
            self.profile.interaction_history = self.profile.interaction_history[-100:]
        self._save_profile()

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.profile.preferences.get(key, default)

    def get_recent_interactions(self, limit: int = 10) -> list[dict]:
        return self.profile.interaction_history[-limit:]

    def _save_profile(self) -> None:
        if self.redis_client:
            self.redis_client.set(
                f"memory:long:profile:{self.user_id}",
                self.profile.model_dump_json(),
                ex=3600 * 24 * 30
            )

    def _load_profile(self) -> None:
        data = self.redis_client.get(f"memory:long:profile:{self.user_id}")
        if data:
            self._profile = UserProfile.model_validate_json(data)
