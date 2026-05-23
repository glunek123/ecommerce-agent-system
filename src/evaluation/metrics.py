from typing import Any
from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    accuracy: float = Field(default=0.0, ge=0, le=1)
    task_completion_rate: float = Field(default=0.0, ge=0, le=1)
    task_success_rate: float = Field(default=0.0, ge=0, le=1)
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    tool_call_success_rate: float = Field(default=0.0, ge=0, le=1)
    avg_tool_calls_per_request: float = 0.0
    unnecessary_tool_calls_rate: float = Field(default=0.0, ge=0, le=1)
    user_satisfaction_score: float = Field(default=0.0, ge=0, le=5)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def get_summary(self) -> str:
        return (f"准确率: {self.accuracy:.2%} | 任务完成率: {self.task_completion_rate:.2%} | "
                f"平均响应: {self.avg_response_time_ms:.0f}ms | 满意度: {self.user_satisfaction_score:.1f}/5")
