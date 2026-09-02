#!/bin/bash
# ====================================
# 下载 Flink CDC 和 ClickHouse 连接器
# ====================================

set -e

FLINK_VERSION="1.18"
CDC_VERSION="3.0.1"
DOWNLOAD_DIR="./data/flink-lib"

echo "========================================="
echo "下载 Flink Connector JAR 包"
echo "========================================="

# 创建目录
mkdir -p ${DOWNLOAD_DIR}
cd ${DOWNLOAD_DIR}

echo ""
echo "Flink 版本: ${FLINK_VERSION}"
echo "CDC 版本: ${CDC_VERSION}"
echo "下载目录: $(pwd)"
echo ""

# 1. MySQL CDC Connector
echo "1. 下载 MySQL CDC Connector..."
if [ ! -f "flink-sql-connector-mysql-cdc-${CDC_VERSION}.jar" ]; then
    wget -c \
        https://repo1.maven.org/maven2/com/ververica/flink-sql-connector-mysql-cdc/${CDC_VERSION}/flink-sql-connector-mysql-cdc-${CDC_VERSION}.jar \
        && echo "✓ MySQL CDC Connector 下载完成" \
        || echo "⚠ 下载失败，请手动下载"
else
    echo "✓ MySQL CDC Connector 已存在"
fi

# 2. ClickHouse JDBC Driver
echo ""
echo "2. 下载 ClickHouse JDBC Driver..."
CLICKHOUSE_JDBC_VERSION="0.6.0"
if [ ! -f "clickhouse-jdbc-${CLICKHOUSE_JDBC_VERSION}-shaded.jar" ]; then
    wget -c \
        https://repo1.maven.org/maven2/com/clickhouse/clickhouse-jdbc/${CLICKHOUSE_JDBC_VERSION}/clickhouse-jdbc-${CLICKHOUSE_JDBC_VERSION}-shaded.jar \
        && echo "✓ ClickHouse JDBC Driver 下载完成" \
        || echo "⚠ 下载失败，请手动下载"
else
    echo "✓ ClickHouse JDBC Driver 已存在"
fi

# 3. Flink JDBC Connector (用于 ClickHouse sink)
echo ""
echo "3. 下载 Flink JDBC Connector..."
if [ ! -f "flink-connector-jdbc-3.1.2-1.18.jar" ]; then
    wget -c \
        https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar \
        && echo "✓ Flink JDBC Connector 下载完成" \
        || echo "⚠ 下载失败，请手动下载"
else
    echo "✓ Flink JDBC Connector 已存在"
fi

echo ""
echo "========================================="
echo "下载完成！"
echo "========================================="
echo ""
echo "已下载的 JAR 包："
ls -lh *.jar 2>/dev/null || echo "未找到 JAR 包，请手动下载"
echo ""
echo "下一步："
echo "  1. 重启 Flink 集群: docker-compose restart flink-jobmanager flink-taskmanager"
echo "  2. 提交 CDC 作业: docker exec -it flink-jobmanager bash /opt/flink-jobs/submit_cdc_job.sh"
echo ""