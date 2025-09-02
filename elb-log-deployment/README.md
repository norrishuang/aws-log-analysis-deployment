# ELB Access Logs CDK Deployment

这个项目使用 AWS CDK 自动化部署 Application Load Balancer (ALB) 访问日志收集基础设施，包括 S3 存储、SQS 事件通知和 OpenSearch 数据摄取管道。

## 功能特性

- **自动启用 ELB 访问日志**：为指定的 Application Load Balancer 启用访问日志
- **S3 存储**：创建专用的 S3 存储桶存储访问日志，包含生命周期管理
- **SQS 事件通知**：当新的日志文件写入 S3 时自动发送通知
- **安全配置**：正确配置 ELB 服务账户权限和 S3 存储桶策略
- **监控支持**：创建 CloudWatch 日志组用于监控
- **OpenSearch 集成**：提供 OpenSearch Ingestion Pipeline 配置

## 架构组件

```
ALB → S3 Bucket → SQS Queue → OpenSearch Ingestion Pipeline → OpenSearch
                     ↓
               Dead Letter Queue
```

### 主要资源

1. **S3 存储桶**：存储 ELB 访问日志
   - 启用版本控制
   - 生命周期管理（IA → Glacier → Deep Archive）
   - 服务器端加密
   - 阻止公共访问

2. **SQS 队列**：接收 S3 事件通知
   - 主队列：处理新文件通知
   - 死信队列：处理失败的消息
   - 加密和可见性超时配置

3. **IAM 权限**：
   - ELB 服务账户写入 S3 的权限
   - Lambda 函数管理 ELB 属性的权限

4. **Lambda 函数**：自动启用/禁用 ELB 访问日志

## 快速开始

### 前置条件

- Node.js 18+ 和 npm
- AWS CLI 已配置
- AWS CDK CLI (`npm install -g aws-cdk`)
- 现有的 Application Load Balancer

### 1. 安装依赖

```bash
cd elb-log-deployment
npm install
```

### 2. 配置参数

复制配置示例文件：
```bash
cp config.example.json config.json
```

编辑 `config.json` 文件，设置你的 Load Balancer ARN 和其他参数。

### 3. 部署

使用部署脚本：
```bash
./deploy.sh <load-balancer-arn> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [log-prefix]
```

示例：
```bash
./deploy.sh arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef my-elb-logs prod elb-notifications true elb-access-logs
```

或者直接使用 CDK：
```bash
npm run build
npx cdk deploy -c loadBalancerArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef
```

### 4. 验证部署

检查 Load Balancer 访问日志是否已启用：
```bash
aws elbv2 describe-load-balancer-attributes --load-balancer-arn <YOUR_LB_ARN> | grep access_logs
```

查看 S3 存储桶中的日志文件（需要等待几分钟）：
```bash
aws s3 ls s3://<bucket-name>/elb-access-logs/ --recursive
```

## 配置参数

### 必需参数

- `loadBalancerArn`: Application Load Balancer 的 ARN

### 可选参数

- `bucketName`: S3 存储桶名称（默认自动生成）
- `environment`: 环境名称（默认 "dev"）
- `enableSqsNotification`: 是否启用 SQS 通知（默认 true）
- `sqsQueueName`: SQS 队列名称（默认自动生成）
- `logPrefix`: S3 日志前缀（默认 "elb-access-logs"）

### 通过 CDK Context 传递参数

```bash
npx cdk deploy \
  -c loadBalancerArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef \
  -c environment=prod \
  -c bucketName=my-elb-logs-bucket \
  -c enableSqsNotification=true
```

### 通过环境变量传递参数

```bash
export LOAD_BALANCER_ARN=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef
export ENVIRONMENT=prod
export BUCKET_NAME=my-elb-logs-bucket
npx cdk deploy
```

## OpenSearch 集成

### 1. 更新 OSI 配置

编辑 `dashborad-script/osi-elb-logs.yml` 文件，更新以下配置：

```yaml
source:
  s3:
    sqs:
      queue_url: 'https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-notifications'
sink:
  - opensearch:
      hosts:
        - 'https://your-opensearch-cluster-endpoint'
```

### 2. 部署 OSI Pipeline

使用 AWS CLI 或控制台部署 OpenSearch Ingestion Pipeline：

```bash
aws osis create-pipeline \
  --pipeline-name elb-logs-pipeline \
  --pipeline-configuration-body file://dashborad-script/osi-elb-logs.yml \
  --min-units 1 \
  --max-units 4
```

## ELB 访问日志格式

ELB 访问日志包含以下字段：

- `type`: 请求类型 (http, https, h2, grpcs, ws, wss)
- `time`: 时间戳 (ISO 8601 格式)
- `elb`: Load Balancer 资源 ID
- `client:port`: 客户端 IP 和端口
- `target:port`: 目标 IP 和端口
- `request_processing_time`: 请求处理时间
- `target_processing_time`: 目标处理时间
- `response_processing_time`: 响应处理时间
- `elb_status_code`: ELB 状态码
- `target_status_code`: 目标状态码
- `received_bytes`: 接收字节数
- `sent_bytes`: 发送字节数
- `request`: HTTP 请求行
- `user_agent`: User-Agent 字符串
- `ssl_cipher`: SSL 加密套件
- `ssl_protocol`: SSL 协议版本
- 以及更多字段...

详细格式请参考：https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html#access-log-entry-syntax

## 监控和故障排除

### 查看 CloudWatch 日志

```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/elb/accesslogs"
```

### 检查 SQS 队列消息

```bash
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All
```

### 验证 S3 事件通知

```bash
aws s3api get-bucket-notification-configuration --bucket <bucket-name>
```

### 常见问题

1. **访问日志未生成**
   - 确保 Load Balancer 有流量
   - 检查 ELB 服务账户权限
   - 验证 S3 存储桶策略

2. **SQS 消息未接收**
   - 检查 S3 事件通知配置
   - 验证 SQS 队列权限
   - 查看死信队列中的失败消息

3. **权限错误**
   - 确保使用正确的 ELB 服务账户 ID
   - 检查 S3 存储桶策略
   - 验证 Lambda 函数权限

## 成本优化

### S3 生命周期管理

默认配置的生命周期规则：
- 30 天后转移到 IA (Infrequent Access)
- 90 天后转移到 Glacier
- 365 天后转移到 Deep Archive
- 30 天后删除旧版本

### SQS 成本

- 使用标准队列（成本较低）
- 配置适当的消息保留期
- 使用死信队列避免重复处理

## 清理资源

### 销毁 Stack

```bash
./destroy.sh [environment]
```

或者：
```bash
npx cdk destroy ElbLogsStack-<environment>
```

### 手动清理

Stack 销毁后，S3 存储桶会被保留。如需完全清理：

```bash
# 删除 S3 存储桶中的所有对象
aws s3 rm s3://<bucket-name> --recursive

# 删除 S3 存储桶
aws s3 rb s3://<bucket-name>
```

## 支持的区域

支持所有有 Application Load Balancer 服务的 AWS 区域。每个区域都有对应的 ELB 服务账户 ID。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！