"""
Embedding 服务客户端
"""
import httpx
from redis import Redis
from typing import List, Optional
import json
from loguru import logger

from .config import settings

class EmbeddingManager:
    """Embedding 生成和缓存管理"""
    
    def __init__(self):
        self.service_url = settings.embedding_service_url
        self.redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=False  # 存储二进制数据
        )
        self.cache_ttl = settings.embedding_cache_ttl
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的 embedding
        
        Args:
            text: 输入文本
        
        Returns:
            向量列表 (长度 1024)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.service_url}/embed",
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                return data["embedding"]
        
        except Exception as e:
            logger.error(f"获取 embedding 失败: {e}")
            raise
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取 embedding
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.service_url}/embed_batch",
                    json={"texts": texts}
                )
                response.raise_for_status()
                data = response.json()
                return data["embeddings"]
        
        except Exception as e:
            logger.error(f"批量获取 embedding 失败: {e}")
            raise
    
    async def get_cached_embedding(self, cache_key: str) -> Optional[List[float]]:
        """
        从 Redis 获取缓存的 embedding
        
        Args:
            cache_key: 缓存键（通常是 query 的 hash）
        
        Returns:
            向量列表，如果不存在返回 None
        """
        try:
            key = f"emb:{cache_key}"
            cached = self.redis_client.get(key)
            
            if cached:
                return json.loads(cached.decode('utf-8'))
            return None
        
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    async def cache_embedding(self, cache_key: str, embedding: List[float]):
        """
        缓存 embedding 到 Redis
        
        Args:
            cache_key: 缓存键
            embedding: 向量
        """
        try:
            key = f"emb:{cache_key}"
            self.redis_client.setex(
                key,
                self.cache_ttl,
                json.dumps(embedding)
            )
        
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    def clear_cache(self, pattern: str = "emb:*"):
        """
        清空缓存
        
        Args:
            pattern: 键匹配模式
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"已清空 {len(keys)} 个缓存")
        
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")