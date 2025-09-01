# OpenSearch Integration (OSI) VPC Flow Logs 部署指南

## 📋 概述

本指南介绍如何使用 OpenSearch Integration (OSI) 将 AWS VPC Flow Logs 从 S3 解析并导入到 OpenSearch 集群中，遵循 OpenSearch Catalog 的标准化模式。

## 🏗️ 架构图

```
VPC Flow Logs → S3 Bucket → SQS Notification → OSI Pipeline → OpenSearch
```

## 📁 文件说明

- `osi-vpcflowlog.yml` - OSI 管道配置文件
- `vpc-logs-mapping.json` - OpenSearch 索引模板
- `test-osi-config.py` - 配置测试脚本

## 🔧 配置特性

### ✅ 已实现的功能

1. **标准化字段映射**
   - 遵循 OpenSearch Catalog AWS VPC 模式
   - 正确的数据类型映射（ip, integer, keyword）
   - 使用 `aws.vpc.*` 命名空间

2. **数据处理**
   - 自动跳过标题行
   - 空值处理（`-` 转换为 `null`）
   - 数据类型转换
   - 时间戳标准化

3. **增强字段**
   - 流持续时间计算
   - 每包字节数
   - 每秒字节数
   - 事件元数据

4. **性能优化**
   - 压缩支持
   - 批量处理
   - 索引模板

## 📊 字段映射

### 核心字段
| VPC Flow Log 字段 | OpenSearch 字段 | 类型 | 说明 |
|------------------|-----------------|------|------|
| version | aws.vpc.version | keyword | Flow Log 版本 |
| account-id | aws.vpc.account-id | keyword | AWS 账户 ID |
| interface-id | aws.vpc.interface-id | keyword | 网络接口 ID |
| srcaddr | aws.vpc.srcaddr | ip | 源 IP 地址 |
| dstaddr | aws.vpc.dstaddr | ip | 目标 IP 地址 |
| srcport | aws.vpc.srcport | integer | 源端口 |
| dstport | aws.vpc.dstport | integer | 目标端口 |
| protocol | aws.vpc.protocol | keyword | 协议号 |
| packets | aws.vpc.packets | long | 数据包数 |
| bytes | aws.vpc.bytes | long | 字节数 |
| start | aws.vpc.start | long | 开始时间戳 |
| end | aws.vpc.end | long | 结束时间戳 |
| action | aws.vpc.action | keyword | 动作 (ACCEPT/REJECT) |
| log-status | aws.vpc.log-status | keyword | 日志状态 |

### 增强字段
| 字段 | 类型 | 说明 |
|------|------|------|
| @timestamp | date | 主时间戳 |
| aws.vpc.end_timestamp | date | 结束时间戳 |
| aws.vpc.duration | integer | 流持续时间（秒） |
| aws.vpc.bytes_per_packet | float | 每包平均字节数 |
| aws.vpc.bytes_per_second | float | 每秒平均字节数 |

## 🚀 部署步骤

### 1. 准备工作

确保已部署 VPC Flow Logs 到 S3：
```bash
cd vpcflowlog-deployment
./deploy.sh vpc-12345678 my-bucket prod my-queue true
```

### 2. 创建 OpenSearch 索引模板

```bash
# 上传索引模板到 OpenSearch
curl -X PUT "https://your-opensearch-domain/_index_template/vpc-logs-template" \
  -H "Content-Type: application/json" \
  -d @vpc-logs-mapping.json
```

### 3. 部署 OSI 管道

```bash
# 使用 AWS CLI 创建 OSI 管道
aws osis create-pipeline \
  --pipeline-name "vpc-logs-pipeline" \
  --pipeline-configuration-body file://osi-vpcflowlog.yml \
  --min-units 1 \
  --max-units 4
```

### 4. 验证配置

运行测试脚本：
```bash
python3 test-osi-config.py
```

## 📈 监控和告警

### 关键指标

1. **流量指标**
   - `aws.vpc.bytes` - 监控异常流量
   - `aws.vpc.packets` - 监控数据包数量
   - `aws.vpc.bytes_per_second` - 监控带宽使用

2. **安全指标**
   - `aws.vpc.action:REJECT` - 监控被拒绝的连接
   - `aws.vpc.flow-direction` - 监控流量方向

3. **性能指标**
   - `aws.vpc.duration` - 监控连接持续时间
   - `aws.vpc.bytes_per_packet` - 监控数据包效率

### 示例查询

```json
# 查找被拒绝的连接
{
  "query": {
    "term": {
      "aws.vpc.action": "REJECT"
    }
  }
}

# 查找高流量连接
{
  "query": {
    "range": {
      "aws.vpc.bytes": {
        "gte": 1000000
      }
    }
  }
}

# 按源 IP 聚合流量
{
  "aggs": {
    "top_sources": {
      "terms": {
        "field": "aws.vpc.srcaddr",
        "size": 10
      },
      "aggs": {
        "total_bytes": {
          "sum": {
            "field": "aws.vpc.bytes"
          }
        }
      }
    }
  }
}
```

## 🔍 故障排除

### 常见问题

1. **字段映射错误**
   ```bash
   # 检查索引映射
   curl -X GET "https://your-opensearch-domain/vpc-logs-*/_mapping"
   ```

2. **数据类型错误**
   ```bash
   # 检查解析错误
   curl -X GET "https://your-opensearch-domain/_cat/indices/vpc-logs-*?v"
   ```

3. **时间戳问题**
   ```bash
   # 验证时间戳格式
   curl -X GET "https://your-opensearch-domain/vpc-logs-*/_search" \
     -H "Content-Type: application/json" \
     -d '{"query":{"match_all":{}},"size":1}'
   ```

### 调试步骤

1. **验证 S3 数据格式**
   ```bash
   aws s3 cp s3://your-bucket/vpc-flow-logs/sample.gz - | gunzip | head -5
   ```

2. **检查 SQS 消息**
   ```bash
   aws sqs receive-message --queue-url https://sqs.region.amazonaws.com/account/queue-name
   ```

3. **监控 OSI 管道**
   ```bash
   aws osis get-pipeline --pipeline-name vpc-logs-pipeline
   ```

## 📚 参考资料

- [OpenSearch Catalog - AWS VPC Schema](https://github.com/opensearch-project/opensearch-catalog/blob/main/docs/schema/observability/logs/aws/aws_vpc.md)
- [AWS VPC Flow Logs 用户指南](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [OpenSearch Integration 文档](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ingestion.html)

## 🎯 最佳实践

1. **索引管理**
   - 使用日期模式的索引名称
   - 设置适当的分片和副本数量
   - 配置索引生命周期管理

2. **性能优化**
   - 调整批量大小
   - 优化刷新间隔
   - 使用压缩

3. **安全性**
   - 配置适当的 IAM 角色
   - 启用 VPC 端点
   - 使用加密传输

4. **成本优化**
   - 监控索引大小
   - 配置数据保留策略
   - 使用冷存储