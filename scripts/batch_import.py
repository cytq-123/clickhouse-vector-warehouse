#!/usr/bin/env python3
"""
批量导入文档到向量数仓
支持 JSON、CSV、TXT 格式
"""
import requests
import json
import time
import sys
from pathlib import Path
from typing import List, Dict
import argparse

API_BASE_URL = "http://localhost:8000/api/v1"

def import_from_json(file_path: str) -> List[Dict]:
    """从 JSON 文件读取文档列表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]

def import_from_txt(file_path: str) -> List[Dict]:
    """从 TXT 文件读取，每段作为一个文档"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按空行分段
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    docs = []
    for idx, para in enumerate(paragraphs):
        docs.append({
            "doc_id": f"txt_{Path(file_path).stem}_{idx:03d}",
            "content": para,
            "title": f"{Path(file_path).stem} - 段落 {idx+1}",
            "source_type": "txt",
            "tags": ["导入数据"],
            "author": "batch_import"
        })
    return docs

def insert_document(doc: Dict) -> bool:
    """插入单个文档"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/documents",
            json=doc,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ 插入失败 [{doc.get('doc_id')}]: {e}")
        return False

def batch_import(docs: List[Dict], batch_size: int = 10, delay: float = 0.5):
    """批量导入文档"""
    total = len(docs)
    success = 0
    failed = 0
    
    print(f"开始导入 {total} 个文档...\n")
    
    for idx, doc in enumerate(docs, 1):
        print(f"[{idx}/{total}] 导入: {doc.get('title', doc.get('doc_id'))[:50]}...", end=" ")
        
        if insert_document(doc):
            success += 1
            print("✅")
        else:
            failed += 1
        
        # 控制速率
        if idx % batch_size == 0:
            print(f"\n已完成 {idx}/{total}，休息 {delay}s...\n")
            time.sleep(delay)
    
    print(f"\n导入完成:")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  总计: {total}")

def create_sample_data(output_file: str = "sample_docs.json"):
    """创建示例数据文件"""
    sample_docs = [
        {
            "doc_id": "db_001",
            "content": "ClickHouse 是一个用于在线分析处理的列式数据库管理系统。它支持实时查询处理，能够在亚秒级时间内处理数十亿行数据。",
            "title": "ClickHouse 简介",
            "source_type": "wiki",
            "tags": ["数据库", "OLAP"],
            "author": "技术文档"
        },
        {
            "doc_id": "db_002",
            "content": "Apache Flink 是一个流处理框架，支持事件时间处理和状态管理。它提供了 exactly-once 语义保证，适合实时数据管道。",
            "title": "Flink 基础",
            "source_type": "wiki",
            "tags": ["流处理", "Flink"],
            "author": "技术文档"
        },
        {
            "doc_id": "db_003",
            "content": "Redis 是一个开源的内存数据结构存储，可用作数据库、缓存和消息代理。它支持多种数据结构如字符串、哈希、列表、集合等。",
            "title": "Redis 入门",
            "source_type": "wiki",
            "tags": ["缓存", "NoSQL"],
            "author": "技术文档"
        },
        {
            "doc_id": "ai_001",
            "content": "向量数据库专门用于存储和检索高维向量数据。它们通常使用近似最近邻（ANN）算法来实现高效的相似度搜索。",
            "title": "向量数据库原理",
            "source_type": "wiki",
            "tags": ["向量数据库", "AI"],
            "author": "技术文档"
        },
        {
            "doc_id": "ai_002",
            "content": "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的AI架构。它先从知识库检索相关文档，再结合大模型生成回答。",
            "title": "RAG 架构详解",
            "source_type": "wiki",
            "tags": ["RAG", "LLM"],
            "author": "技术文档"
        }
    ]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_docs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 示例数据已创建: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="批量导入文档到向量数仓")
    parser.add_argument("file", nargs='?', help="输入文件路径 (JSON/TXT)")
    parser.add_argument("--sample", action="store_true", help="创建并导入示例数据")
    parser.add_argument("--batch-size", type=int, default=10, help="批次大小 (默认: 10)")
    parser.add_argument("--delay", type=float, default=0.5, help="批次间延迟秒数 (默认: 0.5)")
    
    args = parser.parse_args()
    
    # 创建示例数据
    if args.sample:
        sample_file = create_sample_data()
        print(f"\n使用示例数据: {sample_file}\n")
        file_path = sample_file
    elif args.file:
        file_path = args.file
    else:
        parser.print_help()
        sys.exit(1)
    
    # 检查文件
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    # 读取文档
    ext = Path(file_path).suffix.lower()
    if ext == '.json':
        docs = import_from_json(file_path)
    elif ext == '.txt':
        docs = import_from_txt(file_path)
    else:
        print(f"❌ 不支持的文件格式: {ext}")
        sys.exit(1)
    
    # 批量导入
    batch_import(docs, batch_size=args.batch_size, delay=args.delay)

if __name__ == "__main__":
    main()