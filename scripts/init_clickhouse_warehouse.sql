-- ====================================
-- ClickHouse 数仓分层表设计
-- DWD（明细数据层）+ DWS（汇总数据层）+ ADS（应用数据层）
-- ====================================

-- 启用实验性功能
SET allow_experimental_annoy_index = 1;

-- ==============================
-- DWD 层：明细数据层（事实表 + 维度表）
-- ==============================

CREATE DATABASE IF NOT EXISTS dwd_layer;

-- 订单明细事实表（星型模型核心）
CREATE TABLE IF NOT EXISTS dwd_layer.fact_order_detail
(
    order_id UInt64 COMMENT '订单ID',
    order_detail_id UInt64 COMMENT '订单明细ID',
    user_id UInt64 COMMENT '用户ID',
    product_id UInt64 COMMENT '商品ID',
    
    -- 度量字段
    quantity UInt32 COMMENT '购买数量',
    price Decimal(10, 2) COMMENT '单价',
    amount Decimal(10, 2) COMMENT '金额',
    
    -- 订单维度
    order_status Enum8('created'=1, 'paid'=2, 'shipped'=3, 'completed'=4, 'cancelled'=5) COMMENT '订单状态',
    payment_type String COMMENT '支付方式',
    
    -- 时间维度
    order_date Date COMMENT '下单日期',
    order_time DateTime COMMENT '下单时间',
    payment_time DateTime COMMENT '支付时间',
    
    -- ETL 元数据
    etl_time DateTime DEFAULT now() COMMENT 'ETL时间',
    data_source String DEFAULT 'mysql_cdc' COMMENT '数据来源'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (order_date, user_id, order_id)
TTL order_date + INTERVAL 2 YEAR
COMMENT '订单明细事实表';

-- 用户行为事实表
CREATE TABLE IF NOT EXISTS dwd_layer.fact_user_behavior
(
    user_id UInt64 COMMENT '用户ID',
    product_id UInt64 COMMENT '商品ID',
    behavior_type Enum8('view'=1, 'cart'=2, 'favorite'=3, 'click'=4) COMMENT '行为类型',
    behavior_date Date COMMENT '行为日期',
    behavior_time DateTime COMMENT '行为时间',
    source String COMMENT '来源',
    etl_time DateTime DEFAULT now() COMMENT 'ETL时间'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(behavior_date)
ORDER BY (behavior_date, user_id, product_id)
TTL behavior_date + INTERVAL 6 MONTH
COMMENT '用户行为事实表';

-- 用户维度表（SCD Type 1：保留最新状态）
CREATE TABLE IF NOT EXISTS dwd_layer.dim_user
(
    user_id UInt64 COMMENT '用户ID',
    username String COMMENT '用户名',
    gender Enum8('M'=1, 'F'=2, 'U'=0) COMMENT '性别',
    age UInt8 COMMENT '年龄',
    city String COMMENT '城市',
    register_date Date COMMENT '注册日期',
    user_level UInt8 COMMENT '用户等级',
    is_active UInt8 DEFAULT 1 COMMENT '是否活跃',
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
ORDER BY user_id
COMMENT '用户维度表';

-- 商品维度表
CREATE TABLE IF NOT EXISTS dwd_layer.dim_product
(
    product_id UInt64 COMMENT '商品ID',
    product_name String COMMENT '商品名称',
    category_1 String COMMENT '一级类目',
    category_2 String COMMENT '二级类目',
    brand String COMMENT '品牌',
    price Decimal(10, 2) COMMENT '价格',
    stock UInt32 COMMENT '库存',
    description String COMMENT '描述',
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
ORDER BY product_id
COMMENT '商品维度表';

-- 日期维度表（预生成）
CREATE TABLE IF NOT EXISTS dwd_layer.dim_date
(
    date_id Date COMMENT '日期',
    year UInt16 COMMENT '年',
    quarter UInt8 COMMENT '季度',
    month UInt8 COMMENT '月',
    day UInt8 COMMENT '日',
    week UInt8 COMMENT '周',
    weekday UInt8 COMMENT '星期',
    is_weekend UInt8 COMMENT '是否周末',
    is_holiday UInt8 DEFAULT 0 COMMENT '是否节假日'
)
ENGINE = MergeTree()
ORDER BY date_id
COMMENT '日期维度表';

-- ==============================
-- DWS 层：汇总数据层（轻度聚合）
-- ==============================

CREATE DATABASE IF NOT EXISTS dws_layer;

-- 用户交易日汇总表
CREATE TABLE IF NOT EXISTS dws_layer.trade_user_1d
(
    user_id UInt64 COMMENT '用户ID',
    dt Date COMMENT '日期',
    
    -- 交易指标
    order_count UInt32 COMMENT '下单次数',
    payment_count UInt32 COMMENT '支付次数',
    total_amount Decimal(18, 2) COMMENT '支付金额',
    
    -- 商品指标
    product_count UInt32 COMMENT '购买商品数',
    avg_price Decimal(10, 2) COMMENT '平均单价',
    
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, user_id)
COMMENT '用户交易日汇总';

-- 商品销售日汇总表
CREATE TABLE IF NOT EXISTS dws_layer.product_sale_1d
(
    product_id UInt64 COMMENT '商品ID',
    dt Date COMMENT '日期',
    
    -- 销售指标
    order_count UInt32 COMMENT '下单次数',
    sale_count UInt32 COMMENT '销售件数',
    sale_amount Decimal(18, 2) COMMENT '销售额',
    
    -- 行为指标
    view_count UInt32 COMMENT '浏览次数',
    cart_count UInt32 COMMENT '加购次数',
    favorite_count UInt32 COMMENT '收藏次数',
    
    -- 转化率（在 ADS 层计算）
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, product_id)
COMMENT '商品销售日汇总';

-- 流量统计小时汇总
CREATE TABLE IF NOT EXISTS dws_layer.traffic_stat_1h
(
    dt Date COMMENT '日期',
    hour UInt8 COMMENT '小时',
    source String COMMENT '来源',
    
    -- 流量指标
    uv UInt32 COMMENT '独立访客数',
    pv UInt32 COMMENT '浏览量',
    session_count UInt32 COMMENT '会话数',
    avg_session_duration Float32 COMMENT '平均会话时长(秒)',
    
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, hour, source)
COMMENT '流量统计小时汇总';

-- ==============================
-- ADS 层：应用数据层（面向业务）
-- ==============================

CREATE DATABASE IF NOT EXISTS ads_layer;

-- GMV 大屏数据
CREATE TABLE IF NOT EXISTS ads_layer.gmv_dashboard
(
    dt Date COMMENT '日期',
    
    -- 核心指标
    gmv Decimal(18, 2) COMMENT 'GMV（成交总额）',
    order_count UInt32 COMMENT '订单数',
    user_count UInt32 COMMENT '下单用户数',
    product_count UInt32 COMMENT '售出商品数',
    
    -- 同比环比
    gmv_yoy Float32 COMMENT 'GMV同比增长率',
    gmv_mom Float32 COMMENT 'GMV环比增长率',
    
    -- 细分维度
    top_category String COMMENT 'TOP类目',
    top_brand String COMMENT 'TOP品牌',
    top_city String COMMENT 'TOP城市',
    
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
ORDER BY dt
COMMENT 'GMV大屏数据';

-- 用户画像表
CREATE TABLE IF NOT EXISTS ads_layer.user_portrait
(
    user_id UInt64 COMMENT '用户ID',
    
    -- 基础属性
    username String COMMENT '用户名',
    gender String COMMENT '性别',
    age UInt8 COMMENT '年龄',
    city String COMMENT '城市',
    user_level UInt8 COMMENT '用户等级',
    
    -- RFM 模型
    recency UInt16 COMMENT '最近一次消费距今天数',
    frequency UInt32 COMMENT '累计消费次数',
    monetary Decimal(18, 2) COMMENT '累计消费金额',
    rfm_score Float32 COMMENT 'RFM综合得分',
    user_type String COMMENT '用户类型：重要价值/重要发展/重要保持/重要挽留/一般价值/一般发展/一般保持/一般挽留',
    
    -- 偏好标签
    prefer_category Array(String) COMMENT '偏好类目',
    prefer_brand Array(String) COMMENT '偏好品牌',
    prefer_price_range String COMMENT '偏好价格区间',
    
    -- 行为特征
    avg_order_amount Decimal(10, 2) COMMENT '平均订单金额',
    total_orders UInt32 COMMENT '累计订单数',
    last_order_date Date COMMENT '最后下单日期',
    
    update_time DateTime DEFAULT now() COMMENT '更新时间'
)
ENGINE = ReplacingMergeTree(update_time)
ORDER BY user_id
COMMENT '用户画像表';

-- 商品推荐结果表（供推荐系统使用）
CREATE TABLE IF NOT EXISTS ads_layer.product_recommend
(
    user_id UInt64 COMMENT '用户ID',
    product_id UInt64 COMMENT '推荐商品ID',
    product_name String COMMENT '商品名称',
    recommend_score Float32 COMMENT '推荐分数',
    recommend_reason String COMMENT '推荐理由',
    recommend_time DateTime DEFAULT now() COMMENT '推荐时间',
    is_clicked UInt8 DEFAULT 0 COMMENT '是否点击',
    is_purchased UInt8 DEFAULT 0 COMMENT '是否购买'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(recommend_time)
ORDER BY (user_id, product_id)
TTL recommend_time + INTERVAL 30 DAY
COMMENT '商品推荐结果表';

-- ==============================
-- Vector 层：语义检索层（保留原有能力）
-- ==============================

CREATE DATABASE IF NOT EXISTS vector_layer;

-- 商品语义向量表
CREATE TABLE IF NOT EXISTS vector_layer.semantic_product
(
    product_id UInt64 COMMENT '商品ID',
    product_name String COMMENT '商品名称',
    description String COMMENT '商品描述',
    embedding Array(Float32) COMMENT '语义向量（1024维）',
    category_1 String COMMENT '一级类目',
    category_2 String COMMENT '二级类目',
    brand String COMMENT '品牌',
    price Decimal(10, 2) COMMENT '价格',
    created_at DateTime DEFAULT now() COMMENT '创建时间',
    
    INDEX vec_idx embedding TYPE annoy() GRANULARITY 100
)
ENGINE = MergeTree()
ORDER BY product_id
COMMENT '商品语义向量表';

-- 订单语义特征表（用户购买意图分析）
CREATE TABLE IF NOT EXISTS vector_layer.semantic_order
(
    order_id UInt64 COMMENT '订单ID',
    user_id UInt64 COMMENT '用户ID',
    order_text String COMMENT '订单文本特征（商品组合描述）',
    embedding Array(Float32) COMMENT '订单语义向量',
    intent_label String COMMENT '意图标签：daily/gift/promotion',
    order_date Date COMMENT '下单日期',
    created_at DateTime DEFAULT now() COMMENT '创建时间'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(order_date)
ORDER BY (order_date, user_id)
TTL order_date + INTERVAL 6 MONTH
COMMENT '订单语义特征表';

-- ==============================
-- 物化视图：自动聚合
-- ==============================

-- 每日 GMV 物化视图
CREATE MATERIALIZED VIEW IF NOT EXISTS dws_layer.mv_gmv_1d
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(dt)
ORDER BY dt
AS
SELECT
    toDate(order_time) AS dt,
    sum(amount) AS gmv,
    count(DISTINCT order_id) AS order_count,
    count(DISTINCT user_id) AS user_count
FROM dwd_layer.fact_order_detail
WHERE order_status IN ('paid', 'shipped', 'completed')
GROUP BY dt;

-- 商品转化率物化视图
CREATE MATERIALIZED VIEW IF NOT EXISTS dws_layer.mv_product_conversion
ENGINE = ReplacingMergeTree()
ORDER BY (product_id, dt)
AS
SELECT
    product_id,
    toDate(behavior_time) AS dt,
    countIf(behavior_type = 'view') AS view_count,
    countIf(behavior_type = 'cart') AS cart_count,
    countIf(behavior_type = 'favorite') AS favorite_count
FROM dwd_layer.fact_user_behavior
GROUP BY product_id, dt;

-- ==============================
-- 数据质量监控表
-- ==============================

CREATE TABLE IF NOT EXISTS dwd_layer.data_quality_monitor
(
    table_name String COMMENT '表名',
    check_date Date COMMENT '检查日期',
    metric_name String COMMENT '指标名称',
    metric_value Float64 COMMENT '指标值',
    threshold Float64 COMMENT '阈值',
    is_abnormal UInt8 COMMENT '是否异常',
    create_time DateTime DEFAULT now() COMMENT '创建时间'
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(check_date)
ORDER BY (check_date, table_name, metric_name)
COMMENT '数据质量监控表';

-- 示例：插入质量监控指标
-- INSERT INTO dwd_layer.data_quality_monitor VALUES
-- ('fact_order_detail', today(), 'null_ratio_user_id', 0.001, 0.01, 0, now()),
-- ('fact_order_detail', today(), 'duplicate_ratio', 0.0001, 0.001, 0, now());