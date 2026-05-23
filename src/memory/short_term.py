from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
import json


class ConversationBufferMemory:
    """简单的对话缓冲记忆，替代 langchain.memory.ConversationBufferMemory"""
    def __init__(self, memory_key: str = "chat_history", return_messages: bool = True):
        self.memory_key = memory_key
        self.return_messages = return_messages
        self.chat_memory = InMemoryChatMessageHistory()

    def clear(self) -> None:
        self.chat_memory.clear()


class ShortTermMemory:
    def __init__(self, session_id: str, redis_client=None, max_token_limit: int = 2000):
        self.session_id = session_id
        self.redis_client = redis_client
        self.max_token_limit = max_token_limit
        self._memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        if redis_client:
            self._load_from_redis()

    def add_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        if role == "user":
            self._memory.chat_memory.add_user_message(content)
        elif role == "assistant":
            self._memory.chat_memory.add_ai_message(content)
        if self.redis_client:
            self._save_to_redis({"role": role, "content": content,
                                 "timestamp": datetime.now().isoformat(), "metadata": metadata or {}})

    def get_messages(self) -> list[BaseMessage]:
        return self._memory.chat_memory.messages

    def get_context(self) -> str:
        parts = []
        for msg in self.get_messages():
            if isinstance(msg, HumanMessage):
                parts.append(f"用户: {msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"助手: {msg.content}")
        return "\n".join(parts)

    def clear(self) -> None:
        self._memory.clear()
        if self.redis_client:
            self.redis_client.delete(f"memory:short:{self.session_id}")

    def _save_to_redis(self, message_data: dict) -> None:
        key = f"memory:short:{self.session_id}"
        self.redis_client.rpush(key, json.dumps(message_data, ensure_ascii=False))
        self.redis_client.expire(key, 3600 * 24)

    def _load_from_redis(self) -> None:
        for msg_json in self.redis_client.lrange(f"memory:short:{self.session_id}", 0, -1):
            msg = json.loads(msg_json)
            if msg["role"] == "user":
                self._memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                self._memory.chat_memory.add_ai_message(msg["content"])

    def to_langchain_memory(self) -> ConversationBufferMemory:
        return self._memory
