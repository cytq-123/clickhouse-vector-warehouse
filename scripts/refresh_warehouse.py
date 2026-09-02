#!/usr/bin/env python3
"""
完整数据仓库刷新脚本
按照 DWD -> DWS -> ADS 的顺序依次刷新各层数据
"""

import clickhouse_connect
from datetime import datetime
import time

CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

def check_clickhouse_connection():
    """检查 ClickHouse 连接"""
    print("检查 ClickHouse 连接...")
    try:
        ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
        version = ch_client.command("SELECT version()")
        print(f"✓ ClickHouse 连接成功，版本: {version}")
        return True
    except Exception as e:
        print(f"✗ ClickHouse 连接失败: {e}")
        return False

def refresh_dwd_layer():
    """刷新 DWD 层（通常由 CDC 实时同步，这里做数据质量检查）"""
    print("\n" + "=" * 50)
    print("DWD 层数据质量检查")
    print("=" * 50)
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 检查事实表数据量
    checks = {
        'dwd_layer.fact_order_detail': '订单明细事实表',
        'dwd_layer.dim_user': '用户维度表',
        'dwd_layer.dim_product': '商品维度表'
    }
    
    for table, desc in checks.items():
        try:
            count = ch_client.command(f"SELECT count() FROM {table}")
            print(f"✓ {desc}: {count:,} 条记录")
        except Exception as e:
            print(f"✗ {desc} 检查失败: {e}")
    
    print("\nDWD 层检查完成")

def refresh_dws_layer():
    """刷新 DWS 层"""
    print("\n" + "=" * 50)
    print("DWS 层数据刷新")
    print("=" * 50)
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 1. 用户交易日汇总
    print("\n1. 刷新用户交易日汇总...")
    query = """
    INSERT INTO dws_layer.trade_user_1d
    SELECT
        user_id,
        order_date AS dt,
        count(DISTINCT order_id) AS order_count,
        countIf(order_status IN ('paid', 'shipped', 'completed')) AS payment_count,
        sumIf(amount, order_status IN ('paid', 'shipped', 'completed')) AS total_amount,
        count(DISTINCT product_id) AS product_count,
        avgIf(price, order_status IN ('paid', 'shipped', 'completed')) AS avg_price,
        now() AS update_time
    FROM dwd_layer.fact_order_detail
    WHERE order_date >= today() - INTERVAL 30 DAY
    GROUP BY user_id, order_date
    """
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM dws_layer.trade_user_1d WHERE dt >= today() - INTERVAL 30 DAY")
    print(f"✓ 用户交易日汇总完成，最近30天共 {count:,} 条记录")
    
    # 2. 商品销售日汇总
    print("\n2. 刷新商品销售日汇总...")
    query = """
    INSERT INTO dws_layer.product_sale_1d
    SELECT
        product_id,
        order_date AS dt,
        count(DISTINCT order_id) AS order_count,
        sum(quantity) AS sale_count,
        sum(amount) AS sale_amount,
        0 AS view_count,
        0 AS cart_count,
        0 AS favorite_count,
        now() AS update_time
    FROM dwd_layer.fact_order_detail
    WHERE order_date >= today() - INTERVAL 30 DAY
      AND order_status IN ('paid', 'shipped', 'completed')
    GROUP BY product_id, order_date
    """
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM dws_layer.product_sale_1d WHERE dt >= today() - INTERVAL 30 DAY")
    print(f"✓ 商品销售日汇总完成，最近30天共 {count:,} 条记录")
    
    print("\n✓ DWS 层刷新完成")

def refresh_ads_layer():
    """刷新 ADS 层"""
    print("\n" + "=" * 50)
    print("ADS 层数据刷新")
    print("=" * 50)
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 1. GMV 大屏数据
    print("\n1. 刷新 GMV 大屏数据...")
    query = """
    INSERT INTO ads_layer.gmv_dashboard
    SELECT
        dt,
        sum(total_amount) AS gmv,
        sum(order_count) AS order_count,
        uniq(user_id) AS user_count,
        sum(product_count) AS product_count,
        0 AS gmv_yoy,
        0 AS gmv_mom,
        '' AS top_category,
        '' AS top_brand,
        '' AS top_city,
        now() AS update_time
    FROM dws_layer.trade_user_1d
    WHERE dt >= today() - INTERVAL 30 DAY
    GROUP BY dt
    """
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM ads_layer.gmv_dashboard WHERE dt >= today() - INTERVAL 30 DAY")
    print(f"✓ GMV 大屏数据完成，最近30天共 {count:,} 条记录")
    
    # 2. 用户画像
    print("\n2. 刷新用户画像...")
    ch_client.command("TRUNCATE TABLE ads_layer.user_portrait")
    
    query = """
    INSERT INTO ads_layer.user_portrait
    SELECT
        u.user_id,
        u.username,
        multiIf(u.gender = 1, 'M', u.gender = 2, 'F', 'U') AS gender,
        u.age,
        u.city,
        u.user_level,
        
        dateDiff('day', ifNull(max(t.dt), u.register_date), today()) AS recency,
        ifNull(sum(t.order_count), 0) AS frequency,
        ifNull(sum(t.total_amount), 0) AS monetary,
        
        (5 - least(floor(recency / 30), 5)) * 0.3 + 
        least(floor(frequency / 10), 5) * 0.3 + 
        least(floor(monetary / 1000), 5) * 0.4 AS rfm_score,
        
        multiIf(
            rfm_score >= 4, '重要价值客户',
            rfm_score >= 3, '重要发展客户',
            rfm_score >= 2, '一般价值客户',
            '一般发展客户'
        ) AS user_type,
        
        [] AS prefer_category,
        [] AS prefer_brand,
        '' AS prefer_price_range,
        
        ifNull(avg(t.total_amount / nullIf(t.order_count, 0)), 0) AS avg_order_amount,
        ifNull(sum(t.order_count), 0) AS total_orders,
        ifNull(max(t.dt), u.register_date) AS last_order_date,
        
        now() AS update_time
    FROM dwd_layer.dim_user AS u
    LEFT JOIN dws_layer.trade_user_1d AS t ON u.user_id = t.user_id
    WHERE u.is_active = 1
    GROUP BY u.user_id, u.username, u.gender, u.age, u.city, u.user_level, u.register_date
    """
    ch_client.command(query)
    count = ch_client.command("SELECT count() FROM ads_layer.user_portrait")
    print(f"✓ 用户画像完成，共 {count:,} 个用户")
    
    print("\n✓ ADS 层刷新完成")

def generate_summary_report():
    """生成汇总报告"""
    print("\n" + "=" * 50)
    print("数据仓库汇总报告")
    print("=" * 50)
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    # 最近7天 GMV 趋势
    print("\n📊 最近7天 GMV 趋势:")
    query = """
    SELECT
        dt,
        round(gmv, 2) AS gmv_rounded,
        order_count,
        user_count,
        round(gmv / nullIf(order_count, 0), 2) AS avg_order_amount
    FROM ads_layer.gmv_dashboard
    WHERE dt >= today() - INTERVAL 7 DAY
    ORDER BY dt DESC
    """
    result = ch_client.query(query)
    
    print("-" * 80)
    print(f"{'日期':12s} | {'GMV':>12s} | {'订单数':>8s} | {'用户数':>8s} | {'客单价':>10s}")
    print("-" * 80)
    for row in result.result_rows:
        print(f"{str(row[0]):12s} | ¥{row[1]:>11.2f} | {row[2]:>8d} | {row[3]:>8d} | ¥{row[4]:>9.2f}")
    print("-" * 80)
    
    # 用户分层统计
    print("\n👥 用户分层统计:")
    query = """
    SELECT
        user_type,
        count() AS user_count,
        round(sum(monetary), 2) AS total_monetary,
        round(avg(frequency), 2) AS avg_frequency
    FROM ads_layer.user_portrait
    GROUP BY user_type
    ORDER BY total_monetary DESC
    """
    result = ch_client.query(query)
    
    print("-" * 80)
    print(f"{'用户类型':20s} | {'用户数':>8s} | {'总消费':>15s} | {'平均购买次数':>12s}")
    print("-" * 80)
    for row in result.result_rows:
        print(f"{row[0]:20s} | {row[1]:>8d} | ¥{row[2]:>14.2f} | {row[3]:>12.2f}")
    print("-" * 80)

def main():
    print("=" * 60)
    print(" " * 15 + "数据仓库完整刷新")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    start_time = time.time()
    
    try:
        # 1. 检查连接
        if not check_clickhouse_connection():
            print("\n✗ 无法连接到 ClickHouse，请检查服务是否启动")
            return
        
        # 2. 检查 DWD 层
        refresh_dwd_layer()
        
        # 3. 刷新 DWS 层
        refresh_dws_layer()
        
        # 4. 刷新 ADS 层
        refresh_ads_layer()
        
        # 5. 生成报告
        generate_summary_report()
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 60)
        print(f"✓ 数据仓库刷新完成！耗时: {elapsed:.2f} 秒")
        print("=" * 60)
        print()
        print("后续操作:")
        print("  1. 访问 Web UI 查看数据: http://localhost:8080")
        print("  2. 查看 ClickHouse 数据:")
        print("     docker exec clickhouse clickhouse-client")
        print("  3. 定时刷新（添加到 crontab）:")
        print("     0 2 * * * cd /path/to/AIBD && python3 scripts/refresh_warehouse.py")
        
    except Exception as e:
        print(f"\n✗ 刷新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()