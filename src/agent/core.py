from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from ..config import get_settings
from ..memory import MemoryManager
from ..observability import get_logger, trace_agent_execution


class AgentConfig(BaseModel):
    max_iterations: int = Field(default=10)
    timeout_seconds: int = Field(default=60)
    temperature: float = Field(default=0.1)
    verbose: bool = Field(default=False)


SYSTEM_PROMPT = """你是一个专业的电商智能客服助手，名叫"小智"。

职责：帮助用户查找商品、查询库存、处理订单、发放优惠券、解答购物问题。

工具使用原则：
- 使用工具获取实时数据，不要编造库存、订单状态、价格
- 一旦工具返回了所需结果，立即用自然语言回复用户，**不要重复调用同一工具**
- 工具失败时友好告知用户，建议人工客服介入

回复风格：
- 称呼用户为"您"，热情友好
- 涉及金额时显示元/分换算清晰
- 整理结构化数据为简洁的中文描述"""


class EcommerceAgent:
    def __init__(self, session_id: str, user_id: str,
                 config: AgentConfig | None = None, tools: list[BaseTool] | None = None):
        self.session_id = session_id
        self.user_id = user_id
        self.config = config or AgentConfig()
        self.settings = get_settings()
        self.logger = get_logger()
        self.tools = tools or self._init_default_tools()
        self.memory_manager = MemoryManager(
            session_id=session_id, user_id=user_id,
            redis_url=None,
            max_token_limit=self.settings.memory_max_tokens
        )
        self._graph = None

    def _init_default_tools(self) -> list[BaseTool]:
        from ..tools import tool_registry
        import src.tools.inventory  # noqa
        import src.tools.order      # noqa
        import src.tools.coupon     # noqa
        import src.tools.product    # noqa
        return tool_registry.get_all_tools(
            ecommerce_api_url=self.settings.ecommerce_api_url,
            ecommerce_api_key=self.settings.ecommerce_api_key
        )

    def _get_graph(self):
        if self._graph is None:
            from langgraph.prebuilt import create_react_agent
            llm = ChatOpenAI(
                model=self.settings.llm_model_name,
                temperature=self.config.temperature,
                max_tokens=self.settings.llm_max_tokens,
                timeout=self.config.timeout_seconds,
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url
            )
            self._graph = create_react_agent(
                model=llm,
                tools=self.tools,
                prompt=SYSTEM_PROMPT
            )
        return self._graph

    def _build_messages(self, user_input: str) -> list:
        """从短期记忆 + 当前输入构造 LangGraph 消息列表（不重复加 system，因为 prompt 已注入）。"""
        msgs = []
        for m in self.memory_manager.short_term.get_messages():
            if isinstance(m, (HumanMessage, AIMessage)):
                msgs.append(m)
        msgs.append(HumanMessage(content=user_input))
        return msgs

    @trace_agent_execution
    async def chat(self, user_input: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self.memory_manager.add_user_message(user_input)
        try:
            graph = self._get_graph()
            result = await graph.ainvoke(
                {"messages": self._build_messages(user_input)},
                config={"recursion_limit": self.config.max_iterations * 2}
            )
            messages = result.get("messages", [])
            final_text = self._extract_final_text(messages)
            tool_calls = self._extract_tool_calls(messages)
            self.memory_manager.add_assistant_message(content=final_text, tool_calls=tool_calls)
            return {
                "success": True,
                "output": final_text,
                "tool_calls": tool_calls,
                "session_id": self.session_id
            }
        except Exception as e:
            self.logger.error("agent_execution_failed", session_id=self.session_id, error=str(e))
            return {
                "success": False,
                "output": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "error": str(e),
                "session_id": self.session_id
            }

    def _extract_final_text(self, messages: list) -> str:
        for m in reversed(messages):
            if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                return m.content if isinstance(m.content, str) else str(m.content)
        return ""

    def _extract_tool_calls(self, messages: list) -> list[dict]:
        """从 LangGraph 输出消息列表里提取工具调用。

        AIMessage 携带 tool_calls(list[{name,args,id}])，紧随其后会有 ToolMessage(tool_call_id, content)。
        """
        tool_msgs_by_id = {m.tool_call_id: m for m in messages if isinstance(m, ToolMessage)}
        out = []
        for m in messages:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    tool_id = tc.get("id")
                    observation = tool_msgs_by_id.get(tool_id)
                    out.append({
                        "tool": tc.get("name", "unknown"),
                        "input": tc.get("args", {}),
                        "output": str(observation.content) if observation else ""
                    })
        return out

    def clear_memory(self) -> None:
        self.memory_manager.clear_session()

    def close(self) -> None:
        self.memory_manager.close()

    async def chat_stream(self, user_input: str, context: dict[str, Any] | None = None):
        """流式输出。事件类型：tool_start / tool_end / final / error。"""
        self.memory_manager.add_user_message(user_input)
        try:
            graph = self._get_graph()
            final_text = ""
            collected_tool_calls: list[dict] = []
            pending_tool_calls: dict[str, dict] = {}  # id -> {tool, input}
            async for event in graph.astream_events(
                {"messages": self._build_messages(user_input)},
                version="v2",
                config={"recursion_limit": self.config.max_iterations * 2}
            ):
                kind = event.get("event")
                data = event.get("data", {})
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = data.get("input", {})
                    run_id = event.get("run_id")
                    pending_tool_calls[run_id] = {"tool": tool_name, "input": tool_input}
                    yield {"event": "tool_start", "tool": tool_name, "input": tool_input}
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = str(data.get("output", ""))
                    run_id = event.get("run_id")
                    started = pending_tool_calls.pop(run_id, {"tool": tool_name, "input": {}})
                    collected_tool_calls.append({**started, "output": output[:1000]})
                    yield {"event": "tool_end", "tool": tool_name, "output": output[:500]}
                elif kind == "on_chat_model_end":
                    msg = data.get("output")
                    if msg is not None and not getattr(msg, "tool_calls", None):
                        content = getattr(msg, "content", "")
                        if isinstance(content, str) and content:
                            final_text = content
            self.memory_manager.add_assistant_message(content=final_text, tool_calls=collected_tool_calls)
            yield {"event": "final", "output": final_text, "session_id": self.session_id}
        except Exception as e:
            self.logger.error("agent_stream_failed", session_id=self.session_id, error=str(e))
            yield {"event": "error", "error": str(e), "session_id": self.session_id}
