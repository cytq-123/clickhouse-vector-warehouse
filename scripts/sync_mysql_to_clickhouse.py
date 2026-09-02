#!/usr/bin/env python3
"""
简化版 CDC 同步脚本
使用 Python 直接读取 MySQL 并写入 ClickHouse
适用于初始数据加载和测试
"""

import mysql.connector
import clickhouse_connect
from datetime import datetime
import time

# 配置
MYSQL_CONFIG = {
    'host': 'localhost',  # 从宿主机访问使用 localhost
    'port': 3306,
    'user': 'root',  # 使用 root 用户
    'password': 'root123',
    'database': 'ecommerce_ods',
    'charset': 'utf8mb4',  # 强制使用 UTF-8 编码
    'use_unicode': True
}

CLICKHOUSE_CONFIG = {
    'host': 'localhost',  # 从宿主机访问使用 localhost
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

def sync_dim_users():
    """同步用户维度表"""
    print("同步用户维度表...")
    
    # 读取 MySQL
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = mysql_conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ods_user_info")
    users = cursor.fetchall()
    cursor.close()
    mysql_conn.close()
    
    # 写入 ClickHouse
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    data = []
    for user in users:
        data.append([
            user['user_id'],
            user['username'],
            user['gender'],
            user['age'],
            user['city'],
            user['register_time'].date() if hasattr(user['register_time'], 'date') else user['register_time'],
            user.get('user_level', 1),
            1,  # is_active
            datetime.now()
        ])
    
    ch_client.insert(
        'dwd_layer.dim_user',
        data,
        column_names=['user_id', 'username', 'gender', 'age', 
                     'city', 'register_date', 'user_level', 'is_active', 'update_time']
    )
    
    print(f"✓ 同步 {len(data)} 条用户记录")

def sync_dim_products():
    """同步商品维度表"""
    print("同步商品维度表...")
    
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = mysql_conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ods_product_info")
    products = cursor.fetchall()
    cursor.close()
    mysql_conn.close()
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    data = []
    for product in products:
        data.append([
            product['product_id'],
            product['product_name'],
            product['category_1'],
            product.get('category_2', ''),
            product['brand'],
            float(product['price']),
            product.get('stock', 0),
            product.get('description', ''),
            datetime.now()
        ])
    
    ch_client.insert(
        'dwd_layer.dim_product',
        data,
        column_names=['product_id', 'product_name', 'category_1', 'category_2',
                     'brand', 'price', 'stock', 'description', 'update_time']
    )
    
    print(f"✓ 同步 {len(data)} 条商品记录")

def sync_fact_order_detail():
    """同步订单明细事实表"""
    print("同步订单明细事实表...")
    
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = mysql_conn.cursor(dictionary=True)
    
    # 执行 JOIN 查询
    query = """
    SELECT 
        o.order_id, od.id AS order_detail_id, o.user_id, od.product_id,
        od.quantity, od.price, 
        (od.quantity * od.price) AS amount,
        o.order_status, o.payment_type,
        DATE(o.order_time) AS order_date, 
        o.order_time, o.payment_time
    FROM ods_order_detail od
    JOIN ods_order_info o ON od.order_id = o.order_id
    """
    
    cursor.execute(query)
    order_details = cursor.fetchall()
    cursor.close()
    mysql_conn.close()
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    data = []
    for detail in order_details:
        data.append([
            detail['order_id'],
            detail['order_detail_id'],
            detail['user_id'],
            detail['product_id'],
            detail['quantity'],
            float(detail['price']),
            float(detail['amount']),
            detail['order_status'],
            detail['payment_type'],
            detail['order_date'],
            detail['order_time'],
            detail.get('payment_time') or detail['order_time'],
            datetime.now(),
            'mysql_cdc'
        ])
    
    ch_client.insert(
        'dwd_layer.fact_order_detail',
        data,
        column_names=['order_id', 'order_detail_id', 'user_id', 'product_id',
                     'quantity', 'price', 'amount', 'order_status', 'payment_type',
                     'order_date', 'order_time', 'payment_time', 'etl_time', 'data_source']
    )
    
    print(f"✓ 同步 {len(data)} 条订单明细记录")

def sync_fact_user_behavior():
    """同步用户行为事实表"""
    print("同步用户行为事实表...")
    
    mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = mysql_conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ods_user_behavior")
    behaviors = cursor.fetchall()
    cursor.close()
    mysql_conn.close()
    
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    
    data = []
    for behavior in behaviors:
        behavior_time = behavior['behavior_time']
        
        data.append([
            behavior['user_id'],
            behavior['product_id'],
            behavior['behavior_type'],
            behavior_time.date() if hasattr(behavior_time, 'date') else behavior_time,
            behavior_time,
            behavior.get('source', 'web'),
            datetime.now()
        ])
    
    ch_client.insert(
        'dwd_layer.fact_user_behavior',
        data,
        column_names=['user_id', 'product_id', 'behavior_type', 'behavior_date',
                     'behavior_time', 'source', 'etl_time']
    )
    
    print(f"✓ 同步 {len(data)} 条用户行为记录")

def main():
    print("=" * 50)
    print("MySQL -> ClickHouse CDC 同步")
    print("=" * 50)
    print()
    
    try:
        # 同步维度表
        sync_dim_users()
        time.sleep(0.5)
        
        sync_dim_products()
        time.sleep(0.5)
        
        # 同步事实表
        sync_fact_order_detail()
        time.sleep(0.5)
        
        sync_fact_user_behavior()
        
        print()
        print("=" * 50)
        print("✓ 所有表同步完成！")
        print("=" * 50)
        print()
        print("验证数据:")
        print("  docker exec clickhouse clickhouse-client --query='SELECT count() FROM dwd_layer.dim_user_info'")
        print("  docker exec clickhouse clickhouse-client --query='SELECT count() FROM dwd_layer.fact_order_detail'")
        
    except Exception as e:
        print(f"\n✗ 同步失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()