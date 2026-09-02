<template>
  <div>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <div class="stat-box">
            <div class="value">{{ stats.users }}</div>
            <div class="label">用户数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-box">
            <div class="value">{{ stats.products }}</div>
            <div class="label">商品数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-box">
            <div class="value">{{ stats.orders }}</div>
            <div class="label">订单数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-box">
            <div class="value">{{ stats.vectors }}</div>
            <div class="label">向量数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>各层数据统计</span>
      </template>
      <el-table :data="tableStats" v-loading="loading">
        <el-table-column prop="layer" label="数据层" width="120" />
        <el-table-column prop="name" label="表名" />
        <el-table-column prop="count" label="记录数" width="120" />
        <el-table-column prop="desc" label="说明" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { queryClickHouse } from '../api/clickhouse'

const stats = ref({ users: 0, products: 0, orders: 0, vectors: 0 })
const tableStats = ref([])
const loading = ref(true)

onMounted(async () => {
  // 加载统计数据
  const [users, products, orders, vectors] = await Promise.all([
    queryClickHouse('SELECT count() as cnt FROM dwd_layer.dim_user'),
    queryClickHouse('SELECT count() as cnt FROM dwd_layer.dim_product'),
    queryClickHouse('SELECT count() as cnt FROM dwd_layer.fact_order_detail'),
    queryClickHouse('SELECT count() as cnt FROM vector_layer.semantic_product')
  ])

  stats.value = {
    users: users[0]?.cnt || 0,
    products: products[0]?.cnt || 0,
    orders: orders[0]?.cnt || 0,
    vectors: vectors[0]?.cnt || 0
  }

  // 加载表统计
  const tables = [
    { layer: 'DWD', db: 'dwd_layer', name: 'dim_user', desc: '用户维度' },
    { layer: 'DWD', db: 'dwd_layer', name: 'dim_product', desc: '商品维度' },
    { layer: 'DWD', db: 'dwd_layer', name: 'fact_order_detail', desc: '订单明细' },
    { layer: 'DWD', db: 'dwd_layer', name: 'fact_user_behavior', desc: '用户行为' },
    { layer: 'DWS', db: 'dws_layer', name: 'trade_user_1d', desc: '用户交易日汇总' },
    { layer: 'DWS', db: 'dws_layer', name: 'product_sale_1d', desc: '商品销售日汇总' },
    { layer: 'ADS', db: 'ads_layer', name: 'user_portrait', desc: '用户画像' },
    { layer: 'ADS', db: 'ads_layer', name: 'product_recommend', desc: '商品推荐' },
    { layer: 'ADS', db: 'ads_layer', name: 'gmv_dashboard', desc: 'GMV大屏' },
    { layer: 'Vector', db: 'vector_layer', name: 'semantic_product', desc: '商品向量' }
  ]

  const results = await Promise.all(
    tables.map(t => queryClickHouse(`SELECT count() as cnt FROM ${t.db}.${t.name}`))
  )

  tableStats.value = tables.map((t, i) => ({
    ...t,
    count: results[i][0]?.cnt || 0
  }))

  loading.value = false
})
</script>

<style scoped>
.stat-box {
  text-align: center;
  padding: 20px 0;
}

.stat-box .value {
  font-size: 2.5em;
  font-weight: bold;
  color: #409eff;
}

.stat-box .label {
  margin-top: 10px;
  color: #666;
}
</style>