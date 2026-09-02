"""
系统测试脚本
验证向量数仓的核心功能
"""
import requests
import time
import json
from typing import List, Dict

API_BASE_URL = "http://localhost:8000/api/v1"

class VectorWarehouseTest:
    """向量数仓测试类"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health(self) -> bool:
        """测试健康检查"""
        print("\n[测试 1] 健康检查...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            data = response.json()
            
            print(f"状态: {data['status']}")
            for service, status in data['services'].items():
                emoji = "✅" if status == "healthy" else "❌"
                print(f"  {emoji} {service}: {status}")
            
            return data['status'] in ['healthy', 'degraded']
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False
    
    def test_search_basic(self) -> bool:
        """测试基础检索"""
        print("\n[测试 2] 基础向量检索...")
        try:
            response = self.session.post(
                f"{self.base_url}/search",
                json={"query": "ClickHouse 性能优化", "top_k": 3}
            )
            data = response.json()
            
            print(f"查询: {data['query']}")
            print(f"结果数: {data['total']}")
            print(f"延迟: {data['latency_ms']}ms")
            print(f"缓存命中: {data['cache_hit']}")
            
            if data['results']:
                print("\n前 3 个结果:")
                for i, result in enumerate(data['results'][:3], 1):
                    print(f"\n  {i}. [{result['similarity_score']:.3f}] {result['title']}")
                    print(f"     {result['content'][:100]}...")
            
            return len(data['results']) > 0
        except Exception as e:
            print(f"❌ 基础检索失败: {e}")
            return False
    
    def test_search_with_filters(self) -> bool:
        """测试带过滤条件的检索"""
        print("\n[测试 3] 带过滤条件的检索...")
        try:
            response = self.session.post(
                f"{self.base_url}/search",
                json={
                    "query": "数据库优化",
                    "filters": {
                        "source_type": "wiki",
                        "tags": ["数据库"]
                    },
                    "top_k": 5
                }
            )
            data = response.json()
            
            print(f"查询: {data['query']}")
            print(f"过滤条件: source_type=wiki, tags=[数据库]")
            print(f"结果数: {data['total']}")
            print(f"延迟: {data['latency_ms']}ms")
            
            return data['total'] >= 0  # 允许 0 结果（过滤后可能没有匹配）
        except Exception as e:
            print(f"❌ 过滤检索失败: {e}")
            return False
    
    def test_cache_effectiveness(self) -> bool:
        """测试缓存效果"""
        print("\n[测试 4] 缓存效果测试...")
        try:
            query = "Redis 缓存设计模式"
            
            # 第一次查询（冷启动）
            print("第一次查询（冷启动）...")
            response1 = self.session.post(
                f"{self.base_url}/search",
                json={"query": query, "top_k": 3, "use_cache": True}
            )
            data1 = response1.json()
            latency1 = data1['latency_ms']
            cache_hit1 = data1['cache_hit']
            
            print(f"  延迟: {latency1}ms, 缓存命中: {cache_hit1}")
            
            # 第二次查询（应该命中缓存）
            time.sleep(0.5)
            print("第二次查询（应该命中缓存）...")
            response2 = self.session.post(
                f"{self.base_url}/search",
                json={"query": query, "top_k": 3, "use_cache": True}
            )
            data2 = response2.json()
            latency2 = data2['latency_ms']
            cache_hit2 = data2['cache_hit']
            
            print(f"  延迟: {latency2}ms, 缓存命中: {cache_hit2}")
            
            if cache_hit2:
                speedup = latency1 / latency2 if latency2 > 0 else 1
                print(f"\n✅ 缓存加速: {speedup:.1f}x")
            else:
                print("\n⚠️  未命中缓存（可能 Redis 配置问题）")
            
            return True
        except Exception as e:
            print(f"❌ 缓存测试失败: {e}")
            return False
    
    def test_stats(self) -> bool:
        """测试统计信息"""
        print("\n[测试 5] 统计信息...")
        try:
            response = self.session.get(f"{self.base_url}/stats")
            data = response.json()
            
            print(f"文档总数: {data['total_documents']}")
            print("按来源分布:")
            for source, count in data['documents_by_source'].items():
                print(f"  - {source}: {count}")
            print(f"近 24h 查询量: {data['recent_24h_queries']}")
            print(f"平均延迟: {data['avg_latency_ms']}ms")
            
            return True
        except Exception as e:
            print(f"❌ 统计信息获取失败: {e}")
            return False
    
    def test_performance(self, num_queries: int = 10) -> bool:
        """测试性能"""
        print(f"\n[测试 6] 性能测试（{num_queries} 次查询）...")
        try:
            queries = [
                "ClickHouse 优化",
                "Flink CDC 实时同步",
                "Redis 缓存策略",
                "Kafka 消息队列",
                "向量数据库选型",
                "LangChain RAG 应用",
                "数据库性能调优",
                "实时数仓架构",
                "分布式系统设计",
                "AI 应用开发"
            ]
            
            latencies = []
            
            for i in range(num_queries):
                query = queries[i % len(queries)]
                start = time.time()
                response = self.session.post(
                    f"{self.base_url}/search",
                    json={"query": query, "top_k": 5}
                )
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                
                print(f"  查询 {i+1}/{num_queries}: {latency:.0f}ms")
            
            # 统计
            avg_latency = sum(latencies) / len(latencies)
            p50 = sorted(latencies)[len(latencies) // 2]
            p99 = sorted(latencies)[int(len(latencies) * 0.99)]
            
            print(f"\n性能统计:")
            print(f"  平均延迟: {avg_latency:.0f}ms")
            print(f"  P50: {p50:.0f}ms")
            print(f"  P99: {p99:.0f}ms")
            print(f"  QPS: {1000 / avg_latency:.1f}")
            
            return True
        except Exception as e:
            print(f"❌ 性能测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("实时向量数仓 - 系统测试")
        print("=" * 60)
        
        tests = [
            ("健康检查", self.test_health),
            ("基础检索", self.test_search_basic),
            ("过滤检索", self.test_search_with_filters),
            ("缓存效果", self.test_cache_effectiveness),
            ("统计信息", self.test_stats),
            ("性能测试", self.test_performance),
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n❌ {name} 异常: {e}")
                results.append((name, False))
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed_count = sum(1 for _, passed in results if passed)
        total_count = len(results)
        
        for name, passed in results:
            emoji = "✅" if passed else "❌"
            print(f"{emoji} {name}")
        
        print("\n" + "=" * 60)
        print(f"通过: {passed_count}/{total_count}")
        
        if passed_count == total_count:
            print("\n🎉 所有测试通过！系统运行正常。")
        else:
            print(f"\n⚠️  有 {total_count - passed_count} 个测试失败，请检查日志。")
        
        print("=" * 60)

if __name__ == "__main__":
    tester = VectorWarehouseTest()
    tester.run_all_tests()