#!/bin/bash

# ====================================
# 实时向量数仓 - 一键启动脚本
# Linux/Mac/虚拟机通用
# ====================================

set -e

echo "=========================================="
echo "实时向量数仓 - MVP 启动脚本"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未安装 Docker"
    echo "请运行: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查 Docker Compose（兼容新旧版本）
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ 错误: 未安装 Docker Compose"
    echo "请运行: sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo "使用 Docker Compose: $DOCKER_COMPOSE"

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "❌ 错误: Docker 服务未运行"
    echo "请运行: sudo systemctl start docker"
    exit 1
fi

# 创建数据目录
echo ""
echo "[1/6] 创建数据目录..."
mkdir -p data/clickhouse
mkdir -p data/redis
mkdir -p data/mysql
mkdir -p data/flink-checkpoints
mkdir -p data/models
mkdir -p data/prometheus
mkdir -p data/grafana

# 启动基础服务
echo ""
echo "[2/6] 启动基础服务（ClickHouse, Redis, MySQL）..."
$DOCKER_COMPOSE up -d clickhouse redis mysql

echo "⏳ 等待数据库启动（30秒）..."
sleep 30

# 检查服务状态
echo "检查服务状态..."
$DOCKER_COMPOSE ps

# 初始化 ClickHouse
echo ""
echo "[3/6] 初始化 ClickHouse 表结构..."
if docker exec -i clickhouse clickhouse-client --multiquery < scripts/init_clickhouse.sql; then
    echo "✅ ClickHouse 初始化完成！"
else
    echo "⚠️  ClickHouse 初始化失败，可能需要手动执行"
fi

# 启动 Embedding 服务
echo ""
echo "[4/6] 启动 Embedding 服务..."
$DOCKER_COMPOSE up -d embedding-service

echo "⏳ 等待 Embedding 模型加载..."
echo "   首次启动会下载 bge-large-zh-v1.5 模型（约 1GB）"
echo "   可以运行 'docker-compose logs -f embedding-service' 查看进度"
sleep 60

# 启动 API 服务
echo ""
echo "[5/6] 启动查询 API 服务..."
$DOCKER_COMPOSE up -d api-service

echo "⏳ 等待 API 服务启动（10秒）..."
sleep 10

# 启动监控服务
echo ""
echo "[6/6] 启动监控服务（Prometheus, Grafana）..."
$DOCKER_COMPOSE up -d prometheus grafana

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成！"
echo "=========================================="
echo ""
echo "📊 服务访问地址："
echo "  - 查询 API:        http://localhost:8000"
echo "  - API 文档:        http://localhost:8000/docs"
echo "  - 健康检查:        http://localhost:8000/api/v1/health"
echo "  - Grafana 监控:    http://localhost:3000 (admin/admin)"
echo "  - Prometheus:      http://localhost:9090"
echo ""
echo "🧪 测试查询："
echo '  curl -X POST http://localhost:8000/api/v1/search \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{"query": "ClickHouse 性能优化", "top_k": 3}'\'
echo ""
echo "📋 查看日志："
echo "  $DOCKER_COMPOSE logs -f                  # 所有服务"
echo "  $DOCKER_COMPOSE logs -f api-service      # API 服务"
echo "  $DOCKER_COMPOSE logs -f embedding-service # Embedding 服务"
echo ""
echo "🔍 查看服务状态："
echo "  $DOCKER_COMPOSE ps"
echo ""
echo "🛑 停止服务："
echo "  $DOCKER_COMPOSE down          # 停止并删除容器"
echo "  $DOCKER_COMPOSE stop          # 仅停止容器（保留数据）"
echo ""
echo "🧹 完全清理（包括数据）："
echo "  $DOCKER_COMPOSE down -v && rm -rf data/"
echo "=========================================="