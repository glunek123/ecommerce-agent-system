"""工具单元测试"""
import pytest
from unittest.mock import patch, Mock

from src.tools.inventory import InventoryCheckTool
from src.tools.order import OrderQueryTool
from src.tools import tool_registry


TOOL_CONFIG = {"ecommerce_api_url": "http://test-api", "ecommerce_api_key": "test-key"}


def test_inventory_check_tool_init():
    tool = InventoryCheckTool(**TOOL_CONFIG)
    assert tool.name == "inventory_check"
    assert "库存" in tool.description


@patch("httpx.Client")
def test_inventory_check_tool_run(mock_client):
    mock_resp = Mock()
    mock_resp.json.return_value = {"product_id": "P001", "stock": 100}
    mock_resp.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.get.return_value = mock_resp

    tool = InventoryCheckTool(**TOOL_CONFIG)
    result = tool._run(product_id="P001")
    assert "success" in result


def test_order_query_tool_init():
    tool = OrderQueryTool(**TOOL_CONFIG)
    assert tool.name == "order_query"


def test_tool_registry_has_all_tools():
    import src.tools.inventory  # noqa
    import src.tools.order      # noqa
    import src.tools.coupon     # noqa
    import src.tools.product    # noqa
    names = [t["name"] for t in tool_registry.list_tools()]
    assert "InventoryCheckTool" in names
    assert "OrderQueryTool" in names
