from pydantic import BaseModel, Field
from .base import BaseEcommerceTool, ToolResult
from .registry import tool_registry


class OrderQueryInput(BaseModel):
    order_id: str = Field(description="订单ID")
    user_id: str | None = Field(default=None)


class OrderQueryTool(BaseEcommerceTool):
    """订单查询工具。查询订单详情和状态。当用户提供订单号查询订单时使用。"""
    name: str = "order_query"
    description: str = "查询订单详情。参数：order_id(订单ID)，user_id(用户ID，可选)"
    args_schema: type[BaseModel] = OrderQueryInput

    def _execute(self, order_id: str, user_id: str | None = None) -> ToolResult:
        try:
            params = {"order_id": order_id}
            if user_id:
                params["user_id"] = user_id
            data = self._call_ecommerce_api("/order/detail", params=params)
            return ToolResult(success=True, data=data, message=f"订单{order_id}查询成功")
        except Exception as e:
            return ToolResult(success=False, message=f"订单查询失败: {e}", error_code="ORDER_QUERY_ERROR")


class OrderModifyInput(BaseModel):
    order_id: str = Field(description="订单ID")
    modification_type: str = Field(description="修改类型：address/quantity/item")
    modification_data: dict = Field(description="修改内容")


class OrderModifyTool(BaseEcommerceTool):
    """订单修改工具。修改订单信息（地址、数量、商品等）。"""
    name: str = "order_modify"
    description: str = "修改订单信息。参数：order_id, modification_type, modification_data"
    args_schema: type[BaseModel] = OrderModifyInput

    def _execute(self, order_id: str, modification_type: str, modification_data: dict) -> ToolResult:
        try:
            result = self._call_ecommerce_api("/order/modify", method="PUT", data={
                "order_id": order_id,
                "modification_type": modification_type,
                "modification_data": modification_data
            })
            return ToolResult(success=True, data=result, message=f"订单{order_id}修改成功")
        except Exception as e:
            return ToolResult(success=False, message=f"订单修改失败: {e}", error_code="ORDER_MODIFY_ERROR")


class OrderCancelInput(BaseModel):
    order_id: str = Field(description="订单ID")
    reason: str = Field(description="取消原因")


class OrderCancelTool(BaseEcommerceTool):
    """订单取消工具。取消订单并释放库存。"""
    name: str = "order_cancel"
    description: str = "取消订单。参数：order_id, reason"
    args_schema: type[BaseModel] = OrderCancelInput

    def _execute(self, order_id: str, reason: str) -> ToolResult:
        try:
            result = self._call_ecommerce_api("/order/cancel", method="POST",
                                              data={"order_id": order_id, "reason": reason})
            return ToolResult(success=True, data=result, message=f"订单{order_id}已取消")
        except Exception as e:
            return ToolResult(success=False, message=f"订单取消失败: {e}", error_code="ORDER_CANCEL_ERROR")


tool_registry.register(OrderQueryTool, category="order")
tool_registry.register(OrderModifyTool, category="order")
tool_registry.register(OrderCancelTool, category="order")
