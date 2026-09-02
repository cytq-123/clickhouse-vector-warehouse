-- ====================================
-- ClickHouse 向量数仓初始化脚本
-- ====================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS vector_warehouse;

-- 主文档表（包含向量）
CREATE TABLE IF NOT EXISTS vector_warehouse.documents
(
    doc_id          String COMMENT '文档唯一标识',
    chunk_id        String COMMENT '分块标识 (doc_id + chunk_index)',
    content         String COMMENT '原始文本内容',
    embedding       Array(Float32) COMMENT '向量 (维度 1024)',
    title           String COMMENT '文档标题',
    author          String DEFAULT '' COMMENT '作者',
    source_type     Enum8('wiki'=1, 'log'=2, 'chat'=3, 'api'=4) COMMENT '数据源类型',
    tags            Array(String) DEFAULT [] COMMENT '业务标签',
    metadata        String DEFAULT '{}' COMMENT 'JSON 元数据',
    created_at      DateTime DEFAULT now() COMMENT '创建时间',
    updated_at      DateTime DEFAULT now() COMMENT '更新时间',
    version         UInt32 DEFAULT 1 COMMENT '版本号',
    is_deleted      UInt8 DEFAULT 0 COMMENT '逻辑删除标记'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)  -- 按月分区
ORDER BY (source_type, doc_id, chunk_id)
PRIMARY KEY (source_type, doc_id, chunk_id)
SETTINGS 
    index_granularity = 8192,
    storage_policy = 'default',
    -- 自动清理 6 个月前的数据
    ttl_only_drop_parts = 1;

-- TTL 策略：6 个月后删除
ALTER TABLE vector_warehouse.documents MODIFY TTL created_at + INTERVAL 6 MONTH;

-- 向量索引表（用于加速检索，存储预计算的索引结构）
CREATE TABLE IF NOT EXISTS vector_warehouse.vector_index
(
    index_id        String COMMENT '索引标识',
    index_type      Enum8('hnsw'=1, 'ivf'=2, 'flat'=3) COMMENT '索引类型',
    index_params    String COMMENT '索引参数 JSON',
    index_data      String COMMENT '序列化的索引数据',
    doc_count       UInt64 COMMENT '包含的文档数',
    created_at      DateTime DEFAULT now(),
    updated_at      DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (index_type, index_id)
PRIMARY KEY (index_type, index_id);

-- 查询日志表（用于监控和优化）
CREATE TABLE IF NOT EXISTS vector_warehouse.query_logs
(
    query_id        String COMMENT '查询 ID',
    query_text      String COMMENT '查询文本',
    query_vector    Array(Float32) COMMENT '查询向量',
    filters         String COMMENT '过滤条件 JSON',
    top_k           UInt16 COMMENT '返回数量',
    result_count    UInt16 COMMENT '实际返回数量',
    latency_ms      UInt32 COMMENT '延迟（毫秒）',
    cache_hit       UInt8 COMMENT '缓存命中',
    timestamp       DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, query_id)
TTL timestamp + INTERVAL 30 DAY;  -- 保留 30 天

-- 数据质量监控表
CREATE TABLE IF NOT EXISTS vector_warehouse.data_quality_metrics
(
    metric_date     Date COMMENT '日期',
    source_type     String COMMENT '数据源',
    doc_count       UInt64 COMMENT '文档总数',
    avg_chunk_size  Float32 COMMENT '平均块大小',
    null_embedding_count UInt64 COMMENT '空向量数',
    duplicate_count UInt64 COMMENT '重复文档数',
    avg_latency_ms  Float32 COMMENT '平均采集延迟'
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(metric_date)
ORDER BY (metric_date, source_type);

-- 创建物化视图：实时统计每日查询量
CREATE MATERIALIZED VIEW IF NOT EXISTS vector_warehouse.query_stats_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMMDD(query_date)
ORDER BY (query_date, cache_hit)
AS SELECT
    toDate(timestamp) AS query_date,
    cache_hit,
    count() AS query_count,
    avg(latency_ms) AS avg_latency,
    quantile(0.5)(latency_ms) AS p50_latency,
    quantile(0.99)(latency_ms) AS p99_latency
FROM vector_warehouse.query_logs
GROUP BY query_date, cache_hit;

-- 创建物化视图：实时统计文档增长
CREATE MATERIALIZED VIEW IF NOT EXISTS vector_warehouse.doc_growth_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(doc_date)
ORDER BY (doc_date, source_type)
AS SELECT
    toDate(created_at) AS doc_date,
    source_type,
    count() AS doc_count,
    countIf(is_deleted = 1) AS deleted_count
FROM vector_warehouse.documents
GROUP BY doc_date, source_type;

-- 辅助函数：计算余弦相似度
CREATE FUNCTION IF NOT EXISTS cosine_similarity AS (vec1, vec2) -> 
    arraySum(arrayMap((x, y) -> x * y, vec1, vec2)) / 
    (sqrt(arraySum(arrayMap(x -> x * x, vec1))) * sqrt(arraySum(arrayMap(x -> x * x, vec2))));

-- 辅助函数：计算欧氏距离
CREATE FUNCTION IF NOT EXISTS euclidean_distance AS (vec1, vec2) ->
    sqrt(arraySum(arrayMap((x, y) -> (x - y) * (x - y), vec1, vec2)));

-- 示例数据插入（用于测试）
-- 注意：示例数据已注释，可在服务启动后通过 API 插入真实数据
-- INSERT INTO vector_warehouse.documents (doc_id, chunk_id, content, embedding, title, source_type, tags) VALUES
--     ('doc_001', 'doc_001_chunk_0', 'ClickHouse 是一个用于在线分析处理的列式数据库管理系统。', arrayMap(x -> randNormal(), range(1024)), 'ClickHouse 简介', 'wiki', ['数据库', 'OLAP']),
--     ('doc_002', 'doc_002_chunk_0', 'Apache Flink 是一个流处理框架，支持事件时间处理和状态管理。', arrayMap(x -> randNormal(), range(1024)), 'Flink 基础', 'wiki', ['流处理', 'Flink']),
--     ('doc_003', 'doc_003_chunk_0', 'Redis 是一个开源的内存数据结构存储，可用作数据库、缓存和消息代理。', arrayMap(x -> randNormal(), range(1024)), 'Redis 入门', 'wiki', ['缓存', 'NoSQL']);

-- 创建用户（用于 API 服务连接）
-- CREATE USER IF NOT EXISTS api_user IDENTIFIED WITH sha256_password BY 'api_password_123';
-- GRANT SELECT, INSERT ON vector_warehouse.* TO api_user;

-- 查看表统计信息
SELECT
    table,
    formatReadableSize(sum(bytes)) AS size,
    sum(rows) AS rows,
    max(modification_time) AS latest_modification
FROM system.parts
WHERE database = 'vector_warehouse' AND active
GROUP BY table
ORDER BY sum(bytes) DESC;

SHOW TABLES FROM vector_warehouse;