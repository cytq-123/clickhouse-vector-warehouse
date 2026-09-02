"""
FastAPI 主应用入口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from loguru import logger
import sys

from .config import settings
from .search import router as search_router
from .health import router as health_router

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)

# 创建 FastAPI 应用
app = FastAPI(
    title="实时向量数仓 API",
    description="基于 ClickHouse 的低成本 RAG 数据基础设施",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, prefix="/api/v1", tags=["健康检查"])
app.include_router(search_router, prefix="/api/v1", tags=["搜索"])

# Prometheus 指标端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "内部服务器错误", "detail": str(exc)}
    )

@app.on_event("startup")
async def startup_event():
    logger.info("API 服务启动中...")
    logger.info(f"ClickHouse: {settings.clickhouse_host}:{settings.clickhouse_port}")
    logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")
    logger.info(f"Embedding 服务: {settings.embedding_service_url}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API 服务关闭中...")

@app.get("/")
async def root():
    return {
        "service": "实时向量数仓 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }