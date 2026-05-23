from pydantic import BaseModel, Field
from .base import BaseEcommerceTool, ToolResult
from .registry import tool_registry


class InventoryQueryInput(BaseModel):
    product_id: str = Field(description="商品ID")
    warehouse: str | None = Field(default=None, description="仓库ID")


class InventoryCheckTool(BaseEcommerceTool):
    """库存查询工具。查询指定商品在各仓库的库存情况。当用户询问"有没有货"、"库存多少"时使用。"""
    name: str = "inventory_check"
    description: str = "查询商品库存。参数：product_id(商品ID)，warehouse(仓库ID，可选)"
    args_schema: type[BaseModel] = InventoryQueryInput

    def _execute(self, product_id: str, warehouse: str | None = None) -> ToolResult:
        try:
            params = {"product_id": product_id}
            if warehouse:
                params["warehouse"] = warehouse
            data = self._call_ecommerce_api("/inventory/query", params=params)
            return ToolResult(success=True, data=data, message=f"商品{product_id}库存查询成功")
        except Exception as e:
            return ToolResult(success=False, message=f"库存查询失败: {e}", error_code="INVENTORY_QUERY_ERROR")


class InventoryReserveInput(BaseModel):
    product_id: str = Field(description="商品ID")
    quantity: int = Field(description="预留数量", ge=1)
    order_id: str = Field(description="关联订单ID")
    warehouse: str | None = Field(default=None)


class InventoryReserveTool(BaseEcommerceTool):
    """库存预留工具。为订单预留库存，防止超卖。"""
    name: str = "inventory_reserve"
    description: str = "预留商品库存。参数：product_id, quantity, order_id, warehouse(可选)"
    args_schema: type[BaseModel] = InventoryReserveInput

    def _execute(self, product_id: str, quantity: int, order_id: str, warehouse: str | None = None) -> ToolResult:
        try:
            data: dict = {"product_id": product_id, "quantity": quantity, "order_id": order_id}
            if warehouse:
                data["warehouse"] = warehouse
            result = self._call_ecommerce_api("/inventory/reserve", method="POST", data=data)
            return ToolResult(success=True, data=result, message=f"成功预留{quantity}件商品{product_id}")
        except Exception as e:
            return ToolResult(success=False, message=f"库存预留失败: {e}", error_code="INVENTORY_RESERVE_ERROR")


tool_registry.register(InventoryCheckTool, category="inventory")
tool_registry.register(InventoryReserveTool, category="inventory")
