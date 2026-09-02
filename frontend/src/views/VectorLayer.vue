<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>🔍 语义搜索</span>
          <el-space>
            <el-tag v-if="searchStats.latency_ms">{{ searchStats.latency_ms }}ms</el-tag>
            <el-tag v-if="searchStats.cache_hit" type="success">缓存命中</el-tag>
            <el-tag v-if="searchStats.total > 0">{{ searchStats.total }} 个结果</el-tag>
          </el-space>
        </div>
      </template>
      
      <el-row :gutter="20" style="margin-bottom: 15px">
        <el-col :span="18">
          <el-input
            v-model="searchQuery"
            placeholder="输入搜索内容，例如：降噪耳机、运动鞋、适合办公的笔记本..."
            size="large"
            @keyup.enter="search"
          >
            <template #append>
              <el-button @click="search" :loading="searching" type="primary">
                🔍 搜索
              </el-button>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select v-model="searchMode" placeholder="检索模式" size="large">
            <el-option label="混合检索（推荐）" value="hybrid" />
            <el-option label="向量检索" value="vector" />
            <el-option label="关键词检索" value="keyword" />
          </el-select>
        </el-col>
      </el-row>

      <el-collapse v-model="activeFilters" style="margin-bottom: 15px">
        <el-collapse-item title="高级过滤" name="filters">
          <el-form :inline="true" size="small">
            <el-form-item label="类目">
              <el-select v-model="filters.category_1" clearable placeholder="全部">
                <el-option label="数码" value="数码" />
                <el-option label="服饰" value="服饰" />
                <el-option label="食品" value="食品" />
              </el-select>
            </el-form-item>
            <el-form-item label="品牌">
              <el-input v-model="filters.brand" clearable placeholder="输入品牌" style="width: 150px" />
            </el-form-item>
            <el-form-item label="价格范围">
              <el-input-number v-model="filters.min_price" :min="0" placeholder="最低" style="width: 120px" />
              <span style="margin: 0 5px">-</span>
              <el-input-number v-model="filters.max_price" :min="0" placeholder="最高" style="width: 120px" />
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
      
      <div v-if="searchResults.length" style="margin-top: 20px">
        <el-table :data="searchResults" stripe>
          <el-table-column prop="product_id" label="ID" width="80" />
          <el-table-column prop="product_name" label="商品名称" min-width="200" />
          <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
          <el-table-column prop="category_1" label="类目" width="100" />
          <el-table-column prop="brand" label="品牌" width="120" />
          <el-table-column prop="price" label="价格" width="100" align="right">
            <template #default="{ row }">
              <span style="color: #f56c6c; font-weight: bold">¥{{ row.price.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="similarity_score" label="相似度" width="100" align="center">
            <template #default="{ row }">
              <el-progress 
                :percentage="Math.round(row.similarity_score * 100)" 
                :color="getScoreColor(row.similarity_score)"
                :stroke-width="8"
              />
            </template>
          </el-table-column>
          <el-table-column prop="match_reason" label="匹配方式" width="100" align="center">
            <template #default="{ row }">
              <el-tag 
                :type="row.match_reason === 'hybrid' ? 'success' : row.match_reason === 'vector' ? 'primary' : 'warning'"
                size="small"
              >
                {{ row.match_reason }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button 
                size="small" 
                @click="recommend(row.product_id)"
                :icon="'MagicStick'"
              >
                推荐
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-empty 
        v-else-if="!searching && searchQuery" 
        description="未找到匹配的商品"
        :image-size="100"
      />
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>商品向量表 (semantic_product)</span>
          <el-button size="small" @click="syncVectors" :loading="syncing">
            🔄 同步向量
          </el-button>
        </div>
      </template>
      <el-table :data="vectors" v-loading="loading" stripe>
        <el-table-column prop="product_id" label="商品ID" width="100" />
        <el-table-column prop="product_name" label="商品名称" min-width="200" />
        <el-table-column prop="category_1" label="类目" width="100" />
        <el-table-column prop="brand" label="品牌" width="120" />
        <el-table-column prop="vec_dim" label="向量维度" width="120">
          <template #default="{ row }">
            {{ row.vec_dim }} 维
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 统计信息卡片 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="向量商品总数" :value="stats.total_vector_products || 0">
            <template #prefix>
              <el-icon><Box /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="类目数量" :value="Object.keys(stats.products_by_category || {}).length">
            <template #prefix>
              <el-icon><FolderOpened /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="品牌数量" :value="Object.keys(stats.top_brands || {}).length">
            <template #prefix>
              <el-icon><ShoppingCart /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { queryClickHouse, searchProducts, recommendProducts, vectorizeProducts, getStats } from '../api/clickhouse'
import { ElMessage } from 'element-plus'

const vectors = ref([])
const loading = ref(true)
const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)
const searchMode = ref('hybrid')
const activeFilters = ref([])
const filters = ref({
  category_1: null,
  brand: null,
  min_price: null,
  max_price: null
})
const searchStats = ref({
  latency_ms: 0,
  cache_hit: false,
  total: 0
})
const stats = ref({})
const syncing = ref(false)

onMounted(async () => {
  await loadVectors()
  await loadStats()
})

async function loadVectors() {
  loading.value = true
  try {
    const v = await queryClickHouse(`
      SELECT product_id, product_name, category_1, brand, length(embedding) as vec_dim
      FROM vector_layer.semantic_product 
      ORDER BY product_id
      LIMIT 50
    `)
    vectors.value = v
  } catch (error) {
    ElMessage.error('加载向量表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getStats()
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

async function search() {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  searching.value = true
  try {
    // 构建过滤条件
    const searchFilters = {}
    if (filters.value.category_1) searchFilters.category_1 = filters.value.category_1
    if (filters.value.brand) searchFilters.brand = filters.value.brand
    if (filters.value.min_price) searchFilters.min_price = filters.value.min_price
    if (filters.value.max_price) searchFilters.max_price = filters.value.max_price

    const result = await searchProducts({
      query: searchQuery.value,
      search_mode: searchMode.value,
      top_k: 20,
      filters: Object.keys(searchFilters).length > 0 ? searchFilters : null
    })

    searchResults.value = result.results
    searchStats.value = {
      latency_ms: result.latency_ms,
      cache_hit: result.cache_hit,
      total: result.total
    }

    if (result.total === 0) {
      ElMessage.info('未找到匹配的商品，请尝试其他关键词')
    } else {
      ElMessage.success(`找到 ${result.total} 个商品，耗时 ${result.latency_ms}ms`)
    }
  } catch (error) {
    ElMessage.error('搜索失败: ' + (error.response?.data?.detail || error.message))
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

async function recommend(productId) {
  searching.value = true
  try {
    const result = await recommendProducts(productId, 10, false)
    
    searchResults.value = result.results
    searchStats.value = {
      latency_ms: result.latency_ms,
      cache_hit: result.cache_hit,
      total: result.total
    }
    searchQuery.value = `商品 ${productId} 的推荐`

    ElMessage.success(`为您推荐 ${result.total} 个相似商品`)
  } catch (error) {
    ElMessage.error('推荐失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    searching.value = false
  }
}

async function syncVectors() {
  syncing.value = true
  try {
    // 获取所有商品 ID
    const products = await queryClickHouse(`
      SELECT product_id 
      FROM dwd_layer.dim_product 
      ORDER BY product_id
    `)
    
    if (products.length === 0) {
      ElMessage.warning('DWD 层没有商品数据')
      return
    }

    const productIds = products.map(p => p.product_id)
    
    ElMessage.info(`开始向量化 ${productIds.length} 个商品...`)
    
    const result = await vectorizeProducts(productIds)
    
    ElMessage.success(
      `向量化完成！成功: ${result.success_count}, 失败: ${result.failed_count}, 耗时: ${result.latency_ms}ms`
    )
    
    // 刷新数据
    await loadVectors()
    await loadStats()
  } catch (error) {
    ElMessage.error('向量同步失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncing.value = false
  }
}

function getScoreColor(score) {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.5) return '#409eff'
  if (score >= 0.3) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.el-statistic {
  text-align: center;
}
</style>