"""
配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ClickHouse 配置
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 9000
    clickhouse_user: str = "admin"
    clickhouse_password: str = "admin123"
    clickhouse_db: str = "vector_warehouse"
    
    # Redis 配置
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Embedding 服务配置
    embedding_service_url: str = "http://embedding-service:8001"
    embedding_cache_ttl: int = 3600  # 缓存 1 小时
    
    # API 配置
    api_key: Optional[str] = None  # 可选的 API Key 认证
    max_query_length: int = 1000
    default_top_k: int = 10
    max_top_k: int = 100
    
    # 日志配置
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()