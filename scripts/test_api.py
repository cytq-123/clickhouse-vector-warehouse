#!/usr/bin/env python3
"""
语义搜索 API 测试脚本
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

def print_result(name: str, result: Dict[Any, Any], success: bool = True):
    """打印测试结果"""
    status = "✅" if success else "❌"
    print(f"\n{status} {name}")
    print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")

def test_health_check():
    """测试健康检查"""
    print("\n" + "="*60)
    print("测试 1: 健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        result = response.json()
        
        success = result.get("status") in ["healthy", "degraded"]
        print_result("健康检查", result, success)
        
        return success
    except Exception as e:
        print_result("健康检查", {"error": str(e)}, False)
        return False

def test_stats():
    """测试统计信息"""
    print("\n" + "="*60)
    print("测试 2: 统计信息")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/stats", timeout=10)
        result = response.json()
        
        success = "total_vector_products" in result
        print_result("统计信息", result, success)
        
        return success
    except Exception as e:
        print_result("统计信息", {"error": str(e)}, False)
        return False

def test_batch_vectorize():
    """测试批量向量化"""
    print("\n" + "="*60)
    print("测试 3: 批量向量化")
    print("="*60)
    
    try:
        # 使用现有的商品 ID（假设 1-5 存在）
        payload = {
            "product_ids": [1, 2, 3, 4, 5]
        }
        
        response = requests.post(
            f"{BASE_URL}/products/vectorize",
            json=payload,
            timeout=60
        )
        result = response.json()
        
        success = result.get("success_count", 0) > 0
        print_result("批量向量化", result, success)
        
        # 等待数据写入
        time.sleep(2)
        
        return success
    except Exception as e:
        print_result("批量向量化", {"error": str(e)}, False)
        return False

def test_vector_search():
    """测试纯向量检索"""
    print("\n" + "="*60)
    print("测试 4: 纯向量检索")
    print("="*60)
    
    try:
        payload = {
            "query": "好吃的零食",
            "search_mode": "vector",
            "top_k": 5,
            "use_cache": True
        }
        
        response = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        success = result.get("total", 0) > 0
        print_result("向量检索", result, success)
        
        if success and result["results"]:
            print("\n   🔍 搜索结果:")
            for i, product in enumerate(result["results"][:3], 1):
                print(f"      {i}. {product['product_name']} - 相似度: {product['similarity_score']:.3f}")
        
        return success
    except Exception as e:
        print_result("向量检索", {"error": str(e)}, False)
        return False

def test_keyword_search():
    """测试关键词检索"""
    print("\n" + "="*60)
    print("测试 5: 关键词检索")
    print("="*60)
    
    try:
        payload = {
            "query": "手机",
            "search_mode": "keyword",
            "top_k": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        success = response.status_code == 200
        print_result("关键词检索", result, success)
        
        if success and result.get("results"):
            print("\n   🔍 搜索结果:")
            for i, product in enumerate(result["results"][:3], 1):
                print(f"      {i}. {product['product_name']}")
        
        return success
    except Exception as e:
        print_result("关键词检索", {"error": str(e)}, False)
        return False

def test_hybrid_search():
    """测试混合检索"""
    print("\n" + "="*60)
    print("测试 6: 混合检索（推荐模式）")
    print("="*60)
    
    try:
        payload = {
            "query": "适合夏天的衣服",
            "search_mode": "hybrid",
            "top_k": 5,
            "filters": {
                "category_1": "服饰"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        success = response.status_code == 200
        print_result("混合检索", result, success)
        
        if success and result.get("results"):
            print("\n   🔍 搜索结果:")
            for i, product in enumerate(result["results"][:3], 1):
                print(f"      {i}. {product['product_name']} - {product['category_2']} - ¥{product['price']}")
                print(f"         相似度: {product['similarity_score']:.3f} | 匹配方式: {product['match_reason']}")
        
        return success
    except Exception as e:
        print_result("混合检索", {"error": str(e)}, False)
        return False

def test_recommend():
    """测试商品推荐"""
    print("\n" + "="*60)
    print("测试 7: 商品推荐")
    print("="*60)
    
    try:
        # 先搜索一个商品
        search_response = requests.post(
            f"{BASE_URL}/products/search",
            json={"query": "零食", "top_k": 1},
            timeout=30
        )
        search_result = search_response.json()
        
        if not search_result.get("results"):
            print("   ⚠️  没有可用的商品进行推荐测试")
            return False
        
        product_id = search_result["results"][0]["product_id"]
        product_name = search_result["results"][0]["product_name"]
        
        print(f"   基于商品: {product_name} (ID: {product_id})")
        
        # 推荐相似商品
        payload = {
            "product_id": product_id,
            "top_k": 3,
            "exclude_same_category": False
        }
        
        response = requests.post(
            f"{BASE_URL}/products/recommend",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        success = result.get("total", 0) > 0
        print_result("商品推荐", result, success)
        
        if success and result["results"]:
            print("\n   💡 推荐商品:")
            for i, product in enumerate(result["results"], 1):
                print(f"      {i}. {product['product_name']} - 相似度: {product['similarity_score']:.3f}")
        
        return success
    except Exception as e:
        print_result("商品推荐", {"error": str(e)}, False)
        return False

def test_price_filter():
    """测试价格过滤"""
    print("\n" + "="*60)
    print("测试 8: 价格范围过滤")
    print("="*60)
    
    try:
        payload = {
            "query": "商品",
            "search_mode": "vector",
            "top_k": 10,
            "filters": {
                "min_price": 50,
                "max_price": 200
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result = response.json()
        
        # 验证所有结果的价格都在范围内
        success = response.status_code == 200
        if success and result.get("results"):
            for product in result["results"]:
                if not (50 <= product["price"] <= 200):
                    success = False
                    break
        
        print_result("价格过滤", result, success)
        
        if success and result.get("results"):
            prices = [p["price"] for p in result["results"]]
            print(f"   价格范围验证: {min(prices):.2f} - {max(prices):.2f} (期望: 50-200)")
        
        return success
    except Exception as e:
        print_result("价格过滤", {"error": str(e)}, False)
        return False

def test_cache_hit():
    """测试缓存命中"""
    print("\n" + "="*60)
    print("测试 9: 缓存效果")
    print("="*60)
    
    try:
        payload = {
            "query": "测试缓存查询",
            "search_mode": "vector",
            "top_k": 5,
            "use_cache": True
        }
        
        # 第一次查询（冷启动）
        response1 = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result1 = response1.json()
        latency1 = result1.get("latency_ms", 0)
        cache_hit1 = result1.get("cache_hit", False)
        
        # 第二次查询（应该命中缓存）
        response2 = requests.post(
            f"{BASE_URL}/products/search",
            json=payload,
            timeout=30
        )
        result2 = response2.json()
        latency2 = result2.get("latency_ms", 0)
        cache_hit2 = result2.get("cache_hit", False)
        
        success = cache_hit2 and latency2 < latency1
        
        print(f"\n   第一次查询: {latency1}ms (缓存命中: {cache_hit1})")
        print(f"   第二次查询: {latency2}ms (缓存命中: {cache_hit2})")
        print(f"   性能提升: {((latency1 - latency2) / latency1 * 100):.1f}%" if latency1 > 0 else "   性能提升: N/A")
        
        print_result("缓存测试", {"cache_hit": cache_hit2, "speedup": f"{latency1}ms -> {latency2}ms"}, success)
        
        return success
    except Exception as e:
        print_result("缓存测试", {"error": str(e)}, False)
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 语义搜索 API 测试套件")
    print("="*60)
    
    tests = [
        ("健康检查", test_health_check),
        ("统计信息", test_stats),
        ("批量向量化", test_batch_vectorize),
        ("纯向量检索", test_vector_search),
        ("关键词检索", test_keyword_search),
        ("混合检索", test_hybrid_search),
        ("商品推荐", test_recommend),
        ("价格过滤", test_price_filter),
        ("缓存效果", test_cache_hit)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 异常: {e}")
            results[name] = False
        
        time.sleep(1)  # 避免请求过快
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}  {name}")
    
    print("\n" + "-"*60)
    print(f"   总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n   🎉 所有测试通过！")
    else:
        print(f"\n   ⚠️  {total - passed} 个测试失败")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    main()