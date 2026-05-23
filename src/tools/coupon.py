from pydantic import BaseModel, Field
from .base import BaseEcommerceTool, ToolResult
from .registry import tool_registry


class CouponSendInput(BaseModel):
    user_id: str = Field(description="用户ID")
    coupon_type: str = Field(description="优惠券类型")
    amount: int = Field(description="优惠金额（分）", ge=1)
    expire_days: int = Field(default=7, ge=1)
    reason: str = Field(description="发放原因")


class CouponSendTool(BaseEcommerceTool):
    """优惠券发放工具。向用户发放优惠券。当需要补偿用户或促销活动时使用。"""
    name: str = "coupon_send"
    description: str = "发放优惠券。参数：user_id, coupon_type, amount, expire_days, reason"
    args_schema: type[BaseModel] = CouponSendInput

    def _execute(self, user_id: str, coupon_type: str, amount: int,
                 expire_days: int = 7, reason: str = "") -> ToolResult:
        try:
            result = self._call_ecommerce_api("/coupon/send", method="POST", data={
                "user_id": user_id, "coupon_type": coupon_type,
                "amount": amount, "expire_days": expire_days, "reason": reason
            })
            return ToolResult(success=True, data=result, message=f"已向用户{user_id}发放{amount/100:.2f}元优惠券")
        except Exception as e:
            return ToolResult(success=False, message=f"优惠券发放失败: {e}", error_code="COUPON_SEND_ERROR")


class CouponQueryInput(BaseModel):
    user_id: str = Field(description="用户ID")
    status: str | None = Field(default=None, description="状态筛选：valid/used/expired")


class CouponQueryTool(BaseEcommerceTool):
    """优惠券查询工具。查询用户的优惠券列表。"""
    name: str = "coupon_query"
    description: str = "查询用户优惠券。参数：user_id, status(可选)"
    args_schema: type[BaseModel] = CouponQueryInput

    def _execute(self, user_id: str, status: str | None = None) -> ToolResult:
        try:
            params = {"user_id": user_id}
            if status:
                params["status"] = status
            data = self._call_ecommerce_api("/coupon/list", params=params)
            return ToolResult(success=True, data=data, message=f"用户{user_id}优惠券查询成功")
        except Exception as e:
            return ToolResult(success=False, message=f"优惠券查询失败: {e}", error_code="COUPON_QUERY_ERROR")


tool_registry.register(CouponSendTool, category="coupon")
tool_registry.register(CouponQueryTool, category="coupon")
