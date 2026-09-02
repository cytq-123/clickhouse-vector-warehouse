#!/bin/bash

# 完整的清理和重新初始化脚本

set -e

echo "======================================"
echo "清理并重新初始化数据仓库"
echo "======================================"
echo

# 1. 清空 MySQL 数据
echo "1. 清空 MySQL 数据..."
docker exec mysql-source mysql -uroot -proot123 --default-character-set=utf8mb4 <<EOF
USE ecommerce_ods;
TRUNCATE TABLE ods_user_info;
TRUNCATE TABLE ods_product_info;
TRUNCATE TABLE ods_order_detail;
TRUNCATE TABLE ods_order_info;
TRUNCATE TABLE ods_user_behavior;
EOF
echo "✓ MySQL 数据已清空"
echo

# 2. 清空 ClickHouse 数据
echo "2. 清空 ClickHouse 数据..."
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dwd_layer.dim_user"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dwd_layer.dim_product"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dwd_layer.fact_order_detail"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dwd_layer.fact_user_behavior"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dws_layer.trade_user_1d"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE dws_layer.product_sale_1d"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE ads_layer.user_portrait"
docker exec clickhouse clickhouse-client --query="TRUNCATE TABLE ads_layer.product_recommend"
echo "✓ ClickHouse 数据已清空"
echo

# 3. 重新导入 MySQL 数据
echo "3. 重新导入 MySQL 测试数据..."
docker exec -i mysql-source mysql -uroot -proot123 --default-character-set=utf8mb4 < scripts/init_mysql_ods.sql
echo "✓ MySQL 数据导入完成"
echo

# 4. 同步到 ClickHouse DWD 层
echo "4. 同步数据到 ClickHouse DWD 层..."
python3 scripts/sync_mysql_to_clickhouse.py
echo

# 5. 刷新 DWS 层
echo "5. 刷新 DWS 层..."
python3 scripts/refresh_dws_layer.py
echo

# 6. 刷新 ADS 层
echo "6. 刷新 ADS 层..."
python3 scripts/refresh_ads_layer.py
echo

# 7. 验证数据
echo "======================================"
echo "数据验证"
echo "======================================"
echo

echo "MySQL 数据统计:"
docker exec mysql-source mysql -uroot -proot123 -e "
USE ecommerce_ods;
SELECT 'ods_user_info' AS table_name, COUNT(*) AS count FROM ods_user_info
UNION ALL
SELECT 'ods_product_info', COUNT(*) FROM ods_product_info
UNION ALL
SELECT 'ods_order_info', COUNT(*) FROM ods_order_info
UNION ALL
SELECT 'ods_order_detail', COUNT(*) FROM ods_order_detail
UNION ALL
SELECT 'ods_user_behavior', COUNT(*) FROM ods_user_behavior;
"
echo

echo "ClickHouse DWD 层:"
docker exec clickhouse clickhouse-client --query="
SELECT 'dim_user' AS table_name, count() AS count FROM dwd_layer.dim_user
UNION ALL
SELECT 'dim_product', count() FROM dwd_layer.dim_product
UNION ALL
SELECT 'fact_order_detail', count() FROM dwd_layer.fact_order_detail
UNION ALL
SELECT 'fact_user_behavior', count() FROM dwd_layer.fact_user_behavior
FORMAT Pretty
"
echo

echo "ClickHouse DWS 层:"
docker exec clickhouse clickhouse-client --query="
SELECT 'trade_user_1d' AS table_name, count() AS count FROM dws_layer.trade_user_1d
UNION ALL
SELECT 'product_sale_1d', count() FROM dws_layer.product_sale_1d
FORMAT Pretty
"
echo

echo "ClickHouse ADS 层:"
docker exec clickhouse clickhouse-client --query="
SELECT 'user_portrait' AS table_name, count() AS count FROM ads_layer.user_portrait
UNION ALL
SELECT 'product_recommend', count() FROM ads_layer.product_recommend
FORMAT Pretty
"
echo

echo "======================================"
echo "✓ 清理和重新初始化完成！"
echo "======================================"