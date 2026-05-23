from typing import Any

from .planner import TaskPlan, SubTask
from ..memory import WorkingMemory
from ..observability import get_logger


class TaskExecutor:
    def __init__(self, working_memory: WorkingMemory, max_workers: int = 3):
        self.working_memory = working_memory
        self.max_workers = max_workers
        self.logger = get_logger()

    async def execute_plan(self, plan: TaskPlan, context: dict[str, Any] | None = None) -> dict[str, Any]:
        results: dict[str, Any] = {}
        context = context or {}
        for task in sorted(plan.subtasks, key=lambda t: t.priority):
            if not self._check_dependencies(task, results):
                self.logger.warning("task_dependencies_not_met", task=task.description)
                continue
            task_result = await self._execute_task(task, context, results)
            results[task.description] = task_result
        return {
            "plan": plan.original_request,
            "results": results,
            "success": all(r["status"] == "completed" for r in results.values())
        }

    async def _execute_task(self, task: SubTask, context: dict[str, Any],
                            previous_results: dict[str, Any]) -> dict[str, Any]:
        if not task.tool_name:
            return {"status": "skipped", "message": "无工具指定"}
        try:
            from ..tools import tool_registry
            tool = tool_registry.get_tool(task.tool_name)
            params = self._resolve_references({**task.parameters, **context}, previous_results)
            result = await tool._arun(**params)
            return {"status": "completed", "result": result}
        except Exception as e:
            self.logger.error("task_execution_failed", task=task.description, error=str(e))
            return {"status": "failed", "error": str(e)}

    def _check_dependencies(self, task: SubTask, completed: dict[str, Any]) -> bool:
        return all(
            dep in completed and completed[dep]["status"] == "completed"
            for dep in task.dependencies
        )

    def _resolve_references(self, params: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
        return {
            k: previous.get(v[1:], {}).get("result") if isinstance(v, str) and v.startswith("$") else v
            for k, v in params.items()
        }
