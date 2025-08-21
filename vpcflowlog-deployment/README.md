# VPC Flow Logs CDK 部署

这个 CDK 项目用于部署 VPC Flow Logs 到 S3 存储桶，支持按时间分区存储。

## 功能特性

- ✅ 可配置的 VPC ID
- ✅ S3 存储桶自动创建或使用指定名称
- ✅ 按时间分区存储（Hive 兼容格式）
- ✅ **SQS 事件通知** - 当文件上传到 S3 时自动发送通知
- ✅ 死信队列 (DLQ) 处理失败的通知
- ✅ 生命周期管理（IA、Glacier、Deep Archive）
- ✅ 服务器端加密
- ✅ CloudWatch 日志组用于监控
- ✅ 完整的 IAM 权限配置
- ✅ 自定义日志格式包含详细字段

## 前置要求

1. **AWS CLI 已配置**: `aws configure` 或使用 IAM 角色
2. **Node.js 和 npm 已安装**: 推荐 Node.js 18+ 
3. **AWS CDK CLI 已安装**: `npm install -g aws-cdk`
4. **有效的 AWS 凭证和权限**:
   - VPC 相关权限 (`ec2:*`)
   - S3 权限 (`s3:*`)
   - SQS 权限 (`sqs:*`)
   - IAM 权限 (`iam:*`)
   - CloudWatch Logs 权限 (`logs:*`)
5. **现有的 VPC**: 确保你要监控的 VPC 已经存在

## 重要注意事项

⚠️ **部署前必读**:
- 确保 VPC ID 存在且在当前 AWS 区域
- S3 存储桶名称必须全局唯一
- Flow Logs 会产生存储和数据传输费用
- 建议先在测试环境部署验证

## 安装依赖

```bash
cd vpcflowlog-deployment
npm install
```

## 部署方式

### 方式 1: 使用部署脚本

```bash
# 基本部署（自动生成 bucket 名称和 SQS 队列）
./deploy.sh vpc-12345678

# 指定 bucket 名称
./deploy.sh vpc-12345678 my-custom-bucket-name

# 指定环境和 SQS 队列名称
./deploy.sh vpc-12345678 my-custom-bucket-name prod my-sqs-queue

# 禁用 SQS 通知
./deploy.sh vpc-12345678 my-custom-bucket-name prod "" false

# 快速部署（开发环境）
./quick-deploy.sh vpc-12345678
```

### 方式 2: 直接使用 CDK 命令

```bash
# 构建项目
npm run build

# 部署（必须指定 VPC ID）
npx cdk deploy -c vpcId=vpc-12345678

# 指定 bucket 名称和环境
npx cdk deploy -c vpcId=vpc-12345678 -c bucketName=my-bucket -c environment=prod

# 指定 SQS 队列名称
npx cdk deploy -c vpcId=vpc-12345678 -c sqsQueueName=my-queue

# 禁用 SQS 通知
npx cdk deploy -c vpcId=vpc-12345678 -c enableSqsNotification=false
```

### 方式 3: 使用环境变量

```bash
export VPC_ID=vpc-12345678
export BUCKET_NAME=my-flow-logs-bucket
export ENVIRONMENT=prod
export SQS_QUEUE_NAME=my-sqs-queue

npx cdk deploy
```

## 配置参数

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| vpcId | ✅ | - | 要启用 Flow Logs 的 VPC ID |
| bucketName | ❌ | 自动生成 | S3 存储桶名称 |
| environment | ❌ | dev | 环境标识 |
| enableSqsNotification | ❌ | true | 是否启用 SQS 事件通知 |
| sqsQueueName | ❌ | 自动生成 | SQS 队列名称 |

## S3 存储结构

Flow Logs 将按以下结构存储在 S3 中：

```
vpc-flow-logs/
├── year=2024/
│   ├── month=01/
│   │   ├── day=15/
│   │   │   ├── hour=10/
│   │   │   │   └── vpc-flow-logs_*.gz
│   │   │   └── hour=11/
│   │   └── day=16/
│   └── month=02/
```

## 文件格式详解

### 文件基本信息
- **压缩格式**: gzip (`.gz` 文件)
- **内容格式**: 空格分隔的文本文件
- **编码**: UTF-8
- **文件命名**: `{account-id}_vpcflowlogs_{region}_{flow-log-id}_{end-time}_{hash}.gz`

### 日志字段 (21个字段)
我们的配置包含以下完整字段：

| 序号 | 字段名 | 类型 | 描述 | 示例 |
|------|--------|------|------|------|
| 1 | version | int | Flow Log 版本 | 5 |
| 2 | account-id | string | AWS 账户 ID | 123456789012 |
| 3 | interface-id | string | 网络接口 ID | eni-1235b8ca123456789 |
| 4 | srcaddr | string | 源 IP 地址 | 172.31.16.139 |
| 5 | dstaddr | string | 目标 IP 地址 | 172.31.16.21 |
| 6 | srcport | int | 源端口 | 20641 |
| 7 | dstport | int | 目标端口 | 22 |
| 8 | protocol | int | IANA 协议号 | 6 (TCP) |
| 9 | packets | int | 数据包数量 | 20 |
| 10 | bytes | int | 字节数 | 4249 |
| 11 | windowstart | int | 捕获窗口开始时间 | 1418530010 |
| 12 | windowend | int | 捕获窗口结束时间 | 1418530070 |
| 13 | action | string | 流量动作 | ACCEPT/REJECT |
| 14 | flowlogstatus | string | Flow Log 状态 | OK/NODATA/SKIPDATA |
| 15 | vpc-id | string | VPC ID | vpc-12345678 |
| 16 | subnet-id | string | 子网 ID | subnet-12345678 |
| 17 | instance-id | string | 实例 ID | i-1234567890abcdef0 |
| 18 | tcp-flags | int | TCP 标志 | 19 |
| 19 | type | string | 流量类型 | IPv4/IPv6 |
| 20 | pkt-srcaddr | string | 数据包源地址 | 172.31.16.139 |
| 21 | pkt-dstaddr | string | 数据包目标地址 | 172.31.16.21 |

### 示例记录
```
5 123456789012 eni-1235b8ca123456789 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.16.139 172.31.16.21
```

**注意**: 我们使用了自定义的日志格式字符串来确保包含所有必要的字段，这样可以避免 CDK 版本兼容性问题。

## 生命周期管理

- 30 天后转换到 IA (Infrequent Access)
- 90 天后转换到 Glacier
- 365 天后转换到 Deep Archive
- 旧版本在 30 天后删除

## 监控

- CloudWatch 日志组：`/aws/vpc/flowlogs/{environment}`
- 只有被拒绝的流量会记录到 CloudWatch（节省成本）
- 所有流量都会记录到 S3

## SQS 事件通知

当新的 Flow Log 文件上传到 S3 时，会自动发送通知到 SQS 队列：

- **触发事件**: `s3:ObjectCreated:Put` 和 `s3:ObjectCreated:CompleteMultipartUpload`
- **过滤条件**: 
  - 前缀: `vpc-flow-logs/`
  - 后缀: `.gz`
- **队列配置**:
  - 可见性超时: 5 分钟
  - 消息保留期: 14 天
  - 死信队列: 3 次重试后进入 DLQ
  - 加密: SQS 托管加密

### SQS 消息格式示例

```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "eventName": "ObjectCreated:Put",
      "eventTime": "2024-01-15T10:30:00.000Z",
      "s3": {
        "bucket": {
          "name": "vpc-flow-logs-prod-123456789012-us-east-1"
        },
        "object": {
          "key": "vpc-flow-logs/year=2024/month=01/day=15/hour=10/vpc-flow-logs_20240115T1030Z_hash.gz",
          "size": 1024
        }
      }
    }
  ]
}
```

## 清理资源

```bash
npx cdk destroy
```

注意：S3 存储桶设置了保留策略，需要手动删除。

## 故障排除

### 常见错误

1. **VPC 不存在**: 确保 VPC ID 正确且在当前区域
2. **权限不足**: 确保 AWS 凭证有足够权限创建资源
3. **Bucket 名称冲突**: S3 bucket 名称必须全局唯一

### 验证部署

```bash
# 检查 Flow Logs 状态
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-12345678"

# 检查 S3 存储桶
aws s3 ls s3://your-bucket-name/vpc-flow-logs/

# 检查 SQS 队列
aws sqs list-queues | grep vpc-flow-logs

# 检查 SQS 队列属性
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All

# 监控 SQS 消息
aws sqs receive-message --queue-url <queue-url> --max-number-of-messages 10

# 下载和查看 Flow Log 文件
aws s3 cp s3://your-bucket-name/vpc-flow-logs/year=2024/month=01/day=15/hour=10/file.gz ./
gunzip file.gz
head -5 file
```

### 文件解析工具

我们提供了专用的解析工具：

```bash
# 解析本地文件
python3 tools/flow-log-parser.py --local-file /path/to/file.gz --stats

# 解析 S3 文件
python3 tools/flow-log-parser.py --s3-file my-bucket vpc-flow-logs/year=2024/month=01/day=15/hour=10/file.gz --format csv

# 批量处理 S3 文件并生成统计
python3 tools/flow-log-parser.py --s3-prefix my-bucket vpc-flow-logs/year=2024/month=01/day=15/ --stats-only

# 转换为不同格式
python3 tools/flow-log-parser.py --local-file file.gz --format parquet --output flow_logs.parquet
```

## 文件处理和分析

### Athena 表创建
```sql
CREATE EXTERNAL TABLE vpc_flow_logs (
  version int,
  account_id string,
  interface_id string,
  srcaddr string,
  dstaddr string,
  srcport int,
  dstport int,
  protocol int,
  packets bigint,
  bytes bigint,
  windowstart bigint,
  windowend bigint,
  action string,
  flowlogstatus string,
  vpc_id string,
  subnet_id string,
  instance_id string,
  tcp_flags int,
  type string,
  pkt_srcaddr string,
  pkt_dstaddr string
)
PARTITIONED BY (
  year string,
  month string,
  day string,
  hour string
)
STORED AS TEXTFILE
LOCATION 's3://your-bucket-name/vpc-flow-logs/'
TBLPROPERTIES (
  'skip.header.line.count'='0',
  'field.delim'=' '
);
```

### 常用查询示例
```sql
-- 查看特定时间段的流量统计
SELECT 
  action,
  COUNT(*) as record_count,
  SUM(bytes) as total_bytes,
  COUNT(DISTINCT srcaddr) as unique_sources
FROM vpc_flow_logs
WHERE year='2024' AND month='01' AND day='15'
GROUP BY action;

-- 查找被拒绝的流量
SELECT srcaddr, dstaddr, dstport, COUNT(*) as attempts
FROM vpc_flow_logs
WHERE action='REJECT' AND year='2024' AND month='01' AND day='15'
GROUP BY srcaddr, dstaddr, dstport
ORDER BY attempts DESC
LIMIT 10;
```

## 成本优化建议

1. 根据需要调整日志格式字段
2. 考虑只记录特定类型的流量（ACCEPT/REJECT）
3. 定期审查生命周期策略
4. 监控 S3 存储成本
5. 使用 Athena 分区查询减少扫描数据量
6. 考虑将历史数据转换为 Parquet 格式以提高查询性能

## 故障排除

如果遇到部署问题，请查看 [故障排除指南](docs/troubleshooting.md)。

常见问题：
- **TypeScript 编译错误**: 检查 CDK 版本和依赖
- **AWS 权限错误**: 确保有足够的 IAM 权限
- **VPC 不存在**: 验证 VPC ID 和区域设置
- **S3 存储桶名称冲突**: 使用唯一的存储桶名称

## 相关文档

- [详细文件格式说明](docs/file-format.md)
- [故障排除指南](docs/troubleshooting.md)
- [Python 解析工具](tools/flow-log-parser.py)
- [Lambda 处理示例](examples/lambda-sqs-processor.py)
- [SQS 消息处理示例](examples/sqs-message-processor.py)