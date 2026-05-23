"""JWT 鉴权测试"""
import pytest
from fastapi.testclient import TestClient

from src.api.middleware.auth import create_access_token, decode_token
from src.config.settings import get_settings


def test_token_roundtrip():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert "exp" in payload


def test_invalid_token_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.valid.jwt")
    assert exc.value.status_code == 401


def test_chat_endpoint_with_auth_disabled():
    """AUTH_ENABLED 默认关闭时，无 token 也能访问。"""
    get_settings.cache_clear()
    from src.api.main import create_app
    app = create_app()
    client = TestClient(app)
    r = client.get("/health/")
    assert r.status_code == 200


def test_chat_endpoint_with_auth_enabled(monkeypatch):
    """开启鉴权后，无 token 应当 401。"""
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-12345")
    get_settings.cache_clear()

    from src.api.main import create_app
    app = create_app()
    client = TestClient(app)

    r = client.post("/api/v1/chat/clear", json={"session_id": "s1", "user_id": "u1"})
    assert r.status_code == 401

    token = create_access_token("u1")
    r = client.post(
        "/api/v1/chat/clear",
        json={"session_id": "s1", "user_id": "u1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    get_settings.cache_clear()


def test_issue_token_endpoint():
    get_settings.cache_clear()
    from src.api.main import create_app
    app = create_app()
    client = TestClient(app)
    r = client.post("/api/v1/auth/token", json={"user_id": "u1"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    payload = decode_token(data["access_token"])
    assert payload["sub"] == "u1"
