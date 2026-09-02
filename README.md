# 电商向量数仓：ClickHouse + 语义搜索

![ClickHouse](https://img.shields.io/badge/ClickHouse-24.1-yellow?logo=clickhouse)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue?logo=mysql)
![Vue](https://img.shields.io/badge/Vue-3.0-green?logo=vue.js)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

**基于 ClickHouse 的向量数仓实战项目**：支持语义搜索、智能推荐、用户画像 | 传统 OLAP + 向量检索 | 一键 Docker 部署

## 📖 项目简介

这是一个**向量数仓**实战项目，在传统 ClickHouse OLAP 数仓基础上，增加向量存储和语义检索能力，支持自然语言查询：

### 🔥 核心亮点

- 🔍 **语义搜索**：支持"适合夏天穿的衣服"这类自然语言查询，自动匹配 T恤、短袖、薄款外套
- 🎯 **智能推荐**：基于向量相似度的"看了又看"功能，新商品也能推荐（解决冷启动）
- 💡 **混合检索**：RRF 算法融合向量检索 + 关键词检索，兼顾语义和精确度
- 💰 **低成本**：复用 ClickHouse 集群，无需单独部署 Milvus/Pinecone
- 🚀 **SQL + 向量**：一条 SQL 完成语义搜索 + 业务过滤（价格、类目、库存）

### 📊 完整数仓能力

- 📊 **分层架构**：ODS/DWD/DWS/ADS 四层 + 向量层
- 👤 **用户画像**：RFM 模型 + 偏好标签（与向量推荐结合）
- 📈 **GMV 大屏**：同比环比分析、商品排行
- 🐳 **一键部署**：Docker Compose 启动完整环境

## ✨ 向量数仓 vs 传统数仓

### 传统数仓只能这样查询：
```sql
SELECT * FROM products 
WHERE category = '服装' AND price BETWEEN 100 AND 500;
```
❌ 只能精确匹配，无法理解用户意图

### 向量数仓可以这样查询：
```python
search("适合夏天穿的衣服")
```
✅ 自动匹配：T恤、短袖衬衫、薄款外套、清凉连衣裙...  
✅ 理解语义："夏天" = 轻薄、透气、清凉

---

## 🛠 核心技术实现

### 1. 向量存储：ClickHouse Array(Float32)

```sql
CREATE TABLE product_vectors (
    product_id UInt64,
    product_name String,
    embedding Array(Float32),  -- 1024 维向量
    ...
) ENGINE = MergeTree();
```

**为什么选 ClickHouse 而不是 Milvus？**
- ✅ 复用现有集群，无需新组件
- ✅ 支持 SQL + 向量混合查询
- ✅ 存储成本低（列式压缩）

### 2. 三种检索模式

| 模式 | 适用场景 | 示例查询 |
|------|---------|---------|
| **向量检索** | 语义理解 | "适合夏天穿的衣服" |
| **关键词检索** | 精确匹配 | "小米手机" |
| **混合检索** | 兼顾两者 | "性价比高的蓝牙耳机" |

### 3. RRF 融合算法

```python
# 向量检索结果权重 0.7 + 关键词检索权重 0.3
def hybrid_search(query, top_k=10):
    vector_results = vector_search(query, top_k=50)
    keyword_results = keyword_search(query, top_k=50)
    
    # RRF 融合
    scores = {}
    for rank, item in enumerate(vector_results):
        scores[item['id']] += 0.7 / (rank + 60)
    for rank, item in enumerate(keyword_results):
        scores[item['id']] += 0.3 / (rank + 60)
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```

### 4. 向量 + SQL 混合查询

```sql
-- 查询"好吃的零食"，价格 10-100 元，食品类目
SELECT 
    product_id,
    product_name,
    -- 余弦相似度计算
    cosine_similarity(embedding, query_vector) AS score
FROM product_vectors
WHERE 
    category_1 = '食品'           -- SQL 过滤
    AND price BETWEEN 10 AND 100  -- SQL 过滤
    AND score > 0.5               -- 向量阈值
ORDER BY score DESC
LIMIT 10;
```

**对比纯向量库（Milvus/Pinecone）**：
- ❌ 需要两次查询：先向量检索，再用 ID 查业务字段
- ✅ ClickHouse 一条 SQL 搞定

### 5. 与用户画像结合

```sql
-- 基于用户偏好的个性化语义搜索
-- 用户喜欢"数码"类目，查询"送女朋友的礼物"
SELECT 
    p.product_name,
    vector_similarity AS base_score,
    -- 用户偏好加权
    if(p.category_1 IN user.prefer_category, 1.5, 1.0) AS weight,
    base_score * weight AS final_score
FROM product_vectors p
JOIN user_portrait u ON u.user_id = 1
ORDER BY final_score DESC;
```

## 🛠 技术栈

| 层次 | 技术选型 |
|------|----------|
| 数据源 | MySQL 8.0 |
| 数据仓库 | ClickHouse 24.1 |
| ETL | Python 3.11 + clickhouse-driver |
| 查询服务 | FastAPI |
| Embedding | bge-large-zh-v1.5 (本地) |
| 前端 | Vue 3 + Element Plus |
| 编排 | Docker Compose |

## 🚀 快速开始

### 前置要求

- Docker 24.0+
- Docker Compose 2.20+
- 至少 8GB RAM

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ecommerce-data-warehouse.git
cd ecommerce-data-warehouse

# 2. 启动所有服务
docker-compose up -d

# 3. 等待服务启动（约 60 秒）
docker-compose ps

# 4. 初始化数据
bash scripts/init_full_warehouse.sh

# 5. 访问前端界面
open http://localhost:3000
```

### 访问服务

- **前端界面**：http://localhost:3000
  - 数据概览、用户画像、商品推荐、GMV 大屏
- **语义搜索 Demo**：http://localhost:8000/semantic-search.html
- **API 文档**：http://localhost:8000/docs
- **ClickHouse**：localhost:8123 (HTTP)

## 📁 项目结构

```
ecommerce-data-warehouse/
├── scripts/                 # 数据初始化和 ETL 脚本
│   ├── init_mysql_ods.sql         # MySQL ODS 层初始化
│   ├── init_clickhouse_warehouse.sql  # ClickHouse 全层初始化
│   ├── sync_mysql_to_clickhouse.py    # ODS → DWD 同步
│   ├── refresh_dws_layer.py           # DWD → DWS 聚合
│   ├── refresh_ads_layer.py           # DWS → ADS 建模
│   └── vectorize_products.py          # 商品向量化
├── api-service/             # FastAPI 查询服务
│   ├── app/
│   │   ├── main.py                # API 入口
│   │   ├── search.py              # 语义搜索
│   │   ├── clickhouse_client.py   # ClickHouse 客户端
│   │   └── embedding_client.py    # Embedding 服务
│   └── requirements.txt
├── embedding-service/       # BGE Embedding 微服务
│   ├── app.py
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Overview.vue       # 数据概览
│   │   │   ├── DWDLayer.vue       # DWD 明细查询
│   │   │   ├── DWSLayer.vue       # DWS 汇总查询
│   │   │   └── ADSLayer.vue       # ADS 应用（用户画像、推荐）
│   │   └── api/clickhouse.js
│   └── package.json
|
├── docker-compose.yml       # 服务编排
└── README.md
```

## 📚 使用示例

### 1. 用户画像查询

```bash
# 查询用户 ID=1 的画像
curl http://localhost:8000/api/v1/user_portrait?user_id=1

# 返回：
{
  "user_id": 1,
  "username": "张三",
  "rfm_score": 3.8,
  "user_type": "重要价值客户",
  "prefer_category": ["数码", "家居"],
  "prefer_brand": ["Apple", "小米"],
  "prefer_price_range": "3000-8000",
  "recent_days": 7,
  "total_orders": 15,
  "total_amount": 45678.90
}
```

### 2. 商品推荐

```bash
# 为用户 ID=1 推荐商品
curl http://localhost:8000/api/v1/recommend?user_id=1&top_k=5

# 返回：
{
  "results": [
    {
      "product_id": 5,
      "product_name": "iPhone 15 Pro",
      "score": 0.85,
      "reason": "您喜欢的品牌「Apple」在「数码」类目"
    },
    ...
  ]
}
```

### 3. 语义搜索

```python
import requests

# 向量检索：语义理解
response = requests.post("http://localhost:8000/api/v1/products/search", json={
    "query": "适合夏天穿的衣服",
    "search_mode": "vector",
    "top_k": 5
})

# 能匹配到：T恤、短袖、薄款外套（即使查询中没有这些词）
```

### 4. GMV 大屏数据

```bash
# 查询最近 30 天 GMV 趋势
curl http://localhost:8000/api/v1/gmv_dashboard?days=30

# 返回：
{
  "gmv_trend": [
    {"date": "2024-09-01", "gmv": 125678.50, "yoy": 15.3, "mom": 2.1},
    ...
  ],
  "top_products": [...],
  "top_users": [...]
}
```

## 🎯 核心亮点

### 1. 表引擎选型解决实际问题

**问题**：维度表需要更新，但 MergeTree 不支持主键去重  
**方案**：使用 `ReplacingMergeTree(update_time)`，按 update_time 保留最新版本  
**坑点**：去重是异步的，查询时需加 `FINAL` 修饰符

### 2. Array 类型的跨系统解析

**问题**：`Array(String)` 类型前端解析为字符串而非数组  
**方案**：ClickHouse 使用 `JSONCompact` 格式，前端手动解析  
**代码**：见 `frontend/src/api/clickhouse.js`

### 3. RFM 用户分层算法

**业务价值**：将用户分为 4 类，为精准营销提供数据支持  
**技术实现**：ClickHouse 窗口函数 + 分位数计算  
**SQL**：见 `scripts/refresh_ads_layer.py`

### 4. 向量检索与关键词检索的融合

**挑战**：纯向量检索召回率低，纯关键词检索无法理解语义  
**方案**：RRF（Reciprocal Rank Fusion）算法融合两种检索结果  
**权重**：向量 0.7 + 关键词 0.3

## 🐛 已解决的技术难题

| 难题 | 现象 | 解决方案 |
|------|------|----------|
| ReplacingMergeTree 去重不生效 | 插入相同主键数据仍有重复 | 理解异步 merge 机制，查询时加 `FINAL` |
| Array 列前端解析失败 | `['数码', '家居']` 变成字符串 | 改用 JSONCompact 格式 + 前端手动解析 |
| Flink CDC 不支持 ClickHouse | JDBC connector 无 ClickHouse 方言 | 改用批处理同步（每 5 分钟） |
| 向量检索延迟高 | 余弦相似度计算慢 | 规划引入 usearch HNSW 索引（待实现） |

详见 [docs/踩坑总结.md](docs/踩坑总结.md)

## 📊 数据规模

- **ODS 层**：5 张表（用户、商品、订单、订单明细、用户行为）
- **DWD 层**：5 张表（2 个维度表 + 3 个事实表）
- **DWS 层**：3 张汇总表（用户日汇总、商品日汇总、流量统计）
- **ADS 层**：3 张应用表（用户画像、商品推荐、GMV 大屏）
- **测试数据**：8 个用户、12 个商品、8 笔订单

## 🔮 未来规划

- [ ] 引入 Flink CDC 实现秒级实时同步（目前是批处理）
- [ ] 集成 usearch HNSW 向量索引优化检索性能
- [ ] 增加 Redis 缓存层提升 QPS
- [ ] 接入 Grafana 监控数据新鲜度和查询性能
- [ ] 支持更多 Embedding 模型（OpenAI、通义千问）

⭐ 如果这个项目对你有帮助，请给个 Star！