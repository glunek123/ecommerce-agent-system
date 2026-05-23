from pydantic import BaseModel, Field
from .base import BaseEcommerceTool, ToolResult
from .registry import tool_registry


class ProductSearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词")
    category: str | None = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class ProductSearchTool(BaseEcommerceTool):
    """商品搜索工具。搜索商品信息。当用户询问"有没有xxx"、"找xxx商品"时使用。"""
    name: str = "product_search"
    description: str = "搜索商品。参数：keyword, category(可选), page, page_size"
    args_schema: type[BaseModel] = ProductSearchInput

    def _execute(self, keyword: str, category: str | None = None,
                 page: int = 1, page_size: int = 10) -> ToolResult:
        try:
            params = {"keyword": keyword, "page": page, "page_size": page_size}
            if category:
                params["category"] = category
            data = self._call_ecommerce_api("/product/search", params=params)
            return ToolResult(success=True, data=data, message=f"搜索到{data.get('total', 0)}个相关商品")
        except Exception as e:
            return ToolResult(success=False, message=f"商品搜索失败: {e}", error_code="PRODUCT_SEARCH_ERROR")


class ProductDetailInput(BaseModel):
    product_id: str = Field(description="商品ID")


class ProductDetailTool(BaseEcommerceTool):
    """商品详情查询工具。查询商品详细信息（价格、规格、库存等）。"""
    name: str = "product_detail"
    description: str = "查询商品详情。参数：product_id"
    args_schema: type[BaseModel] = ProductDetailInput

    def _execute(self, product_id: str) -> ToolResult:
        try:
            data = self._call_ecommerce_api(f"/product/{product_id}")
            return ToolResult(success=True, data=data, message=f"商品{product_id}详情查询成功")
        except Exception as e:
            return ToolResult(success=False, message=f"商品详情查询失败: {e}", error_code="PRODUCT_DETAIL_ERROR")


tool_registry.register(ProductSearchTool, category="product")
tool_registry.register(ProductDetailTool, category="product")
