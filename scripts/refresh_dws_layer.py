#!/usr/bin/env python3
"""
DWS 层数据刷新脚本
从 DWD 层聚合计算汇总指标
"""

import clickhouse_connect
from datetime import datetime

# 配置
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

def main():
    print("=" * 50)
    print("DWS 层数据刷新")
    print("=" * 50)
    print()
    
    try:
        # 只刷新在 init_clickhouse_warehouse.sql 中实际定义的表
        # user_order_summary, product_sales_summary, daily_sales_summary 这些表不在标准 SQL 中
        # 实际应该刷新: trade_user_1d, product_sale_1d
        
        ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
        
        # 1. 刷新 trade_user_1d
        print("1. 刷新用户交易日汇总 (trade_user_1d)...")
        
        # 先检查数据范围
        date_check = ch_client.query("SELECT min(order_date) AS min_date, max(order_date) AS max_date, count() AS total FROM dwd_layer.fact_order_detail").first_row
        print(f"   DWD fact_order_detail 数据范围: {date_check[0]} ~ {date_check[1]}, 共 {date_check[2]} 条")
        
        query = """
        INSERT INTO dws_layer.trade_user_1d
        SELECT
            user_id,
            order_date AS dt,
            count(DISTINCT order_id) AS order_count,
            countIf(order_status IN ('paid', 'shipped', 'completed')) AS payment_count,
            sumIf(amount, order_status IN ('paid', 'shipped', 'completed')) AS total_amount,
            count(DISTINCT product_id) AS product_count,
            if(payment_count > 0, avgIf(price, order_status IN ('paid', 'shipped', 'completed')), 0) AS avg_price,
            now() AS update_time
        FROM dwd_layer.fact_order_detail
        WHERE order_date >= today() - INTERVAL 30 DAY
        GROUP BY user_id, order_date
        """
        ch_client.command(query)
        count = ch_client.command("SELECT count() FROM dws_layer.trade_user_1d WHERE dt >= today() - INTERVAL 30 DAY")
        print(f"✓ 用户交易日汇总完成，最近30天共 {count:,} 条记录\n")
        
        # 2. 刷新 product_sale_1d
        print("2. 刷新商品销售日汇总 (product_sale_1d)...")
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
        print(f"✓ 商品销售日汇总完成，最近30天共 {count:,} 条记录\n")
        
        print()
        print("=" * 50)
        print("✓ DWS 层刷新完成！")
        print("=" * 50)
        print()
        print("验证:")
        print("  docker exec clickhouse clickhouse-client --query='SELECT * FROM dws_layer.trade_user_1d LIMIT 5 FORMAT Pretty'")
        print("  docker exec clickhouse clickhouse-client --query='SELECT * FROM dws_layer.product_sale_1d ORDER BY sale_amount DESC LIMIT 5 FORMAT Pretty'")
        
    except Exception as e:
        print(f"\n✗ 刷新失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()