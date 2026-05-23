from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any
from ...tools import tool_registry
from ...tools import inventory, order, coupon, product  # noqa: F401  触发工具注册
from ...observability import get_logger

router = APIRouter()
logger = get_logger()


@router.get("/tools")
async def list_tools():
    return {"tools": tool_registry.list_tools()}


@router.get("/tools/{category}")
async def list_tools_by_category(category: str):
    matched = [t for t in tool_registry.list_tools() if t["category"] == category]
    return {"category": category, "tools": matched}


@router.get("/metrics")
async def get_agent_metrics():
    return {
        "total_requests": 0,
        "success_rate": 1.0,
        "avg_latency_ms": 0,
        "tool_call_distribution": {}
    }
