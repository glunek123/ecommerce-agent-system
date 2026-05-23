import functools
import time
from typing import Callable, Any

from .logger import get_logger
from .metrics import MetricsCollector


def trace_agent_execution(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs) -> Any:
        logger = get_logger()
        start_time = time.time()
        session_id = getattr(self, "session_id", "unknown")
        user_id = getattr(self, "user_id", "unknown")
        logger.info("agent_execution_started", session_id=session_id)
        try:
            result = await func(self, *args, **kwargs)
            duration = time.time() - start_time
            status = "success" if result.get("success", True) else "failed"
            MetricsCollector.record_request(session_id, user_id, status, duration)
            logger.info("agent_execution_completed", session_id=session_id,
                        status=status, duration_seconds=duration)
            return result
        except Exception as e:
            duration = time.time() - start_time
            MetricsCollector.record_request(session_id, user_id, "error", duration)
            logger.error("agent_execution_failed", session_id=session_id, error=str(e))
            raise
    return wrapper
