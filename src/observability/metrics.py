from prometheus_client import Counter, Histogram, Gauge, Info


class MetricsCollector:
    request_total = Counter(
        "agent_request_total", "Total agent requests", ["session_id", "user_id", "status"]
    )
    request_duration = Histogram(
        "agent_request_duration_seconds", "Agent request duration",
        ["session_id"], buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    )
    tool_call_total = Counter(
        "agent_tool_call_total", "Total tool calls", ["tool_name", "status"]
    )
    tool_duration = Histogram(
        "agent_tool_duration_seconds", "Tool execution duration",
        ["tool_name"], buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
    )
    active_sessions = Gauge("agent_active_sessions", "Active agent sessions")
    agent_info = Info("agent_info", "Agent system information")

    @classmethod
    def record_request(cls, session_id: str, user_id: str, status: str, duration: float) -> None:
        cls.request_total.labels(session_id=session_id, user_id=user_id, status=status).inc()
        cls.request_duration.labels(session_id=session_id).observe(duration)

    @classmethod
    def record_tool_call(cls, tool_name: str, status: str, duration: float) -> None:
        cls.tool_call_total.labels(tool_name=tool_name, status=status).inc()
        cls.tool_duration.labels(tool_name=tool_name).observe(duration)


def setup_metrics() -> None:
    MetricsCollector.agent_info.info({"version": "0.1.0", "framework": "langchain"})
