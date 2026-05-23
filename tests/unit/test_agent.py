"""Agent单元测试"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from langchain_core.messages import AIMessage, HumanMessage

from src.agent import EcommerceAgent, AgentConfig


@pytest.fixture
def agent():
    return EcommerceAgent(session_id="test-session", user_id="test-user")


def test_agent_init(agent):
    assert agent.session_id == "test-session"
    assert agent.user_id == "test-user"
    assert len(agent.tools) == 9


@pytest.mark.asyncio
async def test_agent_chat_success(agent):
    with patch.object(agent, "_get_graph") as mock_graph:
        graph = Mock()
        graph.ainvoke = AsyncMock(return_value={
            "messages": [
                HumanMessage(content="你好"),
                AIMessage(content="测试回复")
            ]
        })
        mock_graph.return_value = graph
        result = await agent.chat("你好")
        assert result["success"] is True
        assert result["output"] == "测试回复"
        assert result["session_id"] == "test-session"


@pytest.mark.asyncio
async def test_agent_chat_error(agent):
    with patch.object(agent, "_get_graph") as mock_graph:
        graph = Mock()
        graph.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
        mock_graph.return_value = graph
        result = await agent.chat("你好")
        assert result["success"] is False
        assert "error" in result


def test_agent_clear_memory(agent):
    agent.memory_manager.add_user_message("test")
    agent.clear_memory()
    assert len(agent.memory_manager.short_term.get_messages()) == 0


def test_extract_tool_calls():
    """新的 _extract_tool_calls 解析 LangGraph 消息列表"""
    from langchain_core.messages import ToolMessage
    agent = EcommerceAgent(session_id="t", user_id="u")
    messages = [
        HumanMessage(content="查库存"),
        AIMessage(
            content="",
            tool_calls=[{"id": "call_1", "name": "inventory_check", "args": {"product_id": "P001"}}]
        ),
        ToolMessage(content='{"success":true,"stock":128}', tool_call_id="call_1"),
        AIMessage(content="库存128件")
    ]
    tool_calls = agent._extract_tool_calls(messages)
    assert len(tool_calls) == 1
    assert tool_calls[0]["tool"] == "inventory_check"
    assert tool_calls[0]["input"] == {"product_id": "P001"}
    assert "128" in tool_calls[0]["output"]
