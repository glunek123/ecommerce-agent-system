from typing import Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    steps: list[dict] = Field(default_factory=list)
    result: Any = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WorkingMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._tasks: dict[str, TaskInfo] = {}
        self._context: dict[str, Any] = {}

    def create_task(self, task_id: str, description: str) -> TaskInfo:
        task = TaskInfo(task_id=task_id, description=description)
        self._tasks[task_id] = task
        return task

    def update_task(self, task_id: str, status: TaskStatus | None = None,
                    step: dict | None = None, result: Any = None, error: str | None = None) -> TaskInfo:
        if task_id not in self._tasks:
            raise ValueError(f"任务不存在: {task_id}")
        task = self._tasks[task_id]
        if status:
            task.status = status
        if step:
            task.steps.append(step)
        if result is not None:
            task.result = result
        if error:
            task.error = error
        task.updated_at = datetime.now()
        return task

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[TaskInfo]:
        return list(self._tasks.values())

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def clear(self) -> None:
        self._tasks.clear()
        self._context.clear()
