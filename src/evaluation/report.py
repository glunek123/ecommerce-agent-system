from datetime import datetime
from pathlib import Path
import json
from pydantic import BaseModel, Field
from .metrics import EvaluationMetrics


class TestResult(BaseModel):
    test_id: str
    success: bool
    actual_response: str
    actual_tools: list[str]
    response_time_ms: float
    error: str | None = None


class EvaluationReport(BaseModel):
    report_id: str
    dataset_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metrics: EvaluationMetrics
    test_results: list[TestResult] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    def save(self, output_dir: str | Path) -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / f"report_{self.report_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        return file_path

    def generate_recommendations(self) -> None:
        self.recommendations = []
        if self.metrics.accuracy < 0.8:
            self.recommendations.append("准确率较低，建议优化Prompt模板或增加Few-shot示例")
        if self.metrics.task_completion_rate < 0.9:
            self.recommendations.append("任务完成率不足，建议检查工具定义和错误处理逻辑")
        if self.metrics.avg_response_time_ms > 3000:
            self.recommendations.append("响应时间较长，建议优化工具调用或使用更快的模型")
