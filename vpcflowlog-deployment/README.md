# VPC Flow Logs CDK 部署

这个 CDK 项目用于部署 VPC Flow Logs 到 S3 存储桶，支持按时间分区存储。

## 功能特性

- ✅ 可配置的 VPC ID
- ✅ S3 存储桶自动创建或使用指定名称
- ✅ 按时间分区存储（Hive 兼容格式）
- ✅ **多种文件格式支持** - Text 和 Parquet 格式
- ✅ **Parquet 格式优势** - 查询速度快 10-100 倍，存储节省 20%
- ✅ **小时级分区** - 支持更细粒度的数据分区
- ✅ **SQS 事件通知** - 当文件上传到 S3 时自动发送通知
- ✅ 死信队列 (DLQ) 处理失败的通知
- ✅ 生命周期管理（IA、Glacier、Deep Archive）
- ✅ 服务器端加密
- ✅ CloudWatch 日志组用于监控
- ✅ 完整的 IAM 权限配置
- ✅ 自定义日志格式包含所有 30 个可用字段

## 📚 快速导航

- 🚀 [部署指南](#部署方式) - 快速开始部署
- 🗑️ [销毁资源](#清理资源) - 安全清理已部署的资源
- 📋 [命令参考](COMMANDS.md) - 所有可用命令的完整列表
- 📖 [文件格式说明](docs/file-format.md) - Text vs Parquet 格式详解
- 🎯 [Parquet 部署示例](examples/parquet-deployment.md) - 高性能配置指南
- 🔧 [故障排除](docs/troubleshooting.md) - 常见问题解决方案

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
# 基本部署（自动生成 bucket 名称和 SQS 队列，使用 Text 格式）
./deploy.sh vpc-12345678

# 使用 Parquet 格式（推荐）
./deploy.sh vpc-12345678 my-custom-bucket-name prod my-sqs-queue true parquet

# 启用小时级分区和 Parquet 格式
./deploy.sh vpc-12345678 my-custom-bucket-name prod my-sqs-queue true parquet true

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
| **fileFormat** | ❌ | text | 文件格式: `text` 或 `parquet` |
| **enableHourlyPartitions** | ❌ | false | 是否启用小时级分区 |

### 文件格式说明

#### Text 格式 (默认)
- 纯文本格式，字段用空格分隔
- 文件扩展名: `.gz`
- 适合小规模数据和临时分析

#### Parquet 格式 (推荐)
- Apache Parquet 列式存储格式
- 文件扩展名: `.parquet`
- **优势**:
  - 查询速度比文本格式快 10-100 倍
  - 存储空间节省 20%
  - 更好的压缩率和查询性能
- **适用场景**: 大规模数据分析，频繁查询，长期存储

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

### 日志字段 (30个字段)
我们的配置包含所有可用的 VPC Flow Logs 字段：

| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
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
| 11 | start | int | 捕获窗口开始时间 | 1418530010 |
| 12 | end | int | 捕获窗口结束时间 | 1418530070 |
| 13 | action | string | 流量动作 | ACCEPT/REJECT |
| 14 | log-status | string | Flow Log 状态 | OK/NODATA/SKIPDATA |
| 15 | vpc-id | string | VPC ID | vpc-12345678 |
| 16 | subnet-id | string | 子网 ID | subnet-12345678 |
| 17 | instance-id | string | 实例 ID | i-1234567890abcdef0 |
| 18 | tcp-flags | int | TCP 标志 | 19 |
| 19 | type | string | 流量类型 | IPv4/IPv6 |
| 20 | pkt-srcaddr | string | 数据包源地址 | 172.31.16.139 |
| 21 | pkt-dstaddr | string | 数据包目标地址 | 172.31.16.21 |
| 22 | region | string | AWS 区域 | us-east-1 |
| 23 | az-id | string | 可用区 ID | use1-az1 |
| 24 | sublocation-type | string | 子位置类型 | wavelength |
| 25 | sublocation-id | string | 子位置 ID | wl-bos-wlz-1 |
| 26 | pkt-src-aws-service | string | 源 AWS 服务 | AMAZON |
| 27 | pkt-dst-aws-service | string | 目标 AWS 服务 | S3 |
| 28 | flow-direction | string | 流方向 | ingress/egress |
| 29 | traffic-path | int | 流量路径 | 1-8 |

### 示例记录
```
5 123456789012 eni-1235b8ca123456789 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.16.139 172.31.16.21 us-east-1 use1-az1 - - - - ingress 1
```

**字段说明**:
- 前 21 个字段是传统的 Flow Log 字段
- 后 9 个字段是扩展字段，提供更详细的网络和服务信息
- 某些字段可能显示为 `-` 表示不适用或不可用

**注意**: 我们使用了自定义的日志格式字符串来确保包含所有可用的字段，这样可以避免 CDK 版本兼容性问题并提供最完整的网络流量信息。

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
  - 后缀: **自动根据文件格式调整**
    - Text 格式: `.gz`
    - Parquet 格式: `.parquet`
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
          "key": "vpc-flow-logs/year=2024/month=01/day=15/hour=10/vpc-flow-logs_20240115T1030Z_hash.parquet",
          "size": 1024
        }
      }
    }
  ]
}
```

## 清理资源

### 方式 1: 简化销毁脚本（推荐）

```bash
# 销毁指定环境的资源（无需 VPC ID）
./destroy-simple.sh dev

# 销毁生产环境资源
./destroy-simple.sh prod

# 强制销毁（跳过确认）
./destroy-simple.sh dev --force
```

### 方式 2: 直接使用 CloudFormation

```bash
# 删除 Stack
aws cloudformation delete-stack --stack-name VpcFlowLogsStack-dev

# 等待删除完成
aws cloudformation wait stack-delete-complete --stack-name VpcFlowLogsStack-dev
```

### 方式 3: 使用 CDK 命令（需要上下文参数）

```bash
# 需要提供原始部署时的 VPC ID
npx cdk destroy VpcFlowLogsStack-dev -c "vpcId=vpc-12345678" -c "environment=dev"

# 查看所有可用的 Stack
npx cdk list
```

### 重要注意事项

⚠️ **数据保护**:
- S3 存储桶设置了 `RETAIN` 保留策略，不会被自动删除
- 存储桶中的 VPC Flow Logs 数据需要手动清理
- CloudWatch 日志组会被删除
- SQS 队列会被删除

### 完全清理 S3 数据

如果确定不再需要历史数据：

```bash
# 1. 获取存储桶名称
aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-dev --query 'Stacks[0].Outputs[?OutputKey==`FlowLogsBucketName`].OutputValue' --output text

# 2. 清空存储桶（⚠️ 数据无法恢复）
aws s3 rm s3://your-bucket-name --recursive

# 3. 删除存储桶
aws s3 rb s3://your-bucket-name
```

## 故障排除

### 常见错误

1. **VPC 不存在**: 确保 VPC ID 正确且在当前区域
2. **权限不足**: 确保 AWS 凭证有足够权限创建资源
3. **Bucket 名称冲突**: S3 bucket 名称必须全局唯一
4. **销毁时 VPC ID 错误**: 
   - 错误信息: `VPC ID is required. Please provide it via context`
   - 解决方案: 使用 `./destroy-simple.sh` 脚本，或提供原始的 VPC ID 参数
5. **文件格式验证错误**:
   - 错误信息: `Model validation failed (#/DestinationOptions/FileFormat: #: only 1 subschema matches out of 2)`
   - 原因: CloudFormation 需要首字母大写的格式值 (`Text`, `Parquet`)
   - 解决方案: 代码已自动处理大小写转换

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
  -- 基础字段
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
  start_time bigint,
  end_time bigint,
  action string,
  log_status string,
  
  -- VPC 和实例字段
  vpc_id string,
  subnet_id string,
  instance_id string,
  
  -- 网络详细信息字段
  tcp_flags int,
  type string,
  pkt_srcaddr string,
  pkt_dstaddr string,
  
  -- 区域和位置字段
  region string,
  az_id string,
  sublocation_type string,
  sublocation_id string,
  
  -- AWS 服务字段
  pkt_src_aws_service string,
  pkt_dst_aws_service string,
  
  -- 流量路径字段
  flow_direction string,
  traffic_path int
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
  flow_direction,
  COUNT(*) as record_count,
  SUM(bytes) as total_bytes,
  COUNT(DISTINCT srcaddr) as unique_sources
FROM vpc_flow_logs
WHERE year='2024' AND month='01' AND day='15'
GROUP BY action, flow_direction;

-- 查找被拒绝的流量
SELECT srcaddr, dstaddr, dstport, COUNT(*) as attempts
FROM vpc_flow_logs
WHERE action='REJECT' AND year='2024' AND month='01' AND day='15'
GROUP BY srcaddr, dstaddr, dstport
ORDER BY attempts DESC
LIMIT 10;

-- 分析 AWS 服务流量
SELECT 
  pkt_src_aws_service,
  pkt_dst_aws_service,
  traffic_path,
  COUNT(*) as connections,
  SUM(bytes) as total_bytes
FROM vpc_flow_logs
WHERE year='2024' AND month='01' AND day='15'
  AND (pkt_src_aws_service != '-' OR pkt_dst_aws_service != '-')
GROUP BY pkt_src_aws_service, pkt_dst_aws_service, traffic_path
ORDER BY total_bytes DESC
LIMIT 20;

-- 分析跨区域流量
SELECT 
  region,
  az_id,
  flow_direction,
  COUNT(*) as record_count,
  SUM(bytes) as total_bytes
FROM vpc_flow_logs
WHERE year='2024' AND month='01' AND day='15'
GROUP BY region, az_id, flow_direction
ORDER BY total_bytes DESC;

-- 查找异常流量路径
SELECT 
  traffic_path,
  CASE traffic_path
    WHEN 1 THEN 'Same VPC'
    WHEN 2 THEN 'Internet Gateway'
    WHEN 3 THEN 'VPN Gateway'
    WHEN 4 THEN 'Intra-region Peering'
    WHEN 5 THEN 'Inter-region Peering'
    WHEN 6 THEN 'Local Gateway'
    WHEN 7 THEN 'Gateway Load Balancer'
    WHEN 8 THEN 'Internet Gateway (IPv6)'
    ELSE 'Unknown'
  END as path_description,
  COUNT(*) as record_count,
  SUM(bytes) as total_bytes
FROM vpc_flow_logs
WHERE year='2024' AND month='01' AND day='15'
GROUP BY traffic_path
ORDER BY total_bytes DESC;
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

- [详细文件格式说明](docs/file-format.md) - 完整的 30 个字段说明
- [字段对照表](docs/field-mapping.md) - CDK 配置与 Athena 字段对照
- [故障排除指南](docs/troubleshooting.md) - 常见问题和解决方案
- [Python 解析工具](tools/flow-log-parser.py) - 文件下载和解析工具
- [Lambda 处理示例](examples/lambda-sqs-processor.py) - SQS 事件处理示例
- [SQS 消息处理示例](examples/sqs-message-processor.py) - 轮询处理示例