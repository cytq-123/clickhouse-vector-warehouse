#!/usr/bin/env python3
"""
测试连接脚本 - 验证 Python 能否连接到 ClickHouse
"""

import sys

# 检查依赖
try:
    import clickhouse_connect
    print("✓ clickhouse_connect 已安装")
except ImportError:
    print("✗ 缺少 clickhouse_connect，请安装:")
    print("  pip3 install clickhouse-connect")
    sys.exit(1)

# 配置
CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

print("\n测试 ClickHouse 连接...")
print(f"  主机: {CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}")

try:
    ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
    version = ch_client.command("SELECT version()")
    print(f"✓ 连接成功，ClickHouse 版本: {version}")
    
    # 检查数据库
    print("\n检查数据库:")
    databases = ch_client.command("SHOW DATABASES")
    for db in ['dwd_layer', 'dws_layer', 'ads_layer']:
        if db in databases:
            print(f"  ✓ {db}")
        else:
            print(f"  ✗ {db} (未找到)")
    
    # 检查 DWD 层表
    print("\n检查 DWD 层表:")
    try:
        tables = {
            'dim_user': ch_client.command("SELECT count() FROM dwd_layer.dim_user"),
            'dim_product': ch_client.command("SELECT count() FROM dwd_layer.dim_product"),
            'fact_order_detail': ch_client.command("SELECT count() FROM dwd_layer.fact_order_detail"),
        }
        for table, count in tables.items():
            print(f"  ✓ {table}: {count:,} 条记录")
    except Exception as e:
        print(f"  ✗ 无法查询表: {e}")
    
    # 检查 DWS 层表
    print("\n检查 DWS 层表:")
    try:
        dws_tables = {
            'trade_user_1d': ch_client.command("SELECT count() FROM dws_layer.trade_user_1d"),
            'product_sale_1d': ch_client.command("SELECT count() FROM dws_layer.product_sale_1d"),
        }
        for table, count in dws_tables.items():
            print(f"  ✓ {table}: {count:,} 条记录")
    except Exception as e:
        print(f"  ⚠  DWS 表可能为空或不存在，这是正常的（需要运行刷新脚本）")
    
    # 检查 ADS 层表
    print("\n检查 ADS 层表:")
    try:
        ads_tables = {
            'gmv_dashboard': ch_client.command("SELECT count() FROM ads_layer.gmv_dashboard"),
            'user_portrait': ch_client.command("SELECT count() FROM ads_layer.user_portrait"),
        }
        for table, count in ads_tables.items():
            print(f"  ✓ {table}: {count:,} 条记录")
    except Exception as e:
        print(f"  ⚠  ADS 表可能为空或不存在，这是正常的（需要运行刷新脚本）")
    
    print("\n" + "=" * 60)
    print("✓ 所有检查完成！可以运行刷新脚本了:")
    print("  bash scripts/refresh_warehouse.sh full")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ 连接失败: {e}")
    print("\n请检查:")
    print("  1. Docker 容器是否运行: docker ps | grep clickhouse")
    print("  2. 端口是否正确映射: 8123")
    print("  3. 用户名/密码是否正确")
    sys.exit(1)