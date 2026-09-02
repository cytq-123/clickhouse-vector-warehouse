import axios from 'axios'

// ClickHouse 客户端
const clickhouse = axios.create({
  baseURL: '/clickhouse',
  timeout: 10000
})

// API 服务客户端（新增）
const apiService = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export async function queryClickHouse(sql) {
  try {
    const response = await clickhouse.post('/', sql + ' FORMAT JSON', {
      params: {
        user: 'admin',
        password: 'admin123'
      }
    })
    return response.data.data || []
  } catch (error) {
    console.error('ClickHouse query failed:', error)
    return []
  }
}

// ==================== 语义搜索 API ====================

/**
 * 商品语义搜索
 * @param {Object} params - 搜索参数
 * @param {string} params.query - 搜索文本
 * @param {string} params.search_mode - 搜索模式：vector/keyword/hybrid
 * @param {number} params.top_k - 返回结果数
 * @param {Object} params.filters - 过滤条件
 * @returns {Promise<Object>} 搜索结果
 */
export async function searchProducts(params) {
  try {
    const response = await apiService.post('/products/search', {
      query: params.query,
      search_mode: params.search_mode || 'hybrid',
      top_k: params.top_k || 10,
      use_cache: params.use_cache !== false,
      filters: params.filters || null
    })
    return response.data
  } catch (error) {
    console.error('Product search failed:', error)
    throw error
  }
}

/**
 * 商品推荐
 * @param {number} productId - 商品 ID
 * @param {number} topK - 推荐数量
 * @param {boolean} excludeSameCategory - 是否排除同类目
 * @returns {Promise<Object>} 推荐结果
 */
export async function recommendProducts(productId, topK = 5, excludeSameCategory = false) {
  try {
    const response = await apiService.post('/products/recommend', {
      product_id: productId,
      top_k: topK,
      exclude_same_category: excludeSameCategory
    })
    return response.data
  } catch (error) {
    console.error('Product recommendation failed:', error)
    throw error
  }
}

/**
 * 批量向量化商品
 * @param {number[]} productIds - 商品 ID 列表
 * @returns {Promise<Object>} 向量化结果
 */
export async function vectorizeProducts(productIds) {
  try {
    const response = await apiService.post('/products/vectorize', {
      product_ids: productIds
    })
    return response.data
  } catch (error) {
    console.error('Product vectorization failed:', error)
    throw error
  }
}

/**
 * 获取统计信息
 * @returns {Promise<Object>} 统计数据
 */
export async function getStats() {
  try {
    const response = await apiService.get('/stats')
    return response.data
  } catch (error) {
    console.error('Get stats failed:', error)
    throw error
  }
}

/**
 * 健康检查
 * @returns {Promise<Object>} 健康状态
 */
export async function healthCheck() {
  try {
    const response = await apiService.get('/health')
    return response.data
  } catch (error) {
    console.error('Health check failed:', error)
    throw error
  }
}