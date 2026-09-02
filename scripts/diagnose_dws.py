#!/usr/bin/env python3
"""
诊断 DWS 层数据为空的原因
"""

import clickhouse_connect

CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

def main():
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    print("=" * 60)
    print("DWS 层数据诊断")
    print("=" * 60)
    print()
    
    # 1. 检查 ClickHouse 系统时间
    print("【1】ClickHouse 系统时间:")
    result = ch_client.query("SELECT now() AS current_time, today() AS current_date, today() - INTERVAL 30 DAY AS days_30_ago")
    for row in result.result_rows:
        print(f"  当前时间: {row[0]}")
        print(f"  当前日期: {row[1]}")
        print(f"  30天前: {row[2]}")
    print()
    
    # 2. 检查 fact_order_detail 数据
    print("【2】DWD fact_order_detail 数据:")
    result = ch_client.query("""
        SELECT 
            min(order_date) AS min_date,
            max(order_date) AS max_date,
            count() AS total_count,
            countIf(order_date >= today() - INTERVAL 30 DAY) AS within_30_days
        FROM dwd_layer.fact_order_detail
    """)
    for row in result.result_rows:
        print(f"  最小日期: {row[0]}")
        print(f"  最大日期: {row[1]}")
        print(f"  总记录数: {row[2]}")
        print(f"  30天内记录数: {row[3]}")
    print()
    
    # 3. 按日期分组统计
    print("【3】按日期分组的订单统计:")
    result = ch_client.query("""
        SELECT 
            order_date,
            count() AS count,
            count(DISTINCT order_id) AS order_count,
            count(DISTINCT user_id) AS user_count,
            sum(amount) AS total_amount,
            multiIf(
                order_date >= today(), '今天',
                order_date >= today() - 1, '昨天',
                order_date >= today() - 7, '最近7天',
                order_date >= today() - 30, '最近30天',
                '30天前'
            ) AS time_range
        FROM dwd_layer.fact_order_detail
        GROUP BY order_date
        ORDER BY order_date DESC
    """)
    for row in result.result_rows:
        print(f"  {row[0]} | 记录数:{row[1]:3} | 订单数:{row[2]} | 用户数:{row[3]} | 金额:{row[4]:10.2f} | {row[5]}")
    print()
    
    # 4. 检查订单状态分布
    print("【4】订单状态分布:")
    result = ch_client.query("""
        SELECT 
            order_status,
            count() AS count,
            sum(amount) AS total_amount
        FROM dwd_layer.fact_order_detail
        GROUP BY order_status
        ORDER BY count DESC
    """)
    for row in result.result_rows:
        print(f"  {row[0]:12} | 记录数:{row[1]:3} | 金额:{row[2]:10.2f}")
    print()
    
    # 5. 尝试执行 DWS 聚合的查询（不插入，只查看结果）
    print("【5】DWS 聚合查询预览（trade_user_1d）:")
    result = ch_client.query("""
        SELECT
            user_id,
            order_date AS dt,
            count(DISTINCT order_id) AS order_count,
            countIf(order_status IN ('paid', 'shipped', 'completed')) AS payment_count,
            sumIf(amount, order_status IN ('paid', 'shipped', 'completed')) AS total_amount,
            count(DISTINCT product_id) AS product_count,
            avgIf(price, order_status IN ('paid', 'shipped', 'completed')) AS avg_price
        FROM dwd_layer.fact_order_detail
        WHERE order_date >= today() - INTERVAL 30 DAY
        GROUP BY user_id, order_date
        ORDER BY order_date DESC, user_id
        LIMIT 10
    """)
    print(f"  查询结果数: {len(result.result_rows)} 行")
    if len(result.result_rows) > 0:
        print(f"  前几行数据:")
        for row in result.result_rows[:5]:
            print(f"    user_id:{row[0]} | dt:{row[1]} | orders:{row[2]} | payments:{row[3]} | amount:{row[4]:.2f}")
    else:
        print("  ⚠ 查询结果为空！")
        print()
        print("  可能原因:")
        print("    1. order_date 不在最近30天范围内")
        print("    2. today() 函数返回值与预期不符")
        print("    3. 时区问题导致日期比较失败")
    print()
    
    # 6. 检查 DWS 表当前数据
    print("【6】DWS 层当前数据:")
    result = ch_client.query("SELECT count() AS count FROM dws_layer.trade_user_1d")
    trade_count = result.first_row[0]
    print(f"  trade_user_1d: {trade_count} 条")
    
    result = ch_client.query("SELECT count() AS count FROM dws_layer.product_sale_1d")
    product_count = result.first_row[0]
    print(f"  product_sale_1d: {product_count} 条")
    print()
    
    # 7. 建议
    print("=" * 60)
    if len(result.result_rows) == 0:
        print("❌ 诊断结果: DWS 聚合查询为空")
        print()
        print("解决方案:")
        print("  1. 检查 MySQL 中的 order_time 是否为最近日期")
        print("  2. 重新导入 MySQL 数据: docker exec -i mysql-source mysql -uroot -proot123 --default-character-set=utf8mb4 < scripts/init_mysql_ods.sql")
        print("  3. 重新同步到 ClickHouse: python3 scripts/sync_mysql_to_clickhouse.py")
        print("  4. 或者直接运行: bash scripts/force_reinit.sh")
    else:
        print("✓ 诊断结果: DWS 聚合查询有数据，应该能成功刷新")
        print()
        print("下一步:")
        print("  运行: python3 scripts/refresh_dws_layer.py")
    print("=" * 60)

if __name__ == '__main__':
    main()