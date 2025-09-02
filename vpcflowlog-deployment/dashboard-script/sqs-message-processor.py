#!/usr/bin/env python3
"""
VPC Flow Logs SQS 消息处理示例

这个脚本演示如何处理来自 S3 的 VPC Flow Logs 文件上传通知，
支持 Text (.gz) 和 Parquet (.parquet) 两种格式。

使用方法:
    python3 sqs-message-processor.py --queue-url <SQS_QUEUE_URL> [--format auto]

依赖:
    pip install boto3 pandas pyarrow
"""

import json
import gzip
import boto3
import argparse
import logging
from urllib.parse import unquote_plus
from typing import Dict, List, Optional
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VPCFlowLogsProcessor:
    def __init__(self, queue_url: str, region: str = None):
        """
        初始化 VPC Flow Logs 处理器
        
        Args:
            queue_url: SQS 队列 URL
            region: AWS 区域
        """
        self.queue_url = queue_url
        self.sqs = boto3.client('sqs', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # VPC Flow Logs 字段定义
        self.flow_log_columns = [
            'version', 'account_id', 'interface_id', 'srcaddr', 'dstaddr',
            'srcport', 'dstport', 'protocol', 'packets', 'bytes',
            'windowstart', 'windowend', 'action', 'flowlogstatus',
            'vpc_id', 'subnet_id', 'instance_id', 'tcp_flags', 'type',
            'pkt_srcaddr', 'pkt_dstaddr', 'region', 'az_id',
            'sublocation_type', 'sublocation_id', 'pkt_src_aws_service',
            'pkt_dst_aws_service', 'flow_direction', 'traffic_path'
        ]

    def detect_file_format(self, file_key: str) -> str:
        """
        根据文件扩展名检测文件格式
        
        Args:
            file_key: S3 文件键
            
        Returns:
            文件格式: 'text' 或 'parquet'
        """
        if file_key.endswith('.parquet'):
            return 'parquet'
        elif file_key.endswith('.gz'):
            return 'text'
        else:
            logger.warning(f"未知文件格式: {file_key}")
            return 'unknown'

    def process_text_file(self, bucket: str, key: str) -> pd.DataFrame:
        """
        处理 Text 格式的 VPC Flow Logs 文件
        
        Args:
            bucket: S3 存储桶名称
            key: S3 文件键
            
        Returns:
            处理后的 DataFrame
        """
        logger.info(f"处理 Text 格式文件: s3://{bucket}/{key}")
        
        try:
            # 下载并解压文件
            response = self.s3.get_object(Bucket=bucket, Key=key)
            
            with gzip.GzipFile(fileobj=response['Body']) as gz_file:
                content = gz_file.read().decode('utf-8')
            
            # 解析每一行
            lines = content.strip().split('\n')
            data = []
            
            for line in lines:
                if line.strip():
                    fields = line.split(' ')
                    # 确保字段数量正确
                    if len(fields) >= len(self.flow_log_columns):
                        data.append(fields[:len(self.flow_log_columns)])
                    else:
                        logger.warning(f"字段数量不足的行: {line[:100]}...")
            
            # 创建 DataFrame
            df = pd.DataFrame(data, columns=self.flow_log_columns)
            
            # 数据类型转换
            numeric_columns = ['version', 'srcport', 'dstport', 'protocol', 
                             'packets', 'bytes', 'windowstart', 'windowend', 
                             'tcp_flags', 'traffic_path']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"成功处理 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"处理 Text 文件失败: {e}")
            raise

    def process_parquet_file(self, bucket: str, key: str) -> pd.DataFrame:
        """
        处理 Parquet 格式的 VPC Flow Logs 文件
        
        Args:
            bucket: S3 存储桶名称
            key: S3 文件键
            
        Returns:
            处理后的 DataFrame
        """
        logger.info(f"处理 Parquet 格式文件: s3://{bucket}/{key}")
        
        try:
            # 直接从 S3 读取 Parquet 文件
            s3_path = f"s3://{bucket}/{key}"
            df = pd.read_parquet(s3_path)
            
            logger.info(f"成功处理 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"处理 Parquet 文件失败: {e}")
            raise

    def analyze_flow_logs(self, df: pd.DataFrame) -> Dict:
        """
        分析 VPC Flow Logs 数据
        
        Args:
            df: Flow Logs DataFrame
            
        Returns:
            分析结果字典
        """
        if df.empty:
            return {"error": "没有数据可分析"}
        
        analysis = {
            "总记录数": len(df),
            "时间范围": {
                "开始": df['windowstart'].min() if 'windowstart' in df.columns else None,
                "结束": df['windowend'].max() if 'windowend' in df.columns else None
            },
            "流量统计": {
                "总字节数": df['bytes'].sum() if 'bytes' in df.columns else 0,
                "总数据包数": df['packets'].sum() if 'packets' in df.columns else 0,
                "ACCEPT流量": len(df[df['action'] == 'ACCEPT']) if 'action' in df.columns else 0,
                "REJECT流量": len(df[df['action'] == 'REJECT']) if 'action' in df.columns else 0
            },
            "协议分布": df['protocol'].value_counts().to_dict() if 'protocol' in df.columns else {},
            "热门源IP": df['srcaddr'].value_counts().head(5).to_dict() if 'srcaddr' in df.columns else {},
            "热门目标IP": df['dstaddr'].value_counts().head(5).to_dict() if 'dstaddr' in df.columns else {}
        }
        
        return analysis

    def process_s3_notification(self, message_body: str) -> Optional[Dict]:
        """
        处理 S3 事件通知消息
        
        Args:
            message_body: SQS 消息体
            
        Returns:
            处理结果或 None
        """
        try:
            # 解析 S3 事件通知
            notification = json.loads(message_body)
            
            # 处理可能的 SNS 包装
            if 'Message' in notification:
                s3_event = json.loads(notification['Message'])
            else:
                s3_event = notification
            
            results = []
            
            # 处理每个 S3 记录
            for record in s3_event.get('Records', []):
                if record.get('eventSource') == 'aws:s3':
                    bucket = record['s3']['bucket']['name']
                    key = unquote_plus(record['s3']['object']['key'])
                    
                    logger.info(f"处理文件: s3://{bucket}/{key}")
                    
                    # 检测文件格式
                    file_format = self.detect_file_format(key)
                    
                    if file_format == 'text':
                        df = self.process_text_file(bucket, key)
                    elif file_format == 'parquet':
                        df = self.process_parquet_file(bucket, key)
                    else:
                        logger.warning(f"跳过未知格式文件: {key}")
                        continue
                    
                    # 分析数据
                    analysis = self.analyze_flow_logs(df)
                    
                    result = {
                        "文件": f"s3://{bucket}/{key}",
                        "格式": file_format,
                        "分析结果": analysis
                    }
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"处理 S3 通知失败: {e}")
            return None

    def poll_and_process(self, max_messages: int = 10, wait_time: int = 20):
        """
        轮询 SQS 队列并处理消息
        
        Args:
            max_messages: 每次轮询的最大消息数
            wait_time: 长轮询等待时间（秒）
        """
        logger.info(f"开始轮询队列: {self.queue_url}")
        
        while True:
            try:
                # 接收消息
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=wait_time,
                    MessageAttributeNames=['All']
                )
                
                messages = response.get('Messages', [])
                
                if not messages:
                    logger.info("没有新消息，继续轮询...")
                    continue
                
                logger.info(f"收到 {len(messages)} 条消息")
                
                # 处理每条消息
                for message in messages:
                    receipt_handle = message['ReceiptHandle']
                    message_body = message['Body']
                    
                    try:
                        # 处理 S3 通知
                        results = self.process_s3_notification(message_body)
                        
                        if results:
                            for result in results:
                                logger.info(f"处理完成: {result['文件']}")
                                logger.info(f"格式: {result['格式']}")
                                logger.info(f"记录数: {result['分析结果'].get('总记录数', 0)}")
                        
                        # 删除已处理的消息
                        self.sqs.delete_message(
                            QueueUrl=self.queue_url,
                            ReceiptHandle=receipt_handle
                        )
                        
                        logger.info("消息处理完成并已删除")
                        
                    except Exception as e:
                        logger.error(f"处理消息失败: {e}")
                        # 消息会返回队列等待重试
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止处理")
                break
            except Exception as e:
                logger.error(f"轮询失败: {e}")
                # 短暂等待后继续
                import time
                time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description='VPC Flow Logs SQS 消息处理器')
    parser.add_argument('--queue-url', required=True, help='SQS 队列 URL')
    parser.add_argument('--region', help='AWS 区域')
    parser.add_argument('--max-messages', type=int, default=10, help='每次轮询的最大消息数')
    parser.add_argument('--wait-time', type=int, default=20, help='长轮询等待时间（秒）')
    
    args = parser.parse_args()
    
    # 创建处理器
    processor = VPCFlowLogsProcessor(args.queue_url, args.region)
    
    # 开始处理
    try:
        processor.poll_and_process(args.max_messages, args.wait_time)
    except Exception as e:
        logger.error(f"处理器启动失败: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())