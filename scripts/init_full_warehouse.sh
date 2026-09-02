#!/bin/bash
# ====================================
# 完整的数据仓库初始化与同步流程
# ====================================

set -e

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "========================================="
echo "AI Vector Data Warehouse - 完整初始化"
echo "========================================="
echo "项目根目录: ${PROJECT_ROOT}"
echo ""

# 步骤 1: 初始化 MySQL ODS
echo "步骤 1/4: 初始化 MySQL ODS 层..."

# 检查数据是否已存在
EXISTING_DATA=$(docker exec mysql-source mysql -uroot -proot123 -se "SELECT COUNT(*) FROM ecommerce_ods.ods_user_info" 2>/dev/null || echo "0")

if [ "$EXISTING_DATA" -gt 0 ]; then
    echo "⚠ 检测到已有数据 (${EXISTING_DATA} 条用户记录)"
    read -p "是否清空重新导入？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "清空 MySQL ODS 数据..."
        docker exec mysql-source mysql -uroot -proot123 -e "
        USE ecommerce_ods;
        SET FOREIGN_KEY_CHECKS = 0;
        TRUNCATE TABLE ods_user_info;
        TRUNCATE TABLE ods_product_info;
        TRUNCATE TABLE ods_order_info;
        TRUNCATE TABLE ods_order_detail;
        TRUNCATE TABLE ods_user_behavior;
        SET FOREIGN_KEY_CHECKS = 1;
        " 2>/dev/null
        echo "✓ 数据已清空"
    else
        echo "✓ 跳过 MySQL ODS 初始化（使用已有数据）"
        echo ""
        echo "步骤 2/4: 初始化 ClickHouse 数仓层（DWD/DWS/ADS/Vector）..."
        docker exec -i clickhouse clickhouse-client --multiquery < "${PROJECT_ROOT}/scripts/init_clickhouse_warehouse.sql" 2>/dev/null || echo "✓ ClickHouse 表已存在"
        echo "✓ ClickHouse 数仓层初始化完成"
        echo ""
        
        # 直接跳到步骤 3
        echo "步骤 3/4: 执行 CDC 数据同步..."
        cd "${PROJECT_ROOT}"
        pip3 install -q -r scripts/cdc_requirements.txt 2>/dev/null || echo "依赖已安装"
        python3 scripts/sync_mysql_to_clickhouse.py
        
        # 跳到步骤 4
        echo ""
        echo "步骤 4/4: 验证数据..."
        echo ""
        echo "MySQL ODS 层:"
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
        " 2>/dev/null
        
        echo ""
        echo "ClickHouse DWD 层:"
        docker exec clickhouse clickhouse-client --query="
        SELECT 'dim_user' AS table_name, count() AS count FROM dwd_layer.dim_user
        UNION ALL
        SELECT 'dim_product', count() FROM dwd_layer.dim_product
        UNION ALL
        SELECT 'fact_order_detail', count() FROM dwd_layer.fact_order_detail
        UNION ALL
        SELECT 'fact_user_behavior', count() FROM dwd_layer.fact_user_behavior
        FORMAT PrettyCompact
        "
        
        echo ""
        echo "========================================="
        echo "✓ 数据仓库初始化完成！"
        echo "========================================="
        echo ""
        echo "下一步："
        echo "  1. 查看 DWD 明细: docker exec clickhouse clickhouse-client --query='SELECT * FROM dwd_layer.fact_order_detail LIMIT 5 FORMAT Pretty'"
        echo "  2. 触发 DWS 汇总: python3 scripts/refresh_dws_layer.py"
        echo "  3. 生成 ADS 应用: python3 scripts/refresh_ads_layer.py"
        echo "  4. 访问 Web UI: http://localhost:8080"
        echo ""
        exit 0
    fi
fi

docker exec -i mysql-source mysql -uroot -proot123 --default-character-set=utf8mb4 < "${PROJECT_ROOT}/scripts/init_mysql_ods.sql"
echo "✓ MySQL ODS 初始化完成"
echo ""

# 步骤 2: 初始化 ClickHouse 数仓层
echo "步骤 2/4: 初始化 ClickHouse 数仓层（DWD/DWS/ADS/Vector）..."
docker exec -i clickhouse clickhouse-client --multiquery < "${PROJECT_ROOT}/scripts/init_clickhouse_warehouse.sql"
echo "✓ ClickHouse 数仓层初始化完成"
echo ""

# 步骤 3: 数据同步 MySQL -> ClickHouse
echo "步骤 3/4: 执行 CDC 数据同步..."
cd "${PROJECT_ROOT}"
pip3 install -q -r scripts/cdc_requirements.txt 2>/dev/null || echo "依赖已安装"
python3 scripts/sync_mysql_to_clickhouse.py
echo "✓ DWD 层数据同步完成"
echo ""

# 步骤 4: 验证数据
echo "步骤 4/4: 验证数据..."
echo ""
echo "MySQL ODS 层:"
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
" 2>/dev/null

echo ""
echo "ClickHouse DWD 层:"
docker exec clickhouse clickhouse-client --query="
SELECT 'dim_user' AS table_name, count() AS count FROM dwd_layer.dim_user
UNION ALL
SELECT 'dim_product', count() FROM dwd_layer.dim_product
UNION ALL
SELECT 'fact_order_detail', count() FROM dwd_layer.fact_order_detail
UNION ALL
SELECT 'fact_user_behavior', count() FROM dwd_layer.fact_user_behavior
FORMAT PrettyCompact
"

echo ""
echo "========================================="
echo "步骤 6: 刷新 DWS/ADS 层数据"
echo "========================================="

echo "执行完整数据仓库刷新..."
cd "${PROJECT_ROOT}"
python3 scripts/refresh_warehouse.py

echo ""
echo "========================================="
echo "步骤 7: 数据质量检查"
echo "========================================="

echo "运行数据质量监控..."
cd "${PROJECT_ROOT}"
python3 scripts/check_data_quality.py

echo ""
echo "========================================="
echo "✓ 数据仓库初始化完成！"
echo "========================================="
echo ""
echo "数据仓库分层架构："
echo "  ODS 层 (MySQL)    → 原始数据存储"
echo "  DWD 层 (ClickHouse) → 明细数据 + 维度表"
echo "  DWS 层 (ClickHouse) → 轻度聚合汇总"
echo "  ADS 层 (ClickHouse) → 面向业务应用"
echo ""
echo "快捷操作："
echo "  1. 查看 DWD 明细: docker exec clickhouse clickhouse-client --query='SELECT * FROM dwd_layer.fact_order_detail LIMIT 5 FORMAT Pretty'"
echo "  2. 查看 GMV 大屏: docker exec clickhouse clickhouse-client --query='SELECT * FROM ads_layer.gmv_dashboard ORDER BY dt DESC LIMIT 7 FORMAT Pretty'"
echo "  3. 查看用户画像: docker exec clickhouse clickhouse-client --query='SELECT user_type, count() FROM ads_layer.user_portrait GROUP BY user_type FORMAT Pretty'"
echo "  4. 刷新数据仓库: bash scripts/refresh_warehouse.sh full"
echo "  5. 数据质量监控: python3 scripts/check_data_quality.py"
echo "  6. 访问 Web UI: http://localhost:8080"
echo ""