#!/bin/bash
# API 服务快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 检测 docker compose 命令（V2 使用空格，V1 使用连字符）
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ 错误: 未找到 docker-compose 或 docker compose 命令"
    exit 1
fi

echo "========================================="
echo "🚀 启动语义搜索 API 服务"
echo "========================================="
echo "   使用命令: $DOCKER_COMPOSE"

# 检查依赖服务
echo ""
echo "1️⃣  检查依赖服务..."

check_service() {
    local service=$1
    local port=$2
    
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        echo "   ✅ $service 运行中"
        return 0
    else
        echo "   ❌ $service 未运行"
        return 1
    fi
}

ALL_READY=true

check_service "clickhouse" "9000" || ALL_READY=false
check_service "redis" "6379" || ALL_READY=false
check_service "embedding-service" "8001" || ALL_READY=false

if [ "$ALL_READY" = false ]; then
    echo ""
    echo "⚠️  依赖服务未就绪，尝试启动..."
    $DOCKER_COMPOSE up -d clickhouse redis embedding-service
    echo "   等待服务启动..."
    sleep 5
fi

# 重建 API 服务
echo ""
echo "2️⃣  构建 API 服务..."
$DOCKER_COMPOSE build api-service

# 启动 API 服务
echo ""
echo "3️⃣  启动 API 服务..."
$DOCKER_COMPOSE up -d api-service

# 等待服务就绪
echo ""
echo "4️⃣  等待服务就绪..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/ready > /dev/null 2>&1; then
        echo "   ✅ API 服务已就绪"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "   ❌ API 服务启动超时"
        exit 1
    fi
    
    echo "   等待中... ($i/30)"
    sleep 2
done

# 显示服务信息
echo ""
echo "========================================="
echo "✅ API 服务启动成功"
echo "========================================="
echo ""
echo "📡 服务端点:"
echo "   - API Base: http://localhost:8000/api/v1"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - 健康检查: http://localhost:8000/api/v1/health"
echo "   - Prometheus: http://localhost:8000/metrics"
echo ""
echo "📚 API 文档: docs/API_REFERENCE.md"
echo ""
echo "🧪 运行测试:"
echo "   python3 scripts/test_api.py"
echo ""
echo "📊 查看日志:"
echo "   docker logs -f api-service"
echo ""
echo "========================================="