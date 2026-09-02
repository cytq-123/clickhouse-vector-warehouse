#!/bin/bash
# 彻底清理 ClickHouse 旧数据并重新初始化

set -e

echo "==========================================="
echo "彻底清理 ClickHouse 并重新同步"
echo "==========================================="
echo

# 1. 删除并重建所有 DWD/DWS/ADS 表
echo "【1/4】删除并重建 ClickHouse 表..."
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dwd_layer.dim_user"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dwd_layer.dim_product"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dwd_layer.fact_order_detail"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dwd_layer.fact_user_behavior"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dws_layer.trade_user_1d"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS dws_layer.product_sale_1d"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS ads_layer.user_portrait"
docker exec clickhouse clickhouse-client --query="DROP TABLE IF EXISTS ads_layer.product_recommend"

# 重新创建表结构
docker exec -i clickhouse clickhouse-client --multiquery < scripts/init_clickhouse_warehouse.sql 2>&1 | head -20
echo "✓ ClickHouse 表已重建"
echo

# 2. 验证 MySQL 数据（确保只有2026年的数据）
echo "【2/4】验证 MySQL 数据..."
docker exec mysql-source mysql -uroot -proot123 -e "USE ecommerce_ods; SELECT MIN(order_time) AS min_time, MAX(order_time) AS max_time, COUNT(*) AS count FROM ods_order_info;" 2>&1 | grep -v "Warning"
echo

# 3. 重新同步到 ClickHouse
echo "【3/4】重新同步到 ClickHouse..."
python3 scripts/sync_mysql_to_clickhouse.py
echo

# 4. 验证同步结果
echo "【4/4】验证同步结果..."
docker exec clickhouse clickhouse-client --query="SELECT '订单数据' AS info, min(order_date) AS min_date, max(order_date) AS max_date, count() AS total, countIf(order_date >= today() - 30) AS within_30_days FROM dwd_layer.fact_order_detail FORMAT PrettyCompact"
echo

echo "==========================================="
echo "✓ ClickHouse 清理并重新同步完成！"
echo "==========================================="
echo
echo "下一步："
echo "  python3 scripts/refresh_dws_layer.py"
echo "  python3 scripts/refresh_ads_layer.py"
echo