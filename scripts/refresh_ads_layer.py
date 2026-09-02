#!/usr/bin/env python3
"""
ADS 层数据刷新脚本
从 DWS 层计算面向业务的应用指标
"""

import clickhouse_connect
from datetime import datetime, timedelta

CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

def refresh_gmv_dashboard():
    """刷新 GMV 大屏数据"""
    print("刷新 GMV 大屏数据...")
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 清空旧数据
    ch_client.command("TRUNCATE TABLE ads_layer.gmv_dashboard")
    
    # 计算最近30天的 GMV
    query = """
    INSERT INTO ads_layer.gmv_dashboard
    SELECT
        dt,
        sum(total_amount) AS gmv,
        sum(order_count) AS order_count,
        count(DISTINCT user_id) AS user_count,
        sum(product_count) AS product_count,
        
        -- 同比增长率（与7天前对比，避免除零）
        if(lagInFrame(gmv, 7) OVER (ORDER BY dt) > 0,
           (gmv - lagInFrame(gmv, 7) OVER (ORDER BY dt)) / lagInFrame(gmv, 7) OVER (ORDER BY dt) * 100,
           0) AS gmv_yoy,
        
        -- 环比增长率（与前一天对比，避免除零）
        if(lagInFrame(gmv, 1) OVER (ORDER BY dt) > 0,
           (gmv - lagInFrame(gmv, 1) OVER (ORDER BY dt)) / lagInFrame(gmv, 1) OVER (ORDER BY dt) * 100,
           0) AS gmv_mom,
        
        '' AS top_category,
        '' AS top_brand,
        '' AS top_city,
        now() AS update_time
    FROM dws_layer.trade_user_1d
    WHERE dt >= today() - INTERVAL 30 DAY
    GROUP BY dt
    ORDER BY dt
    """
    
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM ads_layer.gmv_dashboard WHERE dt >= today() - INTERVAL 30 DAY")
    print(f"✓ GMV 大屏数据刷新完成，最近30天共 {count} 条记录")

def refresh_user_portrait():
    """刷新用户画像表（RFM模型）"""
    print("刷新用户画像表...")
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 清空表
    ch_client.command("TRUNCATE TABLE ads_layer.user_portrait")
    
    # 计算 RFM 和用户偏好
    query = """
    INSERT INTO ads_layer.user_portrait
    WITH user_orders AS (
        -- 获取用户订单及商品信息
        SELECT 
            o.user_id,
            p.category_1,
            p.brand,
            o.price
        FROM dwd_layer.fact_order_detail AS o
        JOIN dwd_layer.dim_product AS p ON o.product_id = p.product_id
        WHERE o.order_status IN ('paid', 'shipped', 'completed')
    ),
    user_preference AS (
        -- 统计用户偏好
        SELECT 
            user_id,
            groupArray(category_1) AS all_categories,
            groupArray(brand) AS all_brands,
            avg(price) AS avg_price
        FROM user_orders
        GROUP BY user_id
    )
    SELECT
        u.user_id,
        u.username,
        if(u.gender = 1, 'M', if(u.gender = 2, 'F', 'U')) AS gender,
        u.age,
        u.city,
        u.user_level,
        
        -- R: Recency（最近一次消费距今天数）
        dateDiff('day', max(t.dt), today()) AS recency,
        
        -- F: Frequency（累计消费次数）
        sum(t.order_count) AS frequency,
        
        -- M: Monetary（累计消费金额）
        sum(t.total_amount) AS monetary,
        
        -- RFM 综合得分（简化计算）
        (
            (5 - least(floor(recency / 30), 5)) * 0.3 +
            (least(floor(frequency / 10), 5)) * 0.3 +
            (least(floor(monetary / 1000), 5)) * 0.4
        ) AS rfm_score,
        
        -- 用户分类（基于 RFM）
        multiIf(
            rfm_score >= 4, '重要价值客户',
            rfm_score >= 3, '重要发展客户',
            rfm_score >= 2, '一般价值客户',
            '一般发展客户'
        ) AS user_type,
        
        -- 偏好标签（从实际订单中统计）
        arrayDistinct(coalesce(pref.all_categories, [])) AS prefer_category,
        arrayDistinct(coalesce(pref.all_brands, [])) AS prefer_brand,
        multiIf(
            coalesce(pref.avg_price, 0) >= 5000, '高端',
            coalesce(pref.avg_price, 0) >= 2000, '中高端',
            coalesce(pref.avg_price, 0) >= 500, '中端',
            '大众'
        ) AS prefer_price_range,
        
        -- 行为特征
        if(sum(t.order_count) > 0, avg(t.total_amount / t.order_count), 0) AS avg_order_amount,
        sum(t.order_count) AS total_orders,
        max(t.dt) AS last_order_date,
        
        now() AS update_time
    FROM dwd_layer.dim_user AS u
    LEFT JOIN dws_layer.trade_user_1d AS t ON u.user_id = t.user_id
    LEFT JOIN user_preference AS pref ON u.user_id = pref.user_id
    WHERE u.is_active = 1
    GROUP BY 
        u.user_id, u.username, u.gender, u.age, u.city, u.user_level,
        pref.all_categories, pref.all_brands, pref.avg_price
    """
    
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM ads_layer.user_portrait")
    print(f"✓ 用户画像表刷新完成，共 {count} 个用户")

def refresh_product_recommend():
    """刷新商品推荐结果（基于用户画像的个性化推荐）"""
    print("刷新商品推荐结果...")
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 清空旧推荐数据
    ch_client.command("TRUNCATE TABLE ads_layer.product_recommend")
    
    # 基于用户画像的个性化推荐（简化版）
    query = """
    INSERT INTO ads_layer.product_recommend
    SELECT 
        user_id,
        product_id,
        product_name,
        recommend_score,
        recommend_reason,
        now() AS recommend_time,
        0 AS is_clicked,
        0 AS is_purchased
    FROM (
        SELECT 
            user_id,
            product_id,
            product_name,
            recommend_score,
            recommend_reason,
            row_number() OVER (PARTITION BY user_id ORDER BY recommend_score DESC, product_id) AS rn
        FROM (
            SELECT 
                u.user_id AS user_id,
                p.product_id AS product_id,
                p.product_name AS product_name,
                
                -- 计算推荐分数（多维度）
                (
                    -- 1. 类目匹配度（40%权重）
                    if(length(u.prefer_category) > 0 AND has(u.prefer_category, p.category_1), 0.4, 0.0) +
                    
                    -- 2. 品牌匹配度（30%权重）
                    if(length(u.prefer_brand) > 0 AND has(u.prefer_brand, p.brand), 0.3, 0.0) +
                    
                    -- 3. 价格匹配度（20%权重）
                    if(
                        (u.prefer_price_range = '高端' AND p.price >= 5000) OR
                        (u.prefer_price_range = '中高端' AND p.price >= 2000 AND p.price < 5000) OR
                        (u.prefer_price_range = '中端' AND p.price >= 500 AND p.price < 2000) OR
                        (u.prefer_price_range = '大众' AND p.price < 500),
                        0.2, 0.0
                    ) +
                    
                    -- 4. 基础热度分（确保所有商品都有最低分）
                    0.1
                ) AS recommend_score,
                
                -- 生成推荐理由
                multiIf(
                    length(u.prefer_category) > 0 AND length(u.prefer_brand) > 0 AND has(u.prefer_category, p.category_1) AND has(u.prefer_brand, p.brand),
                    concat('您喜欢的品牌「', p.brand, '」在「', p.category_1, '」类目'),
                    length(u.prefer_category) > 0 AND has(u.prefer_category, p.category_1),
                    concat('根据您对「', p.category_1, '」的偏好推荐'),
                    length(u.prefer_brand) > 0 AND has(u.prefer_brand, p.brand),
                    concat('您喜欢的品牌「', p.brand, '」推荐'),
                    '热门商品推荐'
                ) AS recommend_reason
                
            FROM ads_layer.user_portrait AS u
            CROSS JOIN dwd_layer.dim_product AS p
            -- 暂时不过滤已购商品，确保能生成推荐
        )
    )
    WHERE rn <= 7  -- 每个用户推荐Top7
    """
    
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM ads_layer.product_recommend WHERE toDate(recommend_time) = today()")
    print(f"✓ 商品推荐结果刷新完成，今日新增 {count} 条推荐")

def generate_top_products_report():
    """生成 TOP 商品销售报告"""
    print("\n生成 TOP 商品销售报告...")
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    query = """
    SELECT
        p.product_name,
        p.brand,
        p.category_1,
        sum(s.sale_amount) AS total_sales,
        sum(s.sale_count) AS total_count,
        sum(s.order_count) AS order_count
    FROM dws_layer.product_sale_1d AS s
    JOIN dwd_layer.dim_product AS p ON s.product_id = p.product_id
    WHERE s.dt >= today() - INTERVAL 30 DAY
    GROUP BY p.product_name, p.brand, p.category_1
    ORDER BY total_sales DESC
    LIMIT 10
    """
    
    result = ch_client.query(query)
    
    print("\n📊 最近30天 TOP10 商品销售排行:")
    print("-" * 80)
    for i, row in enumerate(result.result_rows, 1):
        print(f"{i}. {row[0][:20]:20s} | {row[1]:10s} | {row[2]:10s} | 销售额: ¥{row[3]:>10.2f} | 销量: {row[4]:>6} | 订单: {row[5]:>6}")
    print("-" * 80)

def main():
    print("=" * 50)
    print("ADS 层数据刷新")
    print("=" * 50)
    print()
    
    try:
        refresh_gmv_dashboard()
        refresh_user_portrait()
        refresh_product_recommend()
        generate_top_products_report()
        
        print()
        print("=" * 50)
        print("✓ ADS 层刷新完成！")
        print("=" * 50)
        print()
        print("验证:")
        print("  docker exec clickhouse clickhouse-client --query='SELECT * FROM ads_layer.gmv_dashboard ORDER BY dt DESC LIMIT 5 FORMAT Pretty'")
        print("  docker exec clickhouse clickhouse-client --query='SELECT * FROM ads_layer.user_portrait ORDER BY rfm_score DESC LIMIT 5 FORMAT Pretty'")
        
    except Exception as e:
        print(f"\n✗ 刷新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()