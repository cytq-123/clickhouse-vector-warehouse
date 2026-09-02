"""
ClickHouse 客户端管理
"""
from clickhouse_driver import Client
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid
from datetime import datetime

from .config import settings

class ClickHouseManager:
    """ClickHouse 连接和查询管理"""
    
    def __init__(self):
        self.client = None
        self._connect()
    
    def _connect(self):
        """建立连接"""
        try:
            self.client = Client(
                host=settings.clickhouse_host,
                port=settings.clickhouse_port,
                user=settings.clickhouse_user,
                password=settings.clickhouse_password,
                database=settings.clickhouse_db
            )
            logger.info("ClickHouse 连接成功")
        except Exception as e:
            logger.error(f"ClickHouse 连接失败: {e}")
            raise
    
    def execute_query(self, sql: str, params: Optional[Dict] = None) -> List[tuple]:
        """
        执行查询
        
        Args:
            sql: SQL 语句
            params: 参数字典
        
        Returns:
            查询结果列表
        """
        try:
            if params:
                result = self.client.execute(sql, params)
            else:
                result = self.client.execute(sql)
            return result
        except Exception as e:
            logger.error(f"查询失败: {e}\nSQL: {sql}\nParams: {params}")
            raise
    
    def insert_documents(self, documents: List[Dict[str, Any]]):
        """
        批量插入文档
        
        Args:
            documents: 文档列表，每个文档包含字段:
                - doc_id, chunk_id, content, embedding, title, source_type, tags, etc.
        """
        try:
            sql = """
            INSERT INTO documents 
            (doc_id, chunk_id, content, embedding, title, author, source_type, tags, metadata)
            VALUES
            """
            
            self.client.execute(sql, documents)
            logger.info(f"成功插入 {len(documents)} 条文档")
        except Exception as e:
            logger.error(f"插入文档失败: {e}")
            raise
    
    def log_query(
        self,
        query_text: str,
        query_vector: List[float],
        filters: Dict,
        top_k: int,
        result_count: int,
        latency_ms: int,
        cache_hit: bool
    ):
        """
        记录查询日志
        """
        try:
            query_id = str(uuid.uuid4())
            sql = """
            INSERT INTO query_logs 
            (query_id, query_text, query_vector, filters, top_k, result_count, latency_ms, cache_hit, timestamp)
            VALUES (%(query_id)s, %(query_text)s, %(query_vector)s, %(filters)s, %(top_k)s, %(result_count)s, %(latency_ms)s, %(cache_hit)s, %(timestamp)s)
            """
            
            import json
            self.client.execute(sql, {
                "query_id": query_id,
                "query_text": query_text[:500],  # 限制长度
                "query_vector": query_vector,
                "filters": json.dumps(filters),
                "top_k": top_k,
                "result_count": result_count,
                "latency_ms": latency_ms,
                "cache_hit": 1 if cache_hit else 0,
                "timestamp": datetime.now()
            })
        except Exception as e:
            # 日志记录失败不应影响主流程
            logger.warning(f"记录查询日志失败: {e}")
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        根据 ID 查询文档
        """
        sql = """
        SELECT doc_id, chunk_id, title, content, author, tags, created_at, updated_at
        FROM documents
        WHERE doc_id = %(doc_id)s AND is_deleted = 0
        LIMIT 1
        """
        result = self.execute_query(sql, {"doc_id": doc_id})
        
        if result:
            row = result[0]
            return {
                "doc_id": row[0],
                "chunk_id": row[1],
                "title": row[2],
                "content": row[3],
                "author": row[4],
                "tags": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
        return None
    
    def delete_document(self, doc_id: str):
        """
        逻辑删除文档
        """
        sql = """
        ALTER TABLE documents UPDATE is_deleted = 1
        WHERE doc_id = %(doc_id)s
        """
        self.execute_query(sql, {"doc_id": doc_id})
        logger.info(f"文档已删除: {doc_id}")
    
    def __del__(self):
        """清理连接"""
        if self.client:
            self.client.disconnect()