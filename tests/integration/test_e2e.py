"""集成测试：用 FastAPI TestClient 把 mock server 进程外起起来，对 chat / admin 路由做端到端断言。"""
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MOCK_PORT = 9099  # 用专属端口避免和开发环境冲突


@pytest.fixture(scope="module")
def mock_server():
    """起一个 mock server 子进程，测试结束后关闭。"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    proc = subprocess.Popen(
        [sys.executable, "-c", f"""
import uvicorn, sys
sys.path.insert(0, r'{PROJECT_ROOT}')
from scripts.mock_server import app
uvicorn.run(app, host='127.0.0.1', port={MOCK_PORT}, log_level='warning')
"""],
        env=env,
    )
    for _ in range(30):
        try:
            r = httpx.get(f"http://127.0.0.1:{MOCK_PORT}/inventory/query", params={"product_id": "P001"}, timeout=1)
            if r.status_code == 200:
                break
        except httpx.ConnectError:
            time.sleep(0.3)
    else:
        proc.terminate()
        pytest.fail("mock server 启动失败")
    yield f"http://127.0.0.1:{MOCK_PORT}"
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="module")
def api_client(mock_server, monkeypatch_module):
    """把 ECOMMERCE_API_URL 指向 mock server 起一个 TestClient。"""
    monkeypatch_module.setenv("ECOMMERCE_API_URL", mock_server)
    monkeypatch_module.setenv("ECOMMERCE_API_KEY", "mock-key")
    monkeypatch_module.setenv("LLM_API_KEY", "test-key")
    from src.config.settings import get_settings
    get_settings.cache_clear()
    from src.api.main import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def test_health(api_client):
    r = api_client.get("/health/")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_admin_tools_list(api_client):
    r = api_client.get("/api/v1/admin/tools")
    assert r.status_code == 200
    tools = r.json()["tools"]
    assert len(tools) == 9
    names = {t["name"] for t in tools}
    assert {"InventoryCheckTool", "OrderQueryTool", "CouponSendTool", "ProductSearchTool"} <= names


def test_admin_tools_by_category(api_client):
    r = api_client.get("/api/v1/admin/tools/inventory")
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == "inventory"
    assert len(data["tools"]) == 2


def test_mock_server_inventory(mock_server):
    """直接打 mock 验证端点正常。"""
    r = httpx.get(f"{mock_server}/inventory/query", params={"product_id": "P001"})
    assert r.status_code == 200
    data = r.json()
    assert data["product_id"] == "P001"
    assert data["stock"] > 0


def test_mock_server_order_detail(mock_server):
    r = httpx.get(f"{mock_server}/order/detail", params={"order_id": "ORD888"})
    assert r.status_code == 200
    data = r.json()
    assert data["order_id"] == "ORD888"
    assert "logistics" in data
