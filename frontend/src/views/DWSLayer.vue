<template>
  <div>
    <el-card>
      <template #header>
        <span>用户交易日汇总 (trade_user_1d)</span>
      </template>
      <el-table :data="userOrders" v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="100" />
        <el-table-column prop="dt" label="日期" width="120" />
        <el-table-column prop="order_count" label="订单数" width="100" />
        <el-table-column prop="payment_count" label="支付数" width="100" />
        <el-table-column prop="total_amount" label="总金额" />
        <el-table-column prop="product_count" label="商品数" width="100" />
        <el-table-column prop="avg_price" label="平均单价" />
      </el-table>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>商品销售日汇总 (product_sale_1d)</span>
      </template>
      <el-table :data="productSales" v-loading="loading">
        <el-table-column prop="product_id" label="商品ID" width="100" />
        <el-table-column prop="dt" label="日期" width="120" />
        <el-table-column prop="order_count" label="订单数" width="100" />
        <el-table-column prop="sale_count" label="销售量" />
        <el-table-column prop="sale_amount" label="销售额" />
        <el-table-column prop="view_count" label="浏览数" width="100" />
        <el-table-column prop="cart_count" label="加购数" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { queryClickHouse } from '../api/clickhouse'

const userOrders = ref([])
const productSales = ref([])
const loading = ref(true)

onMounted(async () => {
  const [uo, ps] = await Promise.all([
    queryClickHouse('SELECT * FROM dws_layer.trade_user_1d ORDER BY dt DESC, total_amount DESC LIMIT 20'),
    queryClickHouse('SELECT * FROM dws_layer.product_sale_1d ORDER BY dt DESC, sale_amount DESC LIMIT 20')
  ])
  userOrders.value = uo
  productSales.value = ps
  loading.value = false
})
</script>