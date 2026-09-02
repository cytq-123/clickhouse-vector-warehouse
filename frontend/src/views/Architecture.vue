<template>
  <div>
    <el-card>
      <template #header>
        <span>数据仓库架构</span>
      </template>
      
      <div class="layer-box">
        <h3>📁 ODS 层 (MySQL)</h3>
        <p><strong>Operational Data Store - 操作数据层</strong></p>
        <p>业务系统源数据，包括用户、商品、订单、行为日志等原始数据。</p>
        <el-tag type="info">ods_user_info</el-tag>
        <el-tag type="info">ods_product_info</el-tag>
        <el-tag type="info">ods_order_info</el-tag>
        <el-tag type="info">ods_order_detail</el-tag>
        <el-tag type="info">ods_user_behavior</el-tag>
      </div>

      <div class="layer-box">
        <h3>🔹 DWD 层 (ClickHouse)</h3>
        <p><strong>Data Warehouse Detail - 数据仓库明细层</strong></p>
        <p>清洗、转换后的明细数据，构建维度表和事实表，使用 ReplacingMergeTree 引擎。</p>
        <el-tag type="primary">dim_user</el-tag>
        <el-tag type="primary">dim_product</el-tag>
        <el-tag type="primary">fact_order_detail</el-tag>
        <el-tag type="primary">fact_user_behavior</el-tag>
      </div>

      <div class="layer-box">
        <h3>🔸 DWS 层 (ClickHouse)</h3>
        <p><strong>Data Warehouse Service - 数据仓库服务层</strong></p>
        <p>预聚合数据,按主题域汇总,使用 AggregatingMergeTree 引擎提升查询性能。</p>
        <el-tag type="success">trade_user_1d</el-tag>
        <el-tag type="success">product_sale_1d</el-tag>
      </div>

      <div class="layer-box">
        <h3>📈 ADS 层 (ClickHouse)</h3>
        <p><strong>Application Data Service - 应用数据层</strong></p>
        <p>面向业务的应用数据,包括用户画像、商品排行、销售趋势、智能推荐等。</p>
        <el-tag type="warning">user_portrait</el-tag>
        <el-tag type="warning">product_recommend</el-tag>
        <el-tag type="warning">gmv_dashboard</el-tag>
        <el-tag type="warning">product_recommend</el-tag>
      </div>

      <div class="layer-box">
        <h3>🔍 Vector 层 (ClickHouse + BGE)</h3>
        <p><strong>Semantic Vector Layer - 语义向量层</strong></p>
        <p>使用 BGE-large-zh-v1.5 模型将文本转换为 1024 维向量，实现语义检索和智能推荐。</p>
        <el-tag type="danger">semantic_product</el-tag>
        <el-tag type="danger">semantic_order</el-tag>
        <el-tag type="danger">query_logs</el-tag>
      </div>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>技术栈</span>
      </template>
      <el-table :data="techStack">
        <el-table-column prop="component" label="组件" width="150" />
        <el-table-column prop="tech" label="技术" width="200" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const techStack = ref([
  { component: '数据源', tech: 'MySQL 8.0', desc: '模拟电商业务系统' },
  { component: '数据仓库', tech: 'ClickHouse 24.1', desc: '列式存储，OLAP 查询引擎' },
  { component: '向量模型', tech: 'BGE-large-zh-v1.5', desc: '中文语义向量化，1024 维' },
  { component: 'API 服务', tech: 'FastAPI', desc: 'RESTful API，异步高性能' },
  { component: '缓存', tech: 'Redis 7.2', desc: '查询缓存，向量缓存' },
  { component: '监控', tech: 'Prometheus + Grafana', desc: '性能监控，可视化' },
  { component: 'CDC', tech: 'Flink 1.18 / Python', desc: '实时/批量数据同步' },
  { component: '前端', tech: 'Vue 3 + Element Plus', desc: '现代化 UI 框架' }
])
</script>

<style scoped>
.layer-box {
  background: #f5f7fa;
  border-left: 4px solid #409eff;
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.layer-box h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #303133;
}

.layer-box p {
  margin: 8px 0;
  line-height: 1.6;
  color: #606266;
}

.layer-box .el-tag {
  margin-right: 8px;
  margin-top: 8px;
}
</style>