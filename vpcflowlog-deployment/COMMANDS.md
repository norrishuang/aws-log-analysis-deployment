# VPC Flow Logs 命令参考

## 🚀 部署命令

### 基础部署
```bash
# 基本部署（使用默认设置）
./deploy.sh vpc-12345678

# 指定环境和存储桶
./deploy.sh vpc-12345678 my-bucket prod

# 启用小时分区
./deploy.sh vpc-12345678 my-bucket prod my-queue true true
```

### 完整参数
```bash
./deploy.sh <vpc-id> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [hourly-partitions]
```

### 参数说明
- `vpc-id`: VPC ID（必需）
- `bucket-name`: S3 存储桶名称（可选，默认自动生成）
- `environment`: 环境名称（可选，默认 dev）
- `sqs-queue-name`: SQS 队列名称（可选，默认自动生成）
- `enable-sqs`: 是否启用 SQS 通知（可选，默认 true）
- `hourly-partitions`: 是否启用小时分区（可选，默认 false）

## 🗑️ 销毁命令

### 方法 1: 简化销毁脚本（推荐）
```bash
# 销毁开发环境
./destroy-simple.sh dev

# 销毁生产环境
./destroy-simple.sh prod

# 强制销毁（跳过确认）
./destroy-simple.sh prod --force
```

### 方法 2: 完整销毁脚本
```bash
# 销毁开发环境（需要 VPC ID）
./destroy.sh dev

# 销毁生产环境
./destroy.sh prod

# 强制销毁（跳过确认）
./destroy.sh prod --force
```

### 方法 3: 直接使用 CloudFormation
```bash
# 删除 Stack
aws cloudformation delete-stack --stack-name VpcFlowLogsStack-dev

# 等待删除完成
aws cloudformation wait stack-delete-complete --stack-name VpcFlowLogsStack-dev

# 查看所有 Stack
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
```

### 方法 4: 直接使用 CDK（需要上下文参数）
```bash
# 销毁指定 Stack（需要提供 VPC ID）
npx cdk destroy VpcFlowLogsStack-dev -c "vpcId=vpc-12345678" -c "environment=dev"

# 查看所有 Stack
npx cdk list
```

## 📋 管理命令

### 查看资源
```bash
# 查看 CloudFormation Stack
aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-dev

# 查看 S3 存储桶
aws s3 ls | grep vpc-flow-logs

# 查看 SQS 队列
aws sqs list-queues | grep vpc-flow-logs

# 查看 VPC Flow Logs
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-12345678"
```

### 监控命令
```bash
# 查看 S3 中的日志文件
aws s3 ls s3://your-bucket-name/vpc-flow-logs/ --recursive

# 查看 SQS 队列消息
aws sqs receive-message --queue-url https://sqs.region.amazonaws.com/account/queue-name

# 查看 CloudWatch 日志
aws logs describe-log-groups --log-group-name-prefix /aws/vpc/flowlogs
```

## 🧪 测试命令

### CDK 相关
```bash
# 构建项目
npm run build

# 语法检查
npm run test

# 生成 CloudFormation 模板
npx cdk synth

# 比较变更
npx cdk diff
```



## 🔧 工具命令

### 日志解析
```bash
# 下载并解析日志文件
python3 tools/flow-log-parser.py --s3-path s3://bucket/path/file.gz

# 转换为 CSV 格式
python3 tools/flow-log-parser.py --local-file file.gz --format csv

# 分析流量模式
python3 tools/flow-log-parser.py --local-file file.gz --analyze
```

### SQS 消息处理
```bash
# 处理 SQS 消息
python3 examples/sqs-message-processor.py --queue-url https://sqs.region.amazonaws.com/account/queue-name

# 指定区域
python3 examples/sqs-message-processor.py --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/my-queue --region us-east-1
```

## 🧹 清理命令

### 完全清理 S3 数据
```bash
# ⚠️ 警告：以下命令会永久删除数据

# 1. 获取存储桶名称
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-dev --query 'Stacks[0].Outputs[?OutputKey==`FlowLogsBucketName`].OutputValue' --output text)

# 2. 清空存储桶
aws s3 rm s3://$BUCKET_NAME --recursive

# 3. 删除存储桶
aws s3 rb s3://$BUCKET_NAME
```

### 清理 CloudWatch 日志
```bash
# 删除日志组
aws logs delete-log-group --log-group-name /aws/vpc/flowlogs/dev
```

## 📊 查询命令

### Athena 查询示例
```sql
-- 创建文本格式表
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
  flowlogstatus string
)
PARTITIONED BY (
  year string,
  month string,
  day string,
  hour string
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ' '
LOCATION 's3://your-bucket-name/vpc-flow-logs/';

-- 查询示例
SELECT srcaddr, dstaddr, SUM(bytes) as total_bytes
FROM vpc_flow_logs 
WHERE year = '2024' AND month = '01' AND day = '15'
GROUP BY srcaddr, dstaddr
ORDER BY total_bytes DESC
LIMIT 10;
```

## 🚨 故障排除命令

### 检查部署状态
```bash
# 检查 Stack 状态
aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-dev --query 'Stacks[0].StackStatus'

# 查看 Stack 事件
aws cloudformation describe-stack-events --stack-name VpcFlowLogsStack-dev

# 检查资源状态
aws cloudformation describe-stack-resources --stack-name VpcFlowLogsStack-dev
```

### 验证配置
```bash
# 验证 VPC 存在
aws ec2 describe-vpcs --vpc-ids vpc-12345678

# 验证 Flow Logs 配置
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-12345678"

# 测试 S3 访问
aws s3 ls s3://your-bucket-name/

# 测试 SQS 访问
aws sqs get-queue-attributes --queue-url https://sqs.region.amazonaws.com/account/queue-name
```

## 📈 监控命令

### CloudWatch 指标
```bash
# S3 存储使用量
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=your-bucket-name Name=StorageType,Value=StandardStorage \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 86400 \
  --statistics Average

# SQS 队列深度
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfVisibleMessages \
  --dimensions Name=QueueName,Value=your-queue-name \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

---

## 🔗 快速链接

- [部署指南](README.md#部署方式)
- [配置参数](README.md#配置参数)
- [技术说明](docs/technical-notes.md)
- [故障排除](docs/troubleshooting.md)
- [字段映射](docs/field-mapping.md)