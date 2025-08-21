#!/usr/bin/env python3
"""
VPC Flow Logs 文件解析和验证工具

功能:
1. 下载和解析 S3 中的 Flow Log 文件
2. 验证文件格式
3. 生成统计报告
4. 转换为不同格式 (JSON, CSV, Parquet)

使用方法:
    python3 flow-log-parser.py --bucket my-bucket --key vpc-flow-logs/year=2024/month=01/day=15/hour=10/file.gz
    python3 flow-log-parser.py --local-file /path/to/file.gz --format json
    python3 flow-log-parser.py --bucket my-bucket --prefix vpc-flow-logs/year=2024/month=01/day=15/ --stats

依赖:
    pip install boto3 pandas pyarrow
"""

import gzip
import json
import argparse
import boto3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Iterator
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FlowLogParser:
    """VPC Flow Logs 解析器"""
    
    # 字段定义 (按我们的 CDK 配置顺序)
    FIELD_NAMES = [
        'version', 'account_id', 'interface_id', 'srcaddr', 'dstaddr',
        'srcport', 'dstport', 'protocol', 'packets', 'bytes',
        'windowstart', 'windowend', 'action', 'flowlogstatus',
        'vpc_id', 'subnet_id', 'instance_id', 'tcp_flags',
        'type', 'pkt_srcaddr', 'pkt_dstaddr'
    ]
    
    # 数值字段
    NUMERIC_FIELDS = {
        'version', 'srcport', 'dstport', 'protocol', 
        'packets', 'bytes', 'windowstart', 'windowend', 'tcp_flags'
    }
    
    # 协议映射
    PROTOCOL_MAP = {
        1: 'ICMP', 6: 'TCP', 17: 'UDP', 58: 'ICMPv6'
    }
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        
    def download_from_s3(self, bucket: str, key: str, local_path: Optional[str] = None) -> str:
        """从 S3 下载文件"""
        if local_path is None:
            local_path = f"/tmp/{Path(key).name}"
            
        logger.info(f"下载 s3://{bucket}/{key} 到 {local_path}")
        self.s3_client.download_file(bucket, key, local_path)
        return local_path
        
    def parse_file(self, file_path: str) -> Iterator[Dict]:
        """解析 Flow Log 文件"""
        logger.info(f"解析文件: {file_path}")
        
        # 判断是否为压缩文件
        if file_path.endswith('.gz'):
            open_func = gzip.open
            mode = 'rt'
        else:
            open_func = open
            mode = 'r'
            
        line_count = 0
        error_count = 0
        
        with open_func(file_path, mode, encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    record = self.parse_line(line)
                    if record:
                        yield record
                        line_count += 1
                except Exception as e:
                    error_count += 1
                    logger.warning(f"解析第 {line_num} 行失败: {e}")
                    
        logger.info(f"解析完成: {line_count} 条记录, {error_count} 个错误")
        
    def parse_line(self, line: str) -> Optional[Dict]:
        """解析单行记录"""
        fields = line.split(' ')
        
        if len(fields) != len(self.FIELD_NAMES):
            raise ValueError(f"字段数量不匹配: 期望 {len(self.FIELD_NAMES)}, 实际 {len(fields)}")
            
        record = {}
        for i, (field_name, value) in enumerate(zip(self.FIELD_NAMES, fields)):
            # 处理缺失值
            if value == '-':
                record[field_name] = None
            elif field_name in self.NUMERIC_FIELDS:
                try:
                    record[field_name] = int(value)
                except ValueError:
                    record[field_name] = None
            else:
                record[field_name] = value
                
        # 添加计算字段
        record['protocol_name'] = self.PROTOCOL_MAP.get(record.get('protocol'), 'Unknown')
        record['start_time'] = datetime.fromtimestamp(record['windowstart']) if record['windowstart'] else None
        record['end_time'] = datetime.fromtimestamp(record['windowend']) if record['windowend'] else None
        record['duration'] = record['windowend'] - record['windowstart'] if record['windowend'] and record['windowstart'] else None
        
        return record
        
    def generate_stats(self, records: List[Dict]) -> Dict:
        """生成统计报告"""
        if not records:
            return {}
            
        df = pd.DataFrame(records)
        
        stats = {
            'total_records': len(records),
            'time_range': {
                'start': df['start_time'].min().isoformat() if 'start_time' in df else None,
                'end': df['end_time'].max().isoformat() if 'end_time' in df else None,
            },
            'traffic_summary': {
                'total_bytes': int(df['bytes'].sum()) if 'bytes' in df else 0,
                'total_packets': int(df['packets'].sum()) if 'packets' in df else 0,
                'unique_sources': df['srcaddr'].nunique() if 'srcaddr' in df else 0,
                'unique_destinations': df['dstaddr'].nunique() if 'dstaddr' in df else 0,
            },
            'action_breakdown': df['action'].value_counts().to_dict() if 'action' in df else {},
            'protocol_breakdown': df['protocol_name'].value_counts().to_dict() if 'protocol_name' in df else {},
            'top_sources': df['srcaddr'].value_counts().head(10).to_dict() if 'srcaddr' in df else {},
            'top_destinations': df['dstaddr'].value_counts().head(10).to_dict() if 'dstaddr' in df else {},
            'top_ports': {
                'source': df['srcport'].value_counts().head(10).to_dict() if 'srcport' in df else {},
                'destination': df['dstport'].value_counts().head(10).to_dict() if 'dstport' in df else {},
            }
        }
        
        return stats
        
    def save_as_json(self, records: List[Dict], output_path: str):
        """保存为 JSON 格式"""
        logger.info(f"保存为 JSON: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, default=str)
            
    def save_as_csv(self, records: List[Dict], output_path: str):
        """保存为 CSV 格式"""
        logger.info(f"保存为 CSV: {output_path}")
        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False)
        
    def save_as_parquet(self, records: List[Dict], output_path: str):
        """保存为 Parquet 格式"""
        logger.info(f"保存为 Parquet: {output_path}")
        df = pd.DataFrame(records)
        df.to_parquet(output_path, index=False)
        
    def list_s3_files(self, bucket: str, prefix: str) -> List[str]:
        """列出 S3 中的文件"""
        logger.info(f"列出 s3://{bucket}/{prefix} 中的文件")
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        files = []
        
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.gz'):
                    files.append(obj['Key'])
                    
        logger.info(f"找到 {len(files)} 个文件")
        return files

def main():
    parser = argparse.ArgumentParser(description='VPC Flow Logs 解析工具')
    
    # 输入选项
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--local-file', help='本地文件路径')
    input_group.add_argument('--s3-file', nargs=2, metavar=('BUCKET', 'KEY'), help='S3 文件 (bucket key)')
    input_group.add_argument('--s3-prefix', nargs=2, metavar=('BUCKET', 'PREFIX'), help='S3 前缀 (处理多个文件)')
    
    # 输出选项
    parser.add_argument('--format', choices=['json', 'csv', 'parquet'], default='json', help='输出格式')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--stats', action='store_true', help='生成统计报告')
    parser.add_argument('--stats-only', action='store_true', help='只生成统计报告')
    parser.add_argument('--limit', type=int, help='限制处理的记录数量')
    
    args = parser.parse_args()
    
    parser_tool = FlowLogParser()
    all_records = []
    
    try:
        # 处理输入
        if args.local_file:
            files_to_process = [args.local_file]
            is_local = True
        elif args.s3_file:
            bucket, key = args.s3_file
            local_file = parser_tool.download_from_s3(bucket, key)
            files_to_process = [local_file]
            is_local = True
        elif args.s3_prefix:
            bucket, prefix = args.s3_prefix
            s3_files = parser_tool.list_s3_files(bucket, prefix)
            files_to_process = []
            is_local = True
            
            for s3_key in s3_files[:10]:  # 限制处理前10个文件
                local_file = parser_tool.download_from_s3(bucket, s3_key)
                files_to_process.append(local_file)
        
        # 解析文件
        for file_path in files_to_process:
            logger.info(f"处理文件: {file_path}")
            
            for record in parser_tool.parse_file(file_path):
                all_records.append(record)
                
                if args.limit and len(all_records) >= args.limit:
                    logger.info(f"达到记录限制: {args.limit}")
                    break
                    
            if args.limit and len(all_records) >= args.limit:
                break
        
        logger.info(f"总共解析了 {len(all_records)} 条记录")
        
        # 生成统计报告
        if args.stats or args.stats_only:
            stats = parser_tool.generate_stats(all_records)
            stats_output = args.output.replace('.json', '_stats.json') if args.output else 'flow_log_stats.json'
            
            with open(stats_output, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, default=str)
            
            logger.info(f"统计报告已保存到: {stats_output}")
            
            # 打印简要统计
            print(f"\n=== Flow Log 统计报告 ===")
            print(f"总记录数: {stats['total_records']:,}")
            print(f"总字节数: {stats['traffic_summary']['total_bytes']:,}")
            print(f"总数据包: {stats['traffic_summary']['total_packets']:,}")
            print(f"唯一源地址: {stats['traffic_summary']['unique_sources']:,}")
            print(f"唯一目标地址: {stats['traffic_summary']['unique_destinations']:,}")
            
            if stats['action_breakdown']:
                print(f"\n动作分布:")
                for action, count in stats['action_breakdown'].items():
                    print(f"  {action}: {count:,}")
                    
            if stats['protocol_breakdown']:
                print(f"\n协议分布:")
                for protocol, count in stats['protocol_breakdown'].items():
                    print(f"  {protocol}: {count:,}")
        
        # 保存解析结果
        if not args.stats_only and all_records:
            output_path = args.output or f'flow_logs.{args.format}'
            
            if args.format == 'json':
                parser_tool.save_as_json(all_records, output_path)
            elif args.format == 'csv':
                parser_tool.save_as_csv(all_records, output_path)
            elif args.format == 'parquet':
                parser_tool.save_as_parquet(all_records, output_path)
                
            logger.info(f"解析结果已保存到: {output_path}")
            
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise

if __name__ == '__main__':
    main()