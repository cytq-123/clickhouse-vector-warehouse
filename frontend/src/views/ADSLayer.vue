<template>
  <div>
    <el-card>
      <template #header>
        <span>用户画像 (user_portrait)</span>
      </template>
      <el-table :data="portraits" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="username" label="用户名" width="100" />
        <el-table-column prop="user_type" label="用户类型" width="120" />
        <el-table-column prop="rfm_score" label="RFM分值" width="100" />
        <el-table-column prop="recency" label="距上次消费(天)" width="130" />
        <el-table-column prop="frequency" label="消费次数" width="100" />
        <el-table-column prop="monetary" label="累计金额" width="110" />
        <el-table-column prop="prefer_category" label="偏好类目" width="150">
          <template #default="{ row }">
            {{ Array.isArray(row.prefer_category) ? row.prefer_category.join(', ') : row.prefer_category }}
          </template>
        </el-table-column>
        <el-table-column prop="prefer_brand" label="偏好品牌" width="150">
          <template #default="{ row }">
            {{ Array.isArray(row.prefer_brand) ? row.prefer_brand.join(', ') : row.prefer_brand }}
          </template>
        </el-table-column>
        <el-table-column prop="prefer_price_range" label="价格偏好" width="100" />
      </el-table>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>商品推荐 (product_recommend)</span>
      </template>
      <el-table :data="recommends" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="product_id" label="推荐商品" width="100" />
        <el-table-column prop="product_name" label="商品名称" width="200" />
        <el-table-column prop="recommend_score" label="推荐分数" width="110" />
        <el-table-column prop="recommend_reason" label="推荐理由" />
        <el-table-column prop="recommend_time" label="生成时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { queryClickHouse } from '../api/clickhouse'

const portraits = ref([])
const recommends = ref([])
const loading = ref(true)

onMounted(async () => {
  const [p, r] = await Promise.all([
    queryClickHouse('SELECT * FROM ads_layer.user_portrait ORDER BY rfm_score DESC LIMIT 20'),
    queryClickHouse('SELECT * FROM ads_layer.product_recommend ORDER BY recommend_time DESC LIMIT 20')
  ])
  portraits.value = p
  recommends.value = r
  loading.value = false
})
</script>