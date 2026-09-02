-- ====================================
-- MySQL 示例数据源初始化脚本
-- 模拟企业 Wiki 文档库
-- ====================================

USE wiki_db;

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    title VARCHAR(500) NOT NULL COMMENT '文档标题',
    content TEXT NOT NULL COMMENT '文档内容',
    author VARCHAR(100) DEFAULT '' COMMENT '作者',
    tags JSON COMMENT '标签（JSON 数组）',
    status ENUM('draft', 'published', 'archived') DEFAULT 'draft' COMMENT '状态',
    view_count INT DEFAULT 0 COMMENT '浏览次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_updated (updated_at),
    INDEX idx_status (status),
    FULLTEXT INDEX ft_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档表';

-- 插入示例数据
INSERT INTO documents (title, content, author, tags, status) VALUES
('ClickHouse 性能优化指南', 
 'ClickHouse 作为列式数据库，在 OLAP 场景下有极高性能。优化要点包括：
 1. 合理设计主键和分区键，避免全表扫描
 2. 使用物化视图预聚合常用查询
 3. 调整 max_threads 和 max_memory_usage 参数
 4. 避免 SELECT * 查询，只选择需要的列
 5. 使用 PREWHERE 过滤条件下推
 
 案例：某电商公司通过优化分区策略，查询延迟从 5s 降低到 200ms。',
 '张三',
 '["数据库", "ClickHouse", "性能优化"]',
 'published'),

('Flink CDC 实战：实时同步 MySQL 到 ClickHouse',
 'Flink CDC 是基于 Debezium 的变更数据捕获组件，支持 MySQL binlog 解析。
 
 实现步骤：
 1. 开启 MySQL binlog（binlog_format=ROW）
 2. 创建 Flink CDC Source
 3. 配置 ClickHouse Sink（支持批量写入）
 4. 设置 Checkpoint 保证 exactly-once
 
 性能优化：
 - 调整 debezium.snapshot.mode（避免全量快照）
 - 增大 sink.buffer-flush.max-rows（批量写入）
 - 使用异步 I/O 提升吞吐量
 
 监控指标：采集延迟、反压时间、Checkpoint 耗时。',
 '李四',
 '["Flink", "CDC", "实时数仓"]',
 'published'),

('Redis 缓存设计模式',
 'Redis 在高并发系统中常用的缓存模式：
 
 1. Cache-Aside（旁路缓存）
    - 读：先查缓存，miss 则查 DB 并回写
    - 写：先写 DB，再删除缓存
    - 优点：简单，适合读多写少
 
 2. Read-Through / Write-Through
    - 由缓存层自动同步 DB
    - 优点：业务代码简单
    - 缺点：增加复杂度
 
 3. Write-Behind（异步写入）
    - 先写缓存，异步批量刷 DB
    - 优点：高吞吐
    - 缺点：可能丢数据
 
 常见问题：
 - 缓存穿透：布隆过滤器
 - 缓存击穿：互斥锁
 - 缓存雪崩：过期时间加随机值',
 '王五',
 '["Redis", "缓存", "架构设计"]',
 'published'),

('Kafka 消息队列最佳实践',
 'Kafka 在微服务架构中的应用要点：
 
 生产者配置：
 - acks=all 保证消息不丢失
 - enable.idempotence=true 幂等性
 - compression.type=lz4 压缩
 
 消费者配置：
 - enable.auto.commit=false 手动提交
 - isolation.level=read_committed 读已提交
 - max.poll.records 控制批量大小
 
 分区策略：
 - 按业务 key 分区（保证顺序）
 - 避免热点分区（负载均衡）
 
 监控指标：
 - 生产延迟、消费 lag、磁盘使用率',
 '赵六',
 '["Kafka", "消息队列", "分布式"]',
 'published'),

('向量数据库技术选型对比',
 '主流向量数据库对比（2024）：
 
 | 方案 | 优势 | 劣势 | 适用场景 |
 |------|------|------|----------|
 | Pinecone | 全托管，易用 | 成本高 | 快速验证 MVP |
 | Milvus | 功能强大，开源 | 运维复杂 | 大规模部署 |
 | Weaviate | 集成 LLM，GraphQL | 社区较小 | AI 应用 |
 | ClickHouse+向量索引 | 成本低，混合查询 | 需自研 | 已有 CH 技术栈 |
 
 选型建议：
 - 预算充足且追求稳定：Pinecone
 - 技术团队强且规模大：Milvus
 - 已有 ClickHouse 经验：自研方案
 
 成本对比（1000 万向量）：
 - Pinecone: $350/月
 - Milvus: $250/月（自建）
 - ClickHouse: $100/月',
 '周七',
 '["向量数据库", "AI", "RAG"]',
 'draft'),

('LangChain RAG 应用开发指南',
 'LangChain RAG (Retrieval-Augmented Generation) 实战：
 
 基本流程：
 1. 文档加载（DocumentLoader）
 2. 文本分割（TextSplitter）
 3. 向量化（Embeddings）
 4. 存储检索（VectorStore）
 5. LLM 生成（Chain）
 
 代码示例：
 ```python
 from langchain.vectorstores import Chroma
 from langchain.embeddings import OpenAIEmbeddings
 from langchain.chains import RetrievalQA
 
 vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings())
 qa_chain = RetrievalQA.from_chain_type(
     llm=llm,
     retriever=vectorstore.as_retriever(k=5)
 )
 answer = qa_chain.run("question")
 ```
 
 优化技巧：
 - 重排序（Reranker）提升准确率
 - 混合检索（关键词+向量）
 - Query 改写（多角度召回）',
 '钱八',
 '["LangChain", "RAG", "LLM"]',
 'published');

-- 创建 CDC 用户（给 Flink CDC 使用）
-- CREATE USER 'flink_cdc'@'%' IDENTIFIED BY 'flink_cdc_password';
-- GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'flink_cdc'@'%';
-- FLUSH PRIVILEGES;

-- 查看 binlog 状态
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW MASTER STATUS;