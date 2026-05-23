from abc import abstractmethod
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangChainBaseTool

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    success: bool = Field(description="执行是否成功")
    data: T | None = Field(default=None)
    message: str = Field(description="结果消息")
    error_code: str | None = Field(default=None)

    model_config = {"arbitrary_types_allowed": True}


class BaseEcommerceTool(LangChainBaseTool):
    ecommerce_api_url: str
    ecommerce_api_key: str

    @abstractmethod
    def _execute(self, *args: Any, **kwargs: Any) -> ToolResult:
        pass

    def _run(self, *args: Any, **kwargs: Any) -> str:
        import structlog
        import json
        logger = structlog.get_logger()
        if args and not kwargs and isinstance(args[0], str):
            raw = args[0].strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    kwargs = parsed
                    args = ()
            except json.JSONDecodeError:
                pass
        try:
            logger.info("tool_execution_started", tool_name=self.name)
            result = self._execute(*args, **kwargs)
            logger.info("tool_execution_completed", tool_name=self.name, success=result.success)
            return result.model_dump_json()
        except Exception as e:
            logger.error("tool_execution_failed", tool_name=self.name, error=str(e))
            return ToolResult(
                success=False,
                message=f"工具执行失败: {str(e)}",
                error_code="TOOL_EXECUTION_ERROR"
            ).model_dump_json()

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)

    def _call_ecommerce_api(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict | None = None,
        data: dict | None = None
    ) -> dict:
        import httpx
        url = f"{self.ecommerce_api_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.ecommerce_api_key}",
            "Content-Type": "application/json"
        }
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            response.raise_for_status()
            return response.json()
