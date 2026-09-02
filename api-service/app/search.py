"""
搜索路由和核心检索逻辑
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import hashlib
import time
from loguru import logger

from .clickhouse_client import ClickHouseManager
from .embedding_client import EmbeddingManager
from .config import settings

router = APIRouter()

# 全局管理器实例
ch_manager = ClickHouseManager()
emb_manager = EmbeddingManager()

# ==================== 请求/响应模型 ====================

class DocumentCreate(BaseModel):
    """创建文档请求"""
    doc_id: str = Field(..., description="文档唯一标识")
    content: str = Field(..., description="文档内容", min_length=1)
    title: str = Field(..., description="文档标题")
    source_type: str = Field("manual", description="数据源类型: wiki/log/chat/api/manual")
    tags: List[str] = Field(default_factory=list, description="业务标签列表")
    author: str = Field("system", description="作者")

class DocumentResponse(BaseModel):
    """文档响应"""
    doc_id: str
    chunk_id: str
    status: str
    message: str

class SearchFilters(BaseModel):
    """搜索过滤条件"""
    source_type: Optional[str] = Field(None, description="数据源类型: wiki/log/chat/api")
    tags: Optional[List[str]] = Field(None, description="业务标签列表")
    date_range: Optional[List[str]] = Field(None, description="时间范围 [start, end]")
    author: Optional[str] = Field(None, description="作者")

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本", min_length=1, max_length=1000)
    filters: Optional[SearchFilters] = Field(None, description="过滤条件")
    top_k: int = Field(10, description="返回结果数", ge=1, le=100)
    use_cache: bool = Field(True, description="是否使用缓存")
    rerank: bool = Field(False, description="是否重排序")

class SearchResult(BaseModel):
    """单条搜索结果"""
    doc_id: str
    chunk_id: str
    title: str
    content: str
    author: str
    tags: List[str]
    created_at: str
    similarity_score: float = Field(..., description="相似度分数 (0-1，越高越相似)")

class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    total: int
    results: List[SearchResult]
    latency_ms: int
    cache_hit: bool

# ==================== API 端点 ====================

@router.post("/documents", response_model=DocumentResponse)
async def create_document(doc: DocumentCreate):
    """
    插入文档 API
    
    自动生成 embedding 并存入 ClickHouse
    """
    try:
        # 1. 生成 embedding
        embedding = await emb_manager.get_embedding(doc.content)
        
        # 2. 生成 chunk_id（简化版：单文档单分块）
        chunk_id = f"{doc.doc_id}_chunk_0"
        
        # 3. 插入到 ClickHouse
        insert_sql = """
            INSERT INTO vector_warehouse.documents 
            (doc_id, chunk_id, content, embedding, title, source_type, tags, author, created_at, is_deleted)
            VALUES
        """
        
        ch_manager.client.execute(
            insert_sql,
            [{
                'doc_id': doc.doc_id,
                'chunk_id': chunk_id,
                'content': doc.content,
                'embedding': embedding,
                'title': doc.title,
                'source_type': doc.source_type,
                'tags': doc.tags,
                'author': doc.author,
                'created_at': datetime.now(),
                'is_deleted': 0
            }]
        )
        
        logger.info(f"文档插入成功: doc_id={doc.doc_id}, chunk_id={chunk_id}")
        
        return DocumentResponse(
            doc_id=doc.doc_id,
            chunk_id=chunk_id,
            status="success",
            message="文档插入成功"
        )
    
    except Exception as e:
        logger.error(f"文档插入失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档插入失败: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    向量检索 API
    
    支持：
    - 纯向量检索
    - 混合查询（向量 + 过滤条件）
    - 缓存加速
    - 重排序
    """
    start_time = time.time()
    cache_hit = False
    
    try:
        # 1. 查询 embedding 缓存
        query_hash = hashlib.md5(request.query.encode()).hexdigest()
        query_vector = None
        
        if request.use_cache:
            query_vector = await emb_manager.get_cached_embedding(query_hash)
            if query_vector:
                cache_hit = True
                logger.info(f"缓存命中: {query_hash[:8]}")
        
        # 2. 生成 embedding
        if not query_vector:
            query_vector = await emb_manager.get_embedding(request.query)
            if request.use_cache:
                await emb_manager.cache_embedding(query_hash, query_vector)
        
        # 3. 构建 ClickHouse 查询
        sql, params = _build_search_query(
            query_vector=query_vector,
            filters=request.filters,
            top_k=request.top_k * 2 if request.rerank else request.top_k
        )
        
        # 4. 执行查询
        results = ch_manager.execute_query(sql, params)
        
        # 5. 重排序（可选）
        if request.rerank and results:
            results = await _rerank_results(request.query, results)
            results = results[:request.top_k]
        
        # 6. 格式化响应
        formatted_results = [
            SearchResult(
                doc_id=row[0],
                chunk_id=row[1],
                title=row[2],
                content=row[3],
                author=row[4],
                tags=row[5],
                created_at=row[6].isoformat(),
                similarity_score=1.0 - row[7]  # cosine distance 转换为 similarity
            )
            for row in results
        ]
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 7. 记录查询日志
        ch_manager.log_query(
            query_text=request.query,
            query_vector=query_vector,
            filters=request.filters.model_dump() if request.filters else {},
            top_k=request.top_k,
            result_count=len(formatted_results),
            latency_ms=latency_ms,
            cache_hit=cache_hit
        )
        
        logger.info(f"查询完成: query='{request.query[:30]}...', results={len(formatted_results)}, latency={latency_ms}ms, cache_hit={cache_hit}")
        
        return SearchResponse(
            query=request.query,
            total=len(formatted_results),
            results=formatted_results,
            latency_ms=latency_ms,
            cache_hit=cache_hit
        )
    
    except Exception as e:
        logger.error(f"搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

def _build_search_query(
    query_vector: List[float],
    filters: Optional[SearchFilters],
    top_k: int
) -> tuple[str, dict]:
    """
    构建 ClickHouse 搜索 SQL
    """
    # 基础查询
    sql_parts = [
        "SELECT",
        "    doc_id,",
        "    chunk_id,",
        "    title,",
        "    content,",
        "    author,",
        "    tags,",
        "    created_at,",
        "    cosineDistance(embedding, %(query_vec)s) AS distance",
        "FROM documents",
        "WHERE is_deleted = 0"
    ]
    
    params = {"query_vec": query_vector}
    
    # 添加过滤条件
    if filters:
        if filters.source_type:
            sql_parts.append("AND source_type = %(source_type)s")
            params["source_type"] = filters.source_type
        
        if filters.tags:
            sql_parts.append("AND hasAny(tags, %(tags)s)")
            params["tags"] = filters.tags
        
        if filters.date_range and len(filters.date_range) == 2:
            sql_parts.append("AND created_at BETWEEN %(start_date)s AND %(end_date)s")
            params["start_date"] = filters.date_range[0]
            params["end_date"] = filters.date_range[1]
        
        if filters.author:
            sql_parts.append("AND author = %(author)s")
            params["author"] = filters.author
    
    # 排序和限制
    sql_parts.extend([
        "ORDER BY distance ASC",
        f"LIMIT {top_k}"
    ])
    
    sql = "\n".join(sql_parts)
    return sql, params

async def _rerank_results(query: str, results: List[tuple]) -> List[tuple]:
    """
    使用重排序模型提升准确率
    TODO: 集成 bge-reranker 或其他重排序模型
    """
    # 当前版本：简单按相似度排序
    # 未来版本：调用专门的重排序服务
    return sorted(results, key=lambda x: x[7])  # 按 distance 排序

# ==================== 商品语义搜索 ====================

class ProductSearchFilters(BaseModel):
    """商品搜索过滤条件"""
    category_1: Optional[str] = Field(None, description="一级类目")
    category_2: Optional[str] = Field(None, description="二级类目")
    brand: Optional[str] = Field(None, description="品牌")
    price_range: Optional[Tuple[float, float]] = Field(None, description="价格范围 (min, max)")
    min_price: Optional[float] = Field(None, description="最低价格")
    max_price: Optional[float] = Field(None, description="最高价格")

class ProductSearchRequest(BaseModel):
    """商品搜索请求"""
    query: str = Field(..., description="搜索文本", min_length=1, max_length=500)
    filters: Optional[ProductSearchFilters] = Field(None, description="过滤条件")
    top_k: int = Field(10, description="返回结果数", ge=1, le=50)
    search_mode: str = Field("vector", description="搜索模式: vector/keyword/hybrid")
    use_cache: bool = Field(True, description="是否使用缓存")

class ProductSearchResult(BaseModel):
    """商品搜索结果"""
    product_id: int
    product_name: str
    description: str
    category_1: str
    category_2: str
    brand: str
    price: float
    similarity_score: float = Field(..., description="相似度分数 (0-1，越高越相似)")
    match_reason: str = Field(..., description="匹配原因：vector/keyword/hybrid")

class ProductSearchResponse(BaseModel):
    """商品搜索响应"""
    query: str
    total: int
    results: List[ProductSearchResult]
    latency_ms: int
    cache_hit: bool
    search_mode: str

@router.post("/products/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """
    商品语义搜索 API
    
    支持三种模式：
    - vector: 纯向量检索（语义相似）
    - keyword: 关键词检索（文本匹配）
    - hybrid: 混合检索（向量 + 关键词加权融合）
    """
    start_time = time.time()
    cache_hit = False
    
    try:
        if request.search_mode == "vector":
            results, cache_hit = await _vector_search_products(request)
        elif request.search_mode == "keyword":
            results = await _keyword_search_products(request)
        elif request.search_mode == "hybrid":
            results, cache_hit = await _hybrid_search_products(request)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的搜索模式: {request.search_mode}")
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"商品搜索完成: query='{request.query}', mode={request.search_mode}, results={len(results)}, latency={latency_ms}ms")
        
        return ProductSearchResponse(
            query=request.query,
            total=len(results),
            results=results,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            search_mode=request.search_mode
        )
    
    except Exception as e:
        logger.error(f"商品搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"商品搜索失败: {str(e)}")

async def _vector_search_products(request: ProductSearchRequest) -> Tuple[List[ProductSearchResult], bool]:
    """纯向量检索"""
    cache_hit = False
    
    # 1. 获取 query embedding
    query_hash = hashlib.md5(request.query.encode()).hexdigest()
    query_vector = None
    
    if request.use_cache:
        query_vector = await emb_manager.get_cached_embedding(query_hash)
        if query_vector:
            cache_hit = True
    
    if not query_vector:
        query_vector = await emb_manager.get_embedding(request.query)
        if request.use_cache:
            await emb_manager.cache_embedding(query_hash, query_vector)
    
    # 2. 构建查询
    sql_parts = [
        "SELECT",
        "    product_id,",
        "    product_name,",
        "    description,",
        "    category_1,",
        "    category_2,",
        "    brand,",
        "    price,",
        "    cosineDistance(embedding, %(query_vec)s) AS distance",
        "FROM vector_layer.semantic_product",
        "WHERE 1=1"
    ]
    
    params = {"query_vec": query_vector}
    
    # 添加过滤条件
    if request.filters:
        if request.filters.category_1:
            sql_parts.append("AND category_1 = %(category_1)s")
            params["category_1"] = request.filters.category_1
        
        if request.filters.category_2:
            sql_parts.append("AND category_2 = %(category_2)s")
            params["category_2"] = request.filters.category_2
        
        if request.filters.brand:
            sql_parts.append("AND brand = %(brand)s")
            params["brand"] = request.filters.brand
        
        if request.filters.min_price is not None:
            sql_parts.append("AND price >= %(min_price)s")
            params["min_price"] = request.filters.min_price
        
        if request.filters.max_price is not None:
            sql_parts.append("AND price <= %(max_price)s")
            params["max_price"] = request.filters.max_price
    
    sql_parts.extend([
        "ORDER BY distance ASC",
        f"LIMIT {request.top_k}"
    ])
    
    sql = "\n".join(sql_parts)
    
    # 3. 执行查询
    rows = ch_manager.execute_query(sql, params)
    
    # 4. 格式化结果
    results = [
        ProductSearchResult(
            product_id=row[0],
            product_name=row[1],
            description=row[2],
            category_1=row[3],
            category_2=row[4],
            brand=row[5],
            price=float(row[6]),
            similarity_score=1.0 - row[7],  # distance 转为 similarity
            match_reason="vector"
        )
        for row in rows
    ]
    
    return results, cache_hit

async def _keyword_search_products(request: ProductSearchRequest) -> List[ProductSearchResult]:
    """关键词检索（基于 ClickHouse 全文索引）"""
    sql_parts = [
        "SELECT",
        "    product_id,",
        "    product_name,",
        "    description,",
        "    category_1,",
        "    category_2,",
        "    brand,",
        "    price,",
        "    multiSearchAllPositionsCaseInsensitive(concat(product_name, ' ', description), %(keywords)s) AS positions",
        "FROM vector_layer.semantic_product",
        "WHERE (positionCaseInsensitive(product_name, %(query)s) > 0",
        "   OR positionCaseInsensitive(description, %(query)s) > 0)"
    ]
    
    params = {
        "query": request.query,
        "keywords": request.query.split()
    }
    
    # 添加过滤条件
    if request.filters:
        if request.filters.category_1:
            sql_parts.append("AND category_1 = %(category_1)s")
            params["category_1"] = request.filters.category_1
        
        if request.filters.brand:
            sql_parts.append("AND brand = %(brand)s")
            params["brand"] = request.filters.brand
        
        if request.filters.min_price is not None:
            sql_parts.append("AND price >= %(min_price)s")
            params["min_price"] = request.filters.min_price
        
        if request.filters.max_price is not None:
            sql_parts.append("AND price <= %(max_price)s")
            params["max_price"] = request.filters.max_price
    
    sql_parts.append(f"ORDER BY length(positions) DESC LIMIT {request.top_k}")
    
    sql = "\n".join(sql_parts)
    rows = ch_manager.execute_query(sql, params)
    
    # 格式化结果（关键词匹配使用基于匹配数的相似度）
    results = [
        ProductSearchResult(
            product_id=row[0],
            product_name=row[1],
            description=row[2],
            category_1=row[3],
            category_2=row[4],
            brand=row[5],
            price=float(row[6]),
            similarity_score=min(len(row[7]) / 10.0, 1.0),  # 匹配位置数归一化
            match_reason="keyword"
        )
        for row in rows
    ]
    
    return results

async def _hybrid_search_products(request: ProductSearchRequest) -> Tuple[List[ProductSearchResult], bool]:
    """混合检索（向量 + 关键词融合）"""
    # 1. 分别获取两种检索结果
    vector_results, cache_hit = await _vector_search_products(
        ProductSearchRequest(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k * 2,  # 取更多结果用于融合
            search_mode="vector",
            use_cache=request.use_cache
        )
    )
    
    keyword_results = await _keyword_search_products(
        ProductSearchRequest(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k * 2,
            search_mode="keyword",
            use_cache=False
        )
    )
    
    # 2. 融合结果（RRF - Reciprocal Rank Fusion）
    product_scores = {}
    
    # 向量检索得分（权重 0.7）
    for rank, result in enumerate(vector_results, 1):
        product_scores[result.product_id] = product_scores.get(result.product_id, 0) + 0.7 / (rank + 60)
    
    # 关键词检索得分（权重 0.3）
    for rank, result in enumerate(keyword_results, 1):
        product_scores[result.product_id] = product_scores.get(result.product_id, 0) + 0.3 / (rank + 60)
    
    # 3. 排序并取 top_k
    sorted_product_ids = sorted(product_scores.items(), key=lambda x: x[1], reverse=True)[:request.top_k]
    
    # 4. 构建最终结果（从原始结果中提取）
    product_map = {r.product_id: r for r in vector_results + keyword_results}
    
    results = []
    for product_id, score in sorted_product_ids:
        if product_id in product_map:
            result = product_map[product_id]
            result.similarity_score = score
            result.match_reason = "hybrid"
            results.append(result)
    
    return results, cache_hit

# ==================== 商品推荐 ====================

class ProductRecommendRequest(BaseModel):
    """商品推荐请求"""
    product_id: int = Field(..., description="商品ID")
    top_k: int = Field(5, description="推荐数量", ge=1, le=20)
    exclude_same_category: bool = Field(False, description="是否排除同类目商品")

@router.post("/products/recommend", response_model=ProductSearchResponse)
async def recommend_products(request: ProductRecommendRequest):
    """
    商品推荐 API
    
    基于向量相似度推荐相似商品
    """
    start_time = time.time()
    
    try:
        # 1. 查询商品的 embedding
        sql = """
        SELECT embedding, category_1, category_2
        FROM vector_layer.semantic_product
        WHERE product_id = %(product_id)s
        """
        
        result = ch_manager.execute_query(sql, {"product_id": request.product_id})
        
        if not result:
            raise HTTPException(status_code=404, detail=f"商品不存在: {request.product_id}")
        
        product_embedding = result[0][0]
        category_1 = result[0][1]
        category_2 = result[0][2]
        
        # 2. 查询相似商品
        sql_parts = [
            "SELECT",
            "    product_id,",
            "    product_name,",
            "    description,",
            "    category_1,",
            "    category_2,",
            "    brand,",
            "    price,",
            "    cosineDistance(embedding, %(product_vec)s) AS distance",
            "FROM vector_layer.semantic_product",
            "WHERE product_id != %(product_id)s"
        ]
        
        params = {
            "product_vec": product_embedding,
            "product_id": request.product_id
        }
        
        # 排除同类目
        if request.exclude_same_category:
            sql_parts.append("AND NOT (category_1 = %(category_1)s AND category_2 = %(category_2)s)")
            params["category_1"] = category_1
            params["category_2"] = category_2
        
        sql_parts.extend([
            "ORDER BY distance ASC",
            f"LIMIT {request.top_k}"
        ])
        
        sql = "\n".join(sql_parts)
        rows = ch_manager.execute_query(sql, params)
        
        # 3. 格式化结果
        results = [
            ProductSearchResult(
                product_id=row[0],
                product_name=row[1],
                description=row[2],
                category_1=row[3],
                category_2=row[4],
                brand=row[5],
                price=float(row[6]),
                similarity_score=1.0 - row[7],
                match_reason="vector"
            )
            for row in rows
        ]
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"商品推荐完成: product_id={request.product_id}, results={len(results)}, latency={latency_ms}ms")
        
        return ProductSearchResponse(
            query=f"商品 {request.product_id} 的推荐",
            total=len(results),
            results=results,
            latency_ms=latency_ms,
            cache_hit=False,
            search_mode="recommend"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"商品推荐失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"商品推荐失败: {str(e)}")

# ==================== 批量向量化 ====================

class BatchVectorizeRequest(BaseModel):
    """批量向量化请求"""
    product_ids: List[int] = Field(..., description="商品ID列表", max_length=100)

class BatchVectorizeResponse(BaseModel):
    """批量向量化响应"""
    total: int
    success_count: int
    failed_count: int
    latency_ms: int

@router.post("/products/vectorize", response_model=BatchVectorizeResponse)
async def batch_vectorize_products(request: BatchVectorizeRequest):
    """
    批量向量化商品
    
    从 DWD 层读取商品信息，生成向量并写入 vector_layer
    """
    start_time = time.time()
    success_count = 0
    failed_count = 0
    
    try:
        # 1. 查询商品信息
        placeholders = ", ".join([f"%(id_{i})s" for i in range(len(request.product_ids))])
        sql = f"""
        SELECT
            product_id,
            product_name,
            category_1,
            category_2,
            brand,
            price,
            stock,
            description
        FROM dwd_layer.dim_product
        WHERE product_id IN ({placeholders})
        """
        
        params = {f"id_{i}": pid for i, pid in enumerate(request.product_ids)}
        products = ch_manager.execute_query(sql, params)
        
        if not products:
            raise HTTPException(status_code=404, detail="未找到商品")
        
        # 2. 批量生成 embedding
        texts = [f"{row[1]} {row[7]}" for row in products]  # product_name + description
        embeddings = await emb_manager.get_embeddings_batch(texts)
        
        # 3. 批量插入 vector_layer
        insert_sql = """
        INSERT INTO vector_layer.semantic_product
        (product_id, product_name, description, embedding, category_1, category_2, brand, price, created_at)
        VALUES
        """
        
        insert_data = []
        for product, embedding in zip(products, embeddings):
            try:
                insert_data.append({
                    'product_id': product[0],
                    'product_name': product[1],
                    'description': product[7] or '',
                    'embedding': embedding,
                    'category_1': product[2],
                    'category_2': product[3],
                    'brand': product[4],
                    'price': float(product[5]),
                    'created_at': datetime.now()
                })
                success_count += 1
            except Exception as e:
                logger.error(f"处理商品 {product[0]} 失败: {e}")
                failed_count += 1
        
        if insert_data:
            ch_manager.client.execute(insert_sql, insert_data)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"批量向量化完成: total={len(request.product_ids)}, success={success_count}, failed={failed_count}, latency={latency_ms}ms")
        
        return BatchVectorizeResponse(
            total=len(request.product_ids),
            success_count=success_count,
            failed_count=failed_count,
            latency_ms=latency_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量向量化失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量向量化失败: {str(e)}")

# ==================== 统计端点 ====================

@router.get("/stats")
async def get_stats():
    """
    获取数仓统计信息
    """
    try:
        # 向量层商品数
        vector_products = ch_manager.execute_query(
            "SELECT count() FROM vector_layer.semantic_product"
        )[0][0]
        
        # 按类目统计
        by_category = ch_manager.execute_query("""
            SELECT category_1, count() AS cnt
            FROM vector_layer.semantic_product
            GROUP BY category_1
            ORDER BY cnt DESC
        """)
        
        # 按品牌统计（Top 10）
        by_brand = ch_manager.execute_query("""
            SELECT brand, count() AS cnt
            FROM vector_layer.semantic_product
            GROUP BY brand
            ORDER BY cnt DESC
            LIMIT 10
        """)
        
        return {
            "total_vector_products": vector_products,
            "products_by_category": {row[0]: row[1] for row in by_category},
            "top_brands": {row[0]: row[1] for row in by_brand}
        }
    
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))