from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import json
from ...agent import EcommerceAgent
from ...observability import get_logger
from ..middleware import require_auth
from ..schemas import ChatRequest, ChatResponse, SessionRequest, SessionResponse

router = APIRouter()
logger = get_logger()
_agent_cache: dict[str, EcommerceAgent] = {}


def get_agent(session_id: str, user_id: str) -> EcommerceAgent:
    key = f"{session_id}:{user_id}"
    if key not in _agent_cache:
        _agent_cache[key] = EcommerceAgent(session_id=session_id, user_id=user_id)
    return _agent_cache[key]


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, _user=Depends(require_auth)):
    try:
        agent = get_agent(request.session_id, request.user_id)
        result = await agent.chat(user_input=request.message, context=request.context)
        return ChatResponse(
            success=result["success"],
            session_id=result["session_id"],
            message=result["output"],
            tool_calls=[{"tool": tc["tool"], "input": tc["input"], "output": tc["output"]}
                        for tc in result.get("tool_calls", [])]
        )
    except Exception as e:
        logger.error("chat_request_failed", session_id=request.session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/clear", response_model=SessionResponse)
async def clear_session(request: SessionRequest, _user=Depends(require_auth)):
    key = f"{request.session_id}:{request.user_id}"
    if key in _agent_cache:
        _agent_cache[key].clear_memory()
    return SessionResponse(success=True, session_id=request.session_id, message="会话已清除")


@router.post("/stream")
async def chat_stream(request: ChatRequest, _user=Depends(require_auth)):
    """SSE 流式接口。客户端通过 EventSource / fetch streaming 消费。

    每行格式：`data: {JSON}\\n\\n`，事件类型见 `EcommerceAgent.chat_stream` 文档字符串。
    """
    agent = get_agent(request.session_id, request.user_id)

    async def event_generator():
        try:
            async for event in agent.chat_stream(request.message, request.context):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("chat_stream_failed", session_id=request.session_id, error=str(e))
            err = {"event": "error", "error": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
