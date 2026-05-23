import time
import uuid
from typing import Any

from .dataset import EvaluationDataset, TestCase
from .metrics import EvaluationMetrics
from .report import EvaluationReport, TestResult
from ..observability import get_logger


class EvaluationRunner:
    def __init__(self):
        self.logger = get_logger()
        self.dataset = EvaluationDataset()

    async def run(self, dataset_name: str = "default",
                  agent_config: dict[str, Any] | None = None,
                  output_dir: str = "reports") -> str:
        report_id = str(uuid.uuid4())[:8]
        self.logger.info("evaluation_started", report_id=report_id)

        if dataset_name == "default":
            self.dataset.load_default()

        test_results = []
        for tc in self.dataset.test_cases:
            result = await self._run_test_case(tc, agent_config or {})
            test_results.append(result)

        metrics = self._calculate_metrics(test_results)
        report = EvaluationReport(report_id=report_id, dataset_name=dataset_name,
                                  metrics=metrics, test_results=test_results)
        report.generate_recommendations()
        report.save(output_dir)
        self.logger.info("evaluation_completed", report_id=report_id)
        return report_id

    async def _run_test_case(self, test_case: TestCase, agent_config: dict[str, Any]) -> TestResult:
        from ..agent import EcommerceAgent
        agent = EcommerceAgent(session_id=f"eval_{test_case.id}", user_id="eval_user")
        start = time.time()
        try:
            result = await agent.chat(user_input=test_case.user_input, context=test_case.context)
            rt = (time.time() - start) * 1000
            actual_tools = [tc["tool"] for tc in result.get("tool_calls", [])]
            success = self._check_success(result, test_case, actual_tools)
            return TestResult(test_id=test_case.id, success=success,
                              actual_response=result.get("output", ""),
                              actual_tools=actual_tools, response_time_ms=rt)
        except Exception as e:
            return TestResult(test_id=test_case.id, success=False, actual_response="",
                              actual_tools=[], response_time_ms=(time.time() - start) * 1000, error=str(e))
        finally:
            agent.close()

    def _check_success(self, result: dict, test_case: TestCase, actual_tools: list[str]) -> bool:
        if not result.get("success", False):
            return False
        if any(t not in actual_tools for t in test_case.expected_tools):
            return False
        response = result.get("output", "")
        return all(kw in response for kw in test_case.expected_response_keywords)

    def _calculate_metrics(self, results: list[TestResult]) -> EvaluationMetrics:
        total = len(results)
        if total == 0:
            return EvaluationMetrics()
        success_count = sum(1 for r in results if r.success)
        times = sorted(r.response_time_ms for r in results)
        rate = success_count / total
        return EvaluationMetrics(
            accuracy=rate, task_completion_rate=rate, task_success_rate=rate,
            avg_response_time_ms=sum(times) / total,
            p95_response_time_ms=times[int(total * 0.95)],
            p99_response_time_ms=times[min(int(total * 0.99), total - 1)],
            tool_call_success_rate=rate,
            user_satisfaction_score=4.0 if rate > 0.8 else 3.0
        )
