"""
健康检查路由
"""
from fastapi import APIRouter
from clickhouse_driver import Client as ClickHouseClient
from redis import Redis
import httpx
from loguru import logger

from .config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    健康检查端点
    返回各个依赖服务的状态
    """
    status = {
        "api": "healthy",
        "clickhouse": {"status": "unknown", "details": None},
        "redis": {"status": "unknown", "details": None},
        "embedding_service": {"status": "unknown", "details": None}
    }
    
    # 检查 ClickHouse
    try:
        client = ClickHouseClient(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db
        )
        result = client.execute("SELECT 1")
        
        # 检查关键表是否存在
        tables = client.execute("""
            SELECT name FROM system.tables 
            WHERE database = 'vector_layer' AND name = 'semantic_product'
        """)
        
        vector_count = client.execute("SELECT count() FROM vector_layer.semantic_product")[0][0]
        
        status["clickhouse"] = {
            "status": "healthy" if result and tables else "unhealthy",
            "details": {
                "connection": "ok",
                "vector_table_exists": len(tables) > 0,
                "vector_products_count": vector_count
            }
        }
        client.disconnect()
    except Exception as e:
        logger.error(f"ClickHouse 健康检查失败: {e}")
        status["clickhouse"] = {"status": "unhealthy", "details": str(e)}
    
    # 检查 Redis
    try:
        redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        redis_client.ping()
        
        # 检查缓存统计
        info = redis_client.info("stats")
        cache_keys = len(redis_client.keys("emb:*"))
        
        status["redis"] = {
            "status": "healthy",
            "details": {
                "connection": "ok",
                "cached_embeddings": cache_keys,
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        }
    except Exception as e:
        logger.error(f"Redis 健康检查失败: {e}")
        status["redis"] = {"status": "unhealthy", "details": str(e)}
    
    # 检查 Embedding 服务
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.embedding_service_url}/health")
            
            if response.status_code == 200:
                # 测试 embedding 生成
                test_response = await client.post(
                    f"{settings.embedding_service_url}/embed",
                    json={"text": "测试"}
                )
                test_success = test_response.status_code == 200
                
                status["embedding_service"] = {
                    "status": "healthy" if test_success else "degraded",
                    "details": {
                        "connection": "ok",
                        "embed_test": "passed" if test_success else "failed"
                    }
                }
            else:
                status["embedding_service"] = {"status": "unhealthy", "details": "service unavailable"}
    except Exception as e:
        logger.error(f"Embedding 服务健康检查失败: {e}")
        status["embedding_service"] = {"status": "unhealthy", "details": str(e)}
    
    # 判断整体健康状态
    service_statuses = [v["status"] if isinstance(v, dict) else v for k, v in status.items() if k != "api"]
    overall_healthy = all(s == "healthy" for s in service_statuses)
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "services": status
    }

@router.get("/ready")
async def readiness_check():
    """
    就绪检查端点（用于 Kubernetes readiness probe）
    只检查是否能处理请求，不关心外部依赖
    """
    return {"status": "ready"}