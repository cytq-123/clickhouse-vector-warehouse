#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品向量化脚本
将商品信息转换为语义向量并存储到 ClickHouse
"""

import sys
import os
import clickhouse_connect
import httpx
import asyncio
from typing import List
import time

# 确保 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 配置
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

EMBEDDING_SERVICE_URL = "http://localhost:8001"

async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """批量获取文本的 embedding"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed_batch",
                json={"texts": texts}
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
    except Exception as e:
        print(f"✗ 获取 embedding 失败: {e}")
        raise

async def vectorize_products():
    """将商品信息向量化"""
    print("=" * 60)
    print("商品向量化")
    print("=" * 60)
    print()
    
    # 1. 检查 Embedding 服务
    print("1. 检查 Embedding 服务...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{EMBEDDING_SERVICE_URL}/health")
            health = response.json()
            print(f"✓ Embedding 服务正常")
            print(f"  模型: {health['model']}")
            print(f"  维度: {health['dimension']}")
            print(f"  设备: {health['device']}")
    except Exception as e:
        print(f"✗ Embedding 服务不可用: {e}")
        print("请先启动 Embedding 服务:")
        print("  docker-compose up -d embedding-service")
        return
    
    print()
    
    # 2. 从 ClickHouse 读取商品数据
    print("2. 读取商品数据...")
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    query = """
    SELECT
        product_id,
        product_name,
        category_1,
        category_2,
        brand,
        price,
        description
    FROM dwd_layer.dim_product
    ORDER BY product_id
    """
    
    result = ch_client.query(query)
    products = result.result_rows
    print(f"✓ 读取 {len(products)} 个商品")
    print()
    
    if not products:
        print("⚠ 没有商品数据，请先运行初始化脚本")
        return
    
    # 3. 构建商品文本描述
    print("3. 构建商品描述文本...")
    product_texts = []
    for p in products:
        # 拼接商品信息：商品名 + 类目 + 品牌 + 描述
        text = f"{p[1]} {p[2]} {p[3]} {p[4]} {p[6]}"
        product_texts.append(text)
    print(f"✓ 构建完成")
    print()
    
    # 4. 批量生成向量
    print("4. 生成语义向量...")
    batch_size = 10
    all_embeddings = []
    
    for i in range(0, len(product_texts), batch_size):
        batch = product_texts[i:i+batch_size]
        print(f"  处理 {i+1}-{min(i+batch_size, len(product_texts))}/{len(product_texts)}...")
        
        embeddings = await get_embeddings_batch(batch)
        all_embeddings.extend(embeddings)
        
        # 避免过于频繁请求
        if i + batch_size < len(product_texts):
            await asyncio.sleep(0.5)
    
    print(f"✓ 生成 {len(all_embeddings)} 个向量")
    print()
    
    # 5. 写入 ClickHouse
    print("5. 写入 Vector 层...")
    
    # 清空旧数据
    ch_client.command("TRUNCATE TABLE vector_layer.semantic_product")
    
    # 准备数据
    data = []
    for i, (product, embedding) in enumerate(zip(products, all_embeddings)):
        data.append([
            product[0],  # product_id
            product[1],  # product_name
            product[6],  # description
            embedding,   # embedding
            product[2],  # category_1
            product[3],  # category_2
            product[4],  # brand
            float(product[5]),  # price
        ])
    
    # 批量插入
    ch_client.insert(
        'vector_layer.semantic_product',
        data,
        column_names=['product_id', 'product_name', 'description', 'embedding',
                     'category_1', 'category_2', 'brand', 'price']
    )
    
    count = ch_client.command("SELECT count() FROM vector_layer.semantic_product")
    print(f"✓ 写入完成，共 {count} 条记录")
    print()
    
    # 6. 验证
    print("6. 验证向量数据...")
    sample = ch_client.query("""
        SELECT 
            product_id,
            product_name,
            brand,
            category_1,
            length(embedding) AS vec_dim
        FROM vector_layer.semantic_product
        ORDER BY product_id
        LIMIT 5
    """)
    
    print("样本数据:")
    print("-" * 80)
    for row in sample.result_rows:
        try:
            # 确保正确处理中文字符
            pid = row[0]
            name = str(row[1]).strip()
            brand = str(row[2]).strip()
            category = str(row[3]).strip()
            vec_dim = row[4]
            print(f"  ID: {pid:4d} | {name:30s} | {brand:10s} | {category:10s} | 维度: {vec_dim}")
        except Exception as e:
            print(f"  [显示错误] {e}")
    print("-" * 80)
    
    # 统计信息
    stats = ch_client.query("""
        SELECT 
            count() as total,
            count(DISTINCT category_1) as categories,
            count(DISTINCT brand) as brands
        FROM vector_layer.semantic_product
    """)
    
    if stats.result_rows:
        total, categories, brands = stats.result_rows[0]
        print(f"\n统计: 共 {total} 个商品, {categories} 个类目, {brands} 个品牌")
    
    print()
    
    print("=" * 60)
    print("✓ 商品向量化完成！")
    print("=" * 60)
    print()
    print("下一步:")
    print("  1. 运行语义搜索: python3 scripts/vector_search.py")
    print("  2. 生成推荐结果: python3 scripts/vector_recommend.py")

async def main():
    try:
        await vectorize_products()
    except Exception as e:
        print(f"\n✗ 向量化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())