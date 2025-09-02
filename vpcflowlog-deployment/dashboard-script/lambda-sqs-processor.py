"""
AWS Lambda 函数示例：处理 VPC Flow Logs SQS 事件

这个 Lambda 函数处理来自 SQS 的 VPC Flow Logs 文件上传通知，
支持 Text (.gz) 和 Parquet (.parquet) 两种格式。

部署要求:
1. 运行时: Python 3.9+
2. 内存: 512MB+
3. 超时: 5 分钟
4. IAM 权限: S3 读取, SQS 接收/删除, CloudWatch Logs

环境变量:
- LOG_LEVEL: 日志级别 (INFO, DEBUG, ERROR)
- ENABLE_DETAILED_ANALYSIS: 是否启用详细分析 (true/false)

依赖层:
需要创建包含以下包的 Lambda 层:
- pandas
- pyarrow (用于 Parquet 支持)
- boto3 (通常已包含)
"""

import json
import gzip
import os
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import unquote_plus
import boto3

# 配置日志
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# 初始化 AWS 客户端
s3_client = boto3.client('s3')

# VPC Flow Logs 字段定义
FLOW_LOG_COLUMNS = [
    'version', 'account_id', 'interface_id', 'srcaddr', 'dstaddr',
    'srcport', 'dstport', 'protocol', 'packets', 'bytes',
    'windowstart', 'windowend', 'action', 'flowlogstatus',
    'vpc_id', 'subnet_id', 'instance_id', 'tcp_flags', 'type',
    'pkt_srcaddr', 'pkt_dstaddr', 'region', 'az_id',
    'sublocation_type', 'sublocation_id', 'pkt_src_aws_service',
    'pkt_dst_aws_service', 'flow_direction', 'traffic_path'
]

def detect_file_format(file_key: str) -> str:
    """
    根据文件扩展名检测文件格式
    
    Args:
        file_key: S3 文件键
        
    Returns:
        文件格式: 'text', 'parquet', 或 'unknown'
    """
    if file_key.endswith('.parquet'):
        return 'parquet'
    elif file_key.endswith('.gz'):
        return 'text'
    else:
        return 'unknown'

def process_text_file(bucket: str, key: str) -> Dict[str, Any]:
    """
    处理 Text 格式的 VPC Flow Logs 文件
    
    Args:
        bucket: S3 存储桶名称
        key: S3 文件键
        
    Returns:
        处理结果字典
    """
    logger.info(f"处理 Text 格式文件: s3://{bucket}/{key}")
    
    try:
        # 下载并解压文件
        response = s3_client.get_object(Bucket=bucket, Key=key)
        
        with gzip.GzipFile(fileobj=response['Body']) as gz_file:
            content = gz_file.read().decode('utf-8')
        
        # 解析每一行
        lines = content.strip().split('\n')
        records = []
        
        for line_num, line in enumerate(lines, 1):
            if line.strip():
                fields = line.split(' ')
                if len(fields) >= len(FLOW_LOG_COLUMNS):
                    record = dict(zip(FLOW_LOG_COLUMNS, fields[:len(FLOW_LOG_COLUMNS)]))
                    records.append(record)
                else:
                    logger.warning(f"第 {line_num} 行字段数量不足: {len(fields)}")
        
        # 基础统计
        stats = analyze_records(records)
        
        result = {
            "status": "success",
            "format": "text",
            "file": f"s3://{bucket}/{key}",
            "records_count": len(records),
            "file_size": response['ContentLength'],
            "statistics": stats
        }
        
        logger.info(f"成功处理 {len(records)} 条记录")
        return result
        
    except Exception as e:
        logger.error(f"处理 Text 文件失败: {e}")
        return {
            "status": "error",
            "format": "text",
            "file": f"s3://{bucket}/{key}",
            "error": str(e)
        }

def process_parquet_file(bucket: str, key: str) -> Dict[str, Any]:
    """
    处理 Parquet 格式的 VPC Flow Logs 文件
    
    Args:
        bucket: S3 存储桶名称
        key: S3 文件键
        
    Returns:
        处理结果字典
    """
    logger.info(f"处理 Parquet 格式文件: s3://{bucket}/{key}")
    
    try:
        # 获取文件元数据
        head_response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = head_response['ContentLength']
        
        # 对于 Parquet 文件，我们可以读取元数据而不需要下载整个文件
        # 这里简化处理，实际应用中可以使用 pyarrow 读取 Parquet 元数据
        
        try:
            import pandas as pd
            
            # 直接从 S3 读取 Parquet 文件
            s3_path = f"s3://{bucket}/{key}"
            df = pd.read_parquet(s3_path)
            
            # 转换为记录列表进行分析
            records = df.to_dict('records')
            stats = analyze_records(records)
            
            result = {
                "status": "success",
                "format": "parquet",
                "file": f"s3://{bucket}/{key}",
                "records_count": len(records),
                "file_size": file_size,
                "statistics": stats
            }
            
            logger.info(f"成功处理 {len(records)} 条记录")
            return result
            
        except ImportError:
            # 如果没有 pandas/pyarrow，只返回基本信息
            logger.warning("pandas/pyarrow 不可用，只返回基本文件信息")
            return {
                "status": "success",
                "format": "parquet",
                "file": f"s3://{bucket}/{key}",
                "file_size": file_size,
                "message": "Parquet 文件检测到，但无法进行详细分析（缺少 pandas/pyarrow）"
            }
        
    except Exception as e:
        logger.error(f"处理 Parquet 文件失败: {e}")
        return {
            "status": "error",
            "format": "parquet",
            "file": f"s3://{bucket}/{key}",
            "error": str(e)
        }

def analyze_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析 VPC Flow Logs 记录
    
    Args:
        records: Flow Logs 记录列表
        
    Returns:
        分析结果字典
    """
    if not records:
        return {"message": "没有记录可分析"}
    
    # 基础统计
    total_bytes = 0
    total_packets = 0
    accept_count = 0
    reject_count = 0
    protocols = {}
    src_ips = {}
    dst_ips = {}
    
    for record in records:
        # 流量统计
        try:
            bytes_val = int(record.get('bytes', 0))
            packets_val = int(record.get('packets', 0))
            total_bytes += bytes_val
            total_packets += packets_val
        except (ValueError, TypeError):
            pass
        
        # 动作统计
        action = record.get('action', '').upper()
        if action == 'ACCEPT':
            accept_count += 1
        elif action == 'REJECT':
            reject_count += 1
        
        # 协议统计
        protocol = record.get('protocol', 'unknown')
        protocols[protocol] = protocols.get(protocol, 0) + 1
        
        # IP 统计（只统计前10个）
        if len(src_ips) < 10:
            src_ip = record.get('srcaddr', 'unknown')
            src_ips[src_ip] = src_ips.get(src_ip, 0) + 1
        
        if len(dst_ips) < 10:
            dst_ip = record.get('dstaddr', 'unknown')
            dst_ips[dst_ip] = dst_ips.get(dst_ip, 0) + 1
    
    # 获取时间范围
    time_range = {}
    try:
        start_times = [int(r.get('windowstart', 0)) for r in records if r.get('windowstart')]
        end_times = [int(r.get('windowend', 0)) for r in records if r.get('windowend')]
        
        if start_times and end_times:
            time_range = {
                "start": min(start_times),
                "end": max(end_times),
                "duration_seconds": max(end_times) - min(start_times)
            }
    except (ValueError, TypeError):
        pass
    
    return {
        "total_records": len(records),
        "traffic": {
            "total_bytes": total_bytes,
            "total_packets": total_packets,
            "accept_flows": accept_count,
            "reject_flows": reject_count
        },
        "time_range": time_range,
        "top_protocols": dict(sorted(protocols.items(), key=lambda x: x[1], reverse=True)[:5]),
        "top_src_ips": dict(sorted(src_ips.items(), key=lambda x: x[1], reverse=True)[:5]),
        "top_dst_ips": dict(sorted(dst_ips.items(), key=lambda x: x[1], reverse=True)[:5])
    }

def process_s3_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理单个 S3 事件记录
    
    Args:
        record: S3 事件记录
        
    Returns:
        处理结果
    """
    try:
        # 提取 S3 信息
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        logger.info(f"处理文件: s3://{bucket}/{key}")
        
        # 检测文件格式
        file_format = detect_file_format(key)
        
        if file_format == 'text':
            return process_text_file(bucket, key)
        elif file_format == 'parquet':
            return process_parquet_file(bucket, key)
        else:
            logger.warning(f"跳过未知格式文件: {key}")
            return {
                "status": "skipped",
                "format": "unknown",
                "file": f"s3://{bucket}/{key}",
                "message": "未知文件格式"
            }
    
    except Exception as e:
        logger.error(f"处理 S3 记录失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "record": record
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 函数入口点
    
    Args:
        event: Lambda 事件
        context: Lambda 上下文
        
    Returns:
        处理结果
    """
    logger.info(f"收到事件: {json.dumps(event, default=str)}")
    
    results = []
    
    try:
        # 处理 SQS 记录
        for sqs_record in event.get('Records', []):
            if sqs_record.get('eventSource') == 'aws:sqs':
                # 解析 SQS 消息体
                message_body = sqs_record['body']
                
                try:
                    # 解析 S3 事件通知
                    s3_notification = json.loads(message_body)
                    
                    # 处理可能的 SNS 包装
                    if 'Message' in s3_notification:
                        s3_event = json.loads(s3_notification['Message'])
                    else:
                        s3_event = s3_notification
                    
                    # 处理每个 S3 记录
                    for s3_record in s3_event.get('Records', []):
                        if s3_record.get('eventSource') == 'aws:s3':
                            result = process_s3_record(s3_record)
                            results.append(result)
                
                except json.JSONDecodeError as e:
                    logger.error(f"解析 SQS 消息失败: {e}")
                    results.append({
                        "status": "error",
                        "error": f"JSON 解析失败: {str(e)}",
                        "message_body": message_body[:200] + "..." if len(message_body) > 200 else message_body
                    })
        
        # 汇总结果
        successful = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'error')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        
        summary = {
            "total_files": len(results),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "results": results
        }
        
        logger.info(f"处理完成: {successful} 成功, {failed} 失败, {skipped} 跳过")
        
        return {
            "statusCode": 200,
            "body": json.dumps(summary, default=str)
        }
    
    except Exception as e:
        logger.error(f"Lambda 函数执行失败: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Lambda 函数执行失败"
            })
        }

# 本地测试函数
def test_locally():
    """
    本地测试函数
    """
    # 模拟 SQS 事件
    test_event = {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": json.dumps({
                    "Records": [
                        {
                            "eventSource": "aws:s3",
                            "s3": {
                                "bucket": {"name": "test-bucket"},
                                "object": {"key": "vpc-flow-logs/year=2024/month=01/day=15/test.parquet"}
                            }
                        }
                    ]
                })
            }
        ]
    }
    
    # 模拟上下文
    class MockContext:
        def __init__(self):
            self.function_name = "test-function"
            self.memory_limit_in_mb = 512
            self.remaining_time_in_millis = lambda: 300000
    
    context = MockContext()
    
    # 执行测试
    result = lambda_handler(test_event, context)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    test_locally()