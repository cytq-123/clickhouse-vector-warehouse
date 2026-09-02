#!/usr/bin/env python3
"""
语义搜索脚本
基于向量相似度搜索商品
"""

import clickhouse_connect
import httpx
import asyncio
import sys

# 配置
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

EMBEDDING_SERVICE_URL = "http://localhost:8001"

async def get_query_embedding(query: str):
    """获取查询文本的 embedding"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"text": query}
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
    except Exception as e:
        print(f"✗ 获取 embedding 失败: {e}")
        raise

async def semantic_search(query: str, top_k: int = 10):
    """
    语义搜索商品
    
    Args:
        query: 查询文本（例如："适合年轻人的运动鞋"）
        top_k: 返回前 K 个结果
    """
    print("=" * 60)
    print("语义搜索")
    print("=" * 60)
    print(f"查询: {query}")
    print(f"返回: Top {top_k}")
    print()
    
    # 1. 获取查询向量
    print("1. 生成查询向量...")
    query_embedding = await get_query_embedding(query)
    print(f"✓ 向量维度: {len(query_embedding)}")
    print()
    
    # 2. 向量检索
    print("2. 执行向量检索...")
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # ClickHouse 向量相似度计算
    # 使用余弦相似度（向量已归一化，所以可以用点积）
    query_vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
    
    search_query = f"""
    SELECT
        product_id,
        product_name,
        brand,
        category_1,
        price,
        description,
        dotProduct(embedding, {query_vector_str}) AS similarity
    FROM vector_layer.semantic_product
    ORDER BY similarity DESC
    LIMIT {top_k}
    """
    
    result = ch_client.query(search_query)
    print(f"✓ 检索完成")
    print()
    
    # 3. 展示结果
    print("=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    if not result.result_rows:
        print("未找到相关商品")
        return
    
    for i, row in enumerate(result.result_rows, 1):
        print(f"\n{i}. {row[1]}")
        print(f"   品牌: {row[2]} | 类目: {row[3]} | 价格: ¥{row[4]:.2f}")
        print(f"   相似度: {row[6]:.4f}")
        if row[5]:
            desc = row[5][:50] + "..." if len(row[5]) > 50 else row[5]
            print(f"   描述: {desc}")
    
    print("\n" + "=" * 60)

async def interactive_search():
    """交互式搜索"""
    print("=" * 60)
    print("语义搜索 - 交互模式")
    print("=" * 60)
    print("输入查询内容，按 Ctrl+C 退出")
    print()
    
    # 检查服务
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{EMBEDDING_SERVICE_URL}/health")
    except Exception:
        print("✗ Embedding 服务不可用，请先启动:")
        print("  docker-compose up -d embedding-service")
        return
    
    # 检查数据
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    count = ch_client.command("SELECT count() FROM vector_layer.semantic_product")
    
    if count == 0:
        print("✗ 没有向量数据，请先运行向量化:")
        print("  python3 scripts/vectorize_products.py")
        return
    
    print(f"✓ 已加载 {count} 个商品向量")
    print()
    
    while True:
        try:
            query = input("搜索 > ").strip()
            
            if not query:
                continue
            
            print()
            await semantic_search(query, top_k=5)
            print()
        
        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            continue

async def main():
    if len(sys.argv) > 1:
        # 命令行模式
        query = ' '.join(sys.argv[1:])
        await semantic_search(query)
    else:
        # 交互模式
        await interactive_search()

if __name__ == '__main__':
    asyncio.run(main())