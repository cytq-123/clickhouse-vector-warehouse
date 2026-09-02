<template>
  <div>
    <el-card>
      <template #header>
        <span>用户维度表 (dim_user)</span>
      </template>
      <el-table :data="users" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column prop="city" label="城市" />
        <el-table-column prop="user_level" label="等级" width="80" />
      </el-table>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>商品维度表 (dim_product)</span>
      </template>
      <el-table :data="products" v-loading="loading">
        <el-table-column prop="product_id" label="商品ID" width="100" />
        <el-table-column prop="product_name" label="商品名称" />
        <el-table-column prop="category_1" label="一级类目" />
        <el-table-column prop="category_2" label="二级类目" />
        <el-table-column prop="brand" label="品牌" />
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">
            ¥{{ row.price }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { queryClickHouse } from '../api/clickhouse'

const users = ref([])
const products = ref([])
const loading = ref(true)

onMounted(async () => {
  const [u, p] = await Promise.all([
    queryClickHouse('SELECT * FROM dwd_layer.dim_user LIMIT 20'),
    queryClickHouse('SELECT * FROM dwd_layer.dim_product LIMIT 20')
  ])
  users.value = u
  products.value = p
  loading.value = false
})
</script>