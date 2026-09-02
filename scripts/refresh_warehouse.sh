#!/bin/bash
# 刷新数据仓库各层数据（在宿主机运行 Python）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  数据仓库刷新脚本"
echo "======================================"
echo ""

# 检查 Docker 容器是否运行
if ! docker ps | grep -q clickhouse; then
    echo "✗ ClickHouse 容器未运行"
    echo "请先启动容器: docker-compose up -d"
    exit 1
fi

echo "✓ ClickHouse 容器运行中"
echo ""

# 检查 Python 依赖
if ! python3 -c "import clickhouse_connect" 2>/dev/null; then
    echo "⚠ 缺少 Python 依赖，正在安装..."
    pip3 install -q clickhouse-connect mysql-connector-python
fi

# 选择刷新层级
if [ "$1" == "dws" ]; then
    echo "执行 DWS 层刷新..."
    cd "$PROJECT_ROOT"
    python3 scripts/refresh_dws_layer.py
    
elif [ "$1" == "ads" ]; then
    echo "执行 ADS 层刷新..."
    cd "$PROJECT_ROOT"
    python3 scripts/refresh_ads_layer.py
    
elif [ "$1" == "full" ] || [ "$1" == "" ]; then
    echo "执行完整数据仓库刷新（DWD -> DWS -> ADS）..."
    cd "$PROJECT_ROOT"
    python3 scripts/refresh_warehouse.py
    
else
    echo "用法: $0 [dws|ads|full]"
    echo ""
    echo "  dws   - 仅刷新 DWS 层"
    echo "  ads   - 仅刷新 ADS 层"
    echo "  full  - 完整刷新所有层（默认）"
    exit 1
fi

echo ""
echo "======================================"
echo "✓ 刷新完成！"
echo "======================================"
echo ""
echo "验证数据:"
echo "  docker exec clickhouse clickhouse-client --query='SELECT * FROM ads_layer.gmv_dashboard ORDER BY dt DESC LIMIT 5 FORMAT Pretty'"
echo "  docker exec clickhouse clickhouse-client --query='SELECT user_type, count() FROM ads_layer.user_portrait GROUP BY user_type FORMAT Pretty'"
echo ""