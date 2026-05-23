from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..observability import setup_logging, setup_metrics
from .routes import chat, admin, health, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    setup_metrics()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="电商智能Agent系统",
        description="基于LangChain的电商智能客服Agent系统",
        version="0.1.0",
        lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(health.router, prefix="/health", tags=["健康检查"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["对话接口"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["运营后台"])
    return app


app = create_app()
