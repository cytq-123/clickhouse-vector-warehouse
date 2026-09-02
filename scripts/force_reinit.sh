#!/bin/bash

set -e

echo "==========================================="
echo "强制清理并重新初始化完整数据仓库"
echo "==========================================="
echo

# 1. 清空所有 MySQL 表
echo "【1/7】清空 MySQL ODS 层..."
docker exec mysql-source mysql -uroot -proot123 <<'EOF'
USE ecommerce_ods;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE ods_user_info;
TRUNCATE TABLE ods_product_info;
TRUNCATE TABLE ods_order_info;
TRUNCATE TABLE ods_order_detail;
TRUNCATE TABLE ods_user_behavior;
SET FOREIGN_KEY_CHECKS = 1;
EOF
echo "✓ MySQL 数据已清空"
echo

# 2. 清空所有 ClickHouse 表
echo "【2/7】清空 ClickHouse 所有层..."
docker exec clickhouse clickhouse-client --multiquery <<'EOF'
TRUNCATE TABLE dwd_layer.dim_user;
TRUNCATE TABLE dwd_layer.dim_product;
TRUNCATE TABLE dwd_layer.fact_order_detail;
TRUNCATE TABLE dwd_layer.fact_user_behavior;
TRUNCATE TABLE dws_layer.trade_user_1d;
TRUNCATE TABLE dws_layer.product_sale_1d;
TRUNCATE TABLE ads_layer.user_portrait;
TRUNCATE TABLE ads_layer.product_recommend;
EOF
echo "✓ ClickHouse 数据已清空"
echo

# 3. 重新导入 MySQL 数据
echo "【3/7】导入 MySQL 测试数据..."
docker exec -i mysql-source mysql -uroot -proot123 --default-character-set=utf8mb4 < scripts/init_mysql_ods.sql 2>&1 | grep -v "Warning: Using a password on the command line"
echo "✓ MySQL 数据导入完成"
echo

# 4. 验证 MySQL 数据和日期范围
echo "【4/7】验证 MySQL 数据..."
docker exec mysql-source mysql -uroot -proot123 -e "
USE ecommerce_ods;
SELECT '用户数' AS metric, COUNT(*) AS count FROM ods_user_info
UNION ALL
SELECT '商品数', COUNT(*) FROM ods_product_info
UNION ALL
SELECT '订单数', COUNT(*) FROM ods_order_info
UNION ALL
SELECT '订单明细', COUNT(*) FROM ods_order_detail
UNION ALL
SELECT '用户行为', COUNT(*) FROM ods_user_behavior;
" 2>&1 | grep -v "Warning"

docker exec mysql-source mysql -uroot -proot123 -e "
USE ecommerce_ods;
SELECT '订单日期范围' AS info, 
       MIN(order_time) AS min_time, 
       MAX(order_time) AS max_time 
FROM ods_order_info;
" 2>&1 | grep -v "Warning"
echo
echo

# 5. 同步到 ClickHouse DWD 层
echo "【5/7】同步数据到 ClickHouse DWD 层..."
python3 scripts/sync_mysql_to_clickhouse.py
echo

# 6. 刷新 DWS 层
echo "【6/7】刷新 DWS 汇总层..."
python3 scripts/refresh_dws_layer.py
echo

# 7. 刷新 ADS 层
echo "【7/7】刷新 ADS 应用层..."
python3 scripts/refresh_ads_layer.py
echo

# 最终验证
echo "==========================================="
echo "最终数据验证"
echo "==========================================="
echo

echo "ClickHouse 各层数据统计:"
docker exec clickhouse clickhouse-client --query="
SELECT '【DWD】dim_user' AS layer_table, count() AS count FROM dwd_layer.dim_user
UNION ALL SELECT '【DWD】dim_product', count() FROM dwd_layer.dim_product
UNION ALL SELECT '【DWD】fact_order_detail', count() FROM dwd_layer.fact_order_detail
UNION ALL SELECT '【DWD】fact_user_behavior', count() FROM dwd_layer.fact_user_behavior
UNION ALL SELECT '【DWS】trade_user_1d', count() FROM dws_layer.trade_user_1d
UNION ALL SELECT '【DWS】product_sale_1d', count() FROM dws_layer.product_sale_1d
UNION ALL SELECT '【ADS】user_portrait', count() FROM ads_layer.user_portrait
UNION ALL SELECT '【ADS】product_recommend', count() FROM ads_layer.product_recommend
FORMAT PrettyCompact
"
echo

echo "DWD 订单明细日期范围:"
docker exec clickhouse clickhouse-client --query="
SELECT 
    min(order_date) AS min_date,
    max(order_date) AS max_date,
    dateDiff('day', min(order_date), max(order_date)) AS date_span_days,
    dateDiff('day', max(order_date), today()) AS days_ago
FROM dwd_layer.fact_order_detail
FORMAT PrettyCompact
"
echo

echo "==========================================="
echo "✓ 完整数据仓库重新初始化完成！"
echo "==========================================="
echo
echo "如果 DWS/ADS 层仍然为 0，请检查:"
echo "  1. order_date 是否在最近 30 天内"
echo "  2. 运行: docker exec clickhouse clickhouse-client --query='SELECT order_date, count() FROM dwd_layer.fact_order_detail GROUP BY order_date FORMAT Pretty'"
echo