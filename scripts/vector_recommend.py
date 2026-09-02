#!/usr/bin/env python3
"""
基于向量的商品推荐脚本
为用户生成个性化推荐
"""

import clickhouse_connect
import httpx
import asyncio
from typing import List
import sys

# 配置
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

EMBEDDING_SERVICE_URL = "http://localhost:8001"

async def get_embedding(text: str):
    """获取文本的 embedding"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embed",
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
    except Exception as e:
        print(f"✗ 获取 embedding 失败: {e}")
        raise

async def recommend_for_user(user_id: int, top_k: int = 10):
    """
    为用户生成商品推荐
    
    策略:
    1. 基于用户历史购买的商品，构建用户画像向量
    2. 查找与用户画像最相似的商品
    3. 排除用户已购买的商品
    """
    print("=" * 60)
    print(f"为用户 {user_id} 生成推荐")
    print("=" * 60)
    print()
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 1. 获取用户历史购买的商品
    print("1. 分析用户购买历史...")
    
    query = """
    SELECT DISTINCT
        p.product_id,
        p.product_name,
        p.category_1,
        p.brand
    FROM dwd_layer.fact_order_detail AS f
    JOIN dwd_layer.dim_product AS p ON f.product_id = p.product_id
    WHERE f.user_id = {user_id:UInt64}
      AND f.order_status IN ('completed', 'paid', 'shipped')
    ORDER BY p.product_id
    LIMIT 10
    """
    
    result = ch_client.query(query, parameters={'user_id': user_id})
    purchased_products = result.result_rows
    
    if not purchased_products:
        print(f"⚠ 用户 {user_id} 没有购买记录，使用热门商品推荐")
        await recommend_popular(top_k)
        return
    
    purchased_ids = [p[0] for p in purchased_products]
    print(f"✓ 用户购买过 {len(purchased_products)} 个商品:")
    for p in purchased_products[:5]:
        print(f"  - {p[1]} ({p[2]}, {p[3]})")
    if len(purchased_products) > 5:
        print(f"  ... 还有 {len(purchased_products) - 5} 个")
    print()
    
    # 2. 构建用户偏好文本
    print("2. 构建用户画像...")
    
    # 提取类目和品牌偏好
    categories = list(set([p[2] for p in purchased_products]))
    brands = list(set([p[3] for p in purchased_products]))
    
    # 构建用户画像文本
    user_profile_text = f"喜欢购买 {', '.join(categories[:3])} 类商品，偏好品牌 {', '.join(brands[:3])}"
    print(f"  用户画像: {user_profile_text}")
    
    # 生成用户画像向量
    user_embedding = await get_embedding(user_profile_text)
    print(f"✓ 用户画像向量维度: {len(user_embedding)}")
    print()
    
    # 3. 向量检索推荐
    print("3. 生成推荐商品...")
    
    user_vector_str = '[' + ','.join(map(str, user_embedding)) + ']'
    purchased_ids_str = ','.join(map(str, purchased_ids))
    
    recommend_query = f"""
    SELECT
        product_id,
        product_name,
        brand,
        category_1,
        price,
        description,
        dotProduct(embedding, {user_vector_str}) AS similarity
    FROM vector_layer.semantic_product
    WHERE product_id NOT IN ({purchased_ids_str})
    ORDER BY similarity DESC
    LIMIT {top_k}
    """
    
    result = ch_client.query(recommend_query)
    recommendations = result.result_rows
    print(f"✓ 生成 {len(recommendations)} 个推荐")
    print()
    
    # 4. 展示推荐结果
    print("=" * 60)
    print("推荐结果")
    print("=" * 60)
    
    for i, row in enumerate(recommendations, 1):
        print(f"\n{i}. {row[1]}")
        print(f"   品牌: {row[2]} | 类目: {row[3]} | 价格: ¥{row[4]:.2f}")
        print(f"   匹配度: {row[6]:.4f}")
        print(f"   推荐理由: 与您偏好的商品相似")
    
    print("\n" + "=" * 60)
    
    # 5. 保存到 ADS 层
    print("\n5. 保存推荐结果到 ADS 层...")
    
    data = []
    for row in recommendations:
        data.append([
            user_id,
            row[0],  # product_id
            row[1],  # product_name
            float(row[6]),  # recommend_score
            "基于用户画像的向量推荐"
        ])
    
    ch_client.insert(
        'ads_layer.product_recommend',
        data,
        column_names=['user_id', 'product_id', 'product_name', 'recommend_score', 'recommend_reason']
    )
    
    print(f"✓ 推荐结果已保存")

async def recommend_popular(top_k: int = 10):
    """热门商品推荐（无购买历史的用户）"""
    print("=" * 60)
    print("热门商品推荐")
    print("=" * 60)
    print()
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    query = f"""
    SELECT
        p.product_id,
        p.product_name,
        p.brand,
        p.category_1,
        p.price,
        sum(s.sale_amount) AS total_sales
    FROM dws_layer.product_sale_1d AS s
    JOIN dwd_layer.dim_product AS p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.brand, p.category_1, p.price
    ORDER BY total_sales DESC
    LIMIT {top_k}
    """
    
    result = ch_client.query(query)
    
    if not result.result_rows:
        print("⚠ 没有销售数据，使用全部商品")
        query = f"""
        SELECT
            product_id,
            product_name,
            brand,
            category_1,
            price,
            0 AS total_sales
        FROM dwd_layer.dim_product
        LIMIT {top_k}
        """
        result = ch_client.query(query)
    
    print(f"✓ 热门商品 Top {top_k}:")
    print()
    
    for i, row in enumerate(result.result_rows, 1):
        print(f"{i}. {row[1]}")
        print(f"   品牌: {row[2]} | 类目: {row[3]} | 价格: ¥{row[4]:.2f}")
        if row[5] > 0:
            print(f"   销售额: ¥{row[5]:.2f}")
    
    print("\n" + "=" * 60)

async def batch_recommend(user_ids: List[int] = None, top_k: int = 10):
    """批量为用户生成推荐"""
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    if user_ids is None:
        # 获取所有活跃用户
        result = ch_client.query("""
            SELECT DISTINCT user_id
            FROM dwd_layer.dim_user
            WHERE is_active = 1
            ORDER BY user_id
        """)
        user_ids = [row[0] for row in result.result_rows]
    
    print("=" * 60)
    print(f"批量推荐: {len(user_ids)} 个用户")
    print("=" * 60)
    print()
    
    for i, uid in enumerate(user_ids, 1):
        print(f"\n[{i}/{len(user_ids)}] 处理用户 {uid}...")
        try:
            await recommend_for_user(uid, top_k)
            await asyncio.sleep(1)  # 避免过于频繁
        except Exception as e:
            print(f"✗ 用户 {uid} 推荐失败: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 批量推荐完成")
    print("=" * 60)

async def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "batch":
            # 批量模式
            await batch_recommend()
        else:
            # 指定用户
            user_id = int(sys.argv[1])
            await recommend_for_user(user_id)
    else:
        print("用法:")
        print("  python3 scripts/vector_recommend.py <user_id>  # 为指定用户推荐")
        print("  python3 scripts/vector_recommend.py batch      # 批量为所有用户推荐")
        print()
        print("示例:")
        print("  python3 scripts/vector_recommend.py 1")

if __name__ == '__main__':
    asyncio.run(main())