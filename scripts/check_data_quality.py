#!/usr/bin/env python3
"""
数据质量监控脚本
检查数据仓库各层的数据质量指标
"""

import clickhouse_connect
from datetime import datetime, timedelta

CLICKHOUSE_CONFIG = {
    'host': 'localhost',
    'port': 8123,
    'username': 'admin',
    'password': 'admin123'
}

class DataQualityMonitor:
    def __init__(self):
        self.ch_client = clickhouse_connect.get_client(**CLICKHOUSE_CONFIG)
        self.alerts = []
    
    def check_null_ratio(self, table, column, threshold=0.01):
        """检查字段空值率"""
        query = f"""
        SELECT
            countIf({column} IS NULL) * 1.0 / count() AS null_ratio
        FROM {table}
        """
        result = self.ch_client.query(query)
        null_ratio = result.result_rows[0][0] if result.result_rows else 0
        
        is_abnormal = null_ratio > threshold
        if is_abnormal:
            self.alerts.append(f"⚠️  {table}.{column} 空值率过高: {null_ratio:.2%} (阈值: {threshold:.2%})")
        
        self._log_metric(table, f'null_ratio_{column}', null_ratio, threshold, is_abnormal)
        return null_ratio
    
    def check_duplicate_ratio(self, table, key_columns, threshold=0.001):
        """检查重复率"""
        key_cols_str = ', '.join(key_columns)
        query = f"""
        SELECT
            (count() - uniq({key_cols_str})) * 1.0 / count() AS dup_ratio
        FROM {table}
        """
        result = self.ch_client.query(query)
        dup_ratio = result.result_rows[0][0] if result.result_rows else 0
        
        is_abnormal = dup_ratio > threshold
        if is_abnormal:
            self.alerts.append(f"⚠️  {table} 重复率过高: {dup_ratio:.2%} (阈值: {threshold:.2%})")
        
        self._log_metric(table, 'duplicate_ratio', dup_ratio, threshold, is_abnormal)
        return dup_ratio
    
    def check_data_freshness(self, table, time_column, threshold_hours=24):
        """检查数据新鲜度"""
        query = f"""
        SELECT
            dateDiff('hour', max({time_column}), now()) AS hours_since_last
        FROM {table}
        """
        result = self.ch_client.query(query)
        hours = result.result_rows[0][0] if result.result_rows else 999
        
        is_abnormal = hours > threshold_hours
        if is_abnormal:
            self.alerts.append(f"⚠️  {table} 数据不新鲜: 最后更新于 {hours} 小时前 (阈值: {threshold_hours} 小时)")
        
        self._log_metric(table, 'hours_since_last_update', hours, threshold_hours, is_abnormal)
        return hours
    
    def check_data_volume(self, table, expected_min_rows=100):
        """检查数据量"""
        query = f"SELECT count() FROM {table}"
        count = self.ch_client.command(query)
        
        is_abnormal = count < expected_min_rows
        if is_abnormal:
            self.alerts.append(f"⚠️  {table} 数据量不足: {count} 条 (预期: >= {expected_min_rows})")
        
        self._log_metric(table, 'row_count', count, expected_min_rows, is_abnormal)
        return count
    
    def check_data_consistency(self, source_table, target_table, join_key, threshold=0.05):
        """检查数据一致性（源表和目标表的差异率）"""
        query = f"""
        SELECT
            count() AS source_count,
            (SELECT count() FROM {target_table}) AS target_count,
            abs(source_count - target_count) * 1.0 / source_count AS diff_ratio
        FROM {source_table}
        """
        result = self.ch_client.query(query)
        if result.result_rows:
            source_count, target_count, diff_ratio = result.result_rows[0]
            
            is_abnormal = diff_ratio > threshold
            if is_abnormal:
                self.alerts.append(
                    f"⚠️  数据一致性异常: {source_table}({source_count}) vs {target_table}({target_count}), "
                    f"差异率: {diff_ratio:.2%} (阈值: {threshold:.2%})"
                )
            
            self._log_metric(f"{source_table}_vs_{target_table}", 'consistency_diff_ratio', diff_ratio, threshold, is_abnormal)
            return diff_ratio
        return 0
    
    def _log_metric(self, table_name, metric_name, metric_value, threshold, is_abnormal):
        """记录监控指标到 ClickHouse"""
        query = """
        INSERT INTO dwd_layer.data_quality_monitor VALUES
        (%(table)s, %(date)s, %(metric)s, %(value)s, %(threshold)s, %(abnormal)s, now())
        """
        self.ch_client.query(
            query,
            parameters={
                'table': table_name,
                'date': datetime.now().date(),
                'metric': metric_name,
                'value': float(metric_value),
                'threshold': float(threshold),
                'abnormal': 1 if is_abnormal else 0
            }
        )
    
    def run_all_checks(self):
        """运行所有质量检查"""
        print("=" * 60)
        print("数据质量监控")
        print("=" * 60)
        print()
        
        print("📊 DWD 层检查:")
        print("-" * 60)
        
        # 订单明细表
        self.check_data_volume('dwd_layer.fact_order_detail', 100)
        self.check_null_ratio('dwd_layer.fact_order_detail', 'user_id', 0.01)
        self.check_duplicate_ratio('dwd_layer.fact_order_detail', ['order_id', 'order_detail_id'], 0.001)
        self.check_data_freshness('dwd_layer.fact_order_detail', 'etl_time', 24)
        
        # 用户维度表
        self.check_data_volume('dwd_layer.dim_user', 50)
        self.check_null_ratio('dwd_layer.dim_user', 'username', 0.0)
        
        # 商品维度表
        self.check_data_volume('dwd_layer.dim_product', 50)
        self.check_null_ratio('dwd_layer.dim_product', 'product_name', 0.0)
        
        print("✓ DWD 层检查完成\n")
        
        print("📊 DWS 层检查:")
        print("-" * 60)
        
        # 用户交易汇总
        self.check_data_volume('dws_layer.trade_user_1d', 10)
        self.check_data_freshness('dws_layer.trade_user_1d', 'update_time', 48)
        
        # 商品销售汇总
        self.check_data_volume('dws_layer.product_sale_1d', 10)
        
        print("✓ DWS 层检查完成\n")
        
        print("📊 ADS 层检查:")
        print("-" * 60)
        
        # GMV 大屏
        self.check_data_volume('ads_layer.gmv_dashboard', 1)
        self.check_data_freshness('ads_layer.gmv_dashboard', 'update_time', 48)
        
        # 用户画像
        self.check_data_volume('ads_layer.user_portrait', 10)
        
        print("✓ ADS 层检查完成\n")
        
        # 汇总报告
        print("=" * 60)
        if self.alerts:
            print(f"⚠️  发现 {len(self.alerts)} 个数据质量问题:")
            print("=" * 60)
            for alert in self.alerts:
                print(alert)
        else:
            print("✓ 所有数据质量检查通过")
        print("=" * 60)
        print()
        
        # 查询历史异常
        print("📈 最近7天质量异常统计:")
        query = """
        SELECT
            table_name,
            metric_name,
            count() AS abnormal_count,
            round(avg(metric_value), 4) AS avg_value
        FROM dwd_layer.data_quality_monitor
        WHERE check_date >= today() - INTERVAL 7 DAY
          AND is_abnormal = 1
        GROUP BY table_name, metric_name
        ORDER BY abnormal_count DESC
        """
        result = self.ch_client.query(query)
        
        if result.result_rows:
            print("-" * 60)
            for row in result.result_rows:
                print(f"  {row[0]:40s} | {row[1]:20s} | 异常{row[2]}次 | 均值{row[3]}")
            print("-" * 60)
        else:
            print("  无历史异常记录")
        print()

def main():
    try:
        monitor = DataQualityMonitor()
        monitor.run_all_checks()
        
        print("提示: 可以配置定时任务每天运行此脚本")
        print("  crontab: 0 3 * * * python3 /path/to/check_data_quality.py")
        
    except Exception as e:
        print(f"\n✗ 监控失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()