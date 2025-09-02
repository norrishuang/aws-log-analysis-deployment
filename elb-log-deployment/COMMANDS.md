# ELB Access Logs 常用命令

## 部署命令

### 基本部署
```bash
# 使用部署脚本（推荐）
./deploy.sh arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef

# 指定所有参数
./deploy.sh \
  arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef \
  my-elb-logs-bucket \
  prod \
  elb-notifications \
  true \
  elb-access-logs
```

### CDK 直接部署
```bash
# 基本部署
npx cdk deploy -c loadBalancerArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef

# 完整参数部署
npx cdk deploy \
  -c loadBalancerArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef \
  -c environment=prod \
  -c bucketName=my-elb-logs-bucket \
  -c enableSqsNotification=true \
  -c sqsQueueName=elb-notifications \
  -c logPrefix=elb-access-logs
```

## 验证命令

### 检查 Load Balancer 配置
```bash
# 查看 Load Balancer 属性
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef

# 只查看访问日志相关属性
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef \
  --query 'Attributes[?contains(Key, `access_logs`)]'
```

### 检查 S3 存储桶
```bash
# 列出所有 ELB 日志存储桶
aws s3 ls | grep elb-access-logs

# 查看存储桶中的日志文件
aws s3 ls s3://elb-access-logs-prod-123456789012-us-east-1/elb-access-logs/ --recursive

# 查看最新的日志文件
aws s3 ls s3://elb-access-logs-prod-123456789012-us-east-1/elb-access-logs/ --recursive | tail -10
```

### 检查 SQS 队列
```bash
# 列出 ELB 相关队列
aws sqs list-queues | grep elb-logs

# 查看队列属性
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-prod-notifications \
  --attribute-names All

# 查看队列中的消息数量
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-prod-notifications \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible
```

## 监控命令

### CloudWatch 日志
```bash
# 查看 CloudWatch 日志组
aws logs describe-log-groups --log-group-name-prefix "/aws/elb/accesslogs"

# 查看最新的日志事件
aws logs describe-log-streams \
  --log-group-name "/aws/elb/accesslogs/prod" \
  --order-by LastEventTime \
  --descending \
  --max-items 5
```

### CloudFormation Stack
```bash
# 查看 Stack 状态
aws cloudformation describe-stacks --stack-name ElbLogsStack-prod

# 查看 Stack 资源
aws cloudformation describe-stack-resources --stack-name ElbLogsStack-prod

# 查看 Stack 输出
aws cloudformation describe-stacks \
  --stack-name ElbLogsStack-prod \
  --query 'Stacks[0].Outputs'
```

## 测试命令

### 生成测试流量
```bash
# 获取 Load Balancer DNS 名称
LB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef \
  --query 'LoadBalancers[0].DNSName' --output text)

# 发送测试请求
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://$LB_DNS/
  sleep 1
done
```

### 检查日志生成
```bash
# 等待 5-10 分钟后检查日志文件
BUCKET_NAME=$(aws s3 ls | grep elb-access-logs | awk '{print $3}')
aws s3 ls s3://$BUCKET_NAME/elb-access-logs/ --recursive | tail -5

# 下载并查看最新的日志文件
LATEST_LOG=$(aws s3 ls s3://$BUCKET_NAME/elb-access-logs/ --recursive | tail -1 | awk '{print $4}')
aws s3 cp s3://$BUCKET_NAME/$LATEST_LOG - | gunzip | head -10
```

## OpenSearch 集成命令

### 创建 OSI Pipeline
```bash
# 创建 OpenSearch Ingestion Pipeline
aws osis create-pipeline \
  --pipeline-name elb-logs-pipeline \
  --pipeline-configuration-body file://dashborad-script/osi-elb-logs.yml \
  --min-units 1 \
  --max-units 4

# 查看 Pipeline 状态
aws osis get-pipeline --pipeline-name elb-logs-pipeline

# 列出所有 Pipeline
aws osis list-pipelines
```

### 更新 OSI 配置
```bash
# 更新 Pipeline 配置
aws osis update-pipeline \
  --pipeline-name elb-logs-pipeline \
  --pipeline-configuration-body file://dashborad-script/osi-elb-logs.yml

# 启动 Pipeline
aws osis start-pipeline --pipeline-name elb-logs-pipeline

# 停止 Pipeline
aws osis stop-pipeline --pipeline-name elb-logs-pipeline
```

## 故障排除命令

### 检查权限问题
```bash
# 检查 S3 存储桶策略
aws s3api get-bucket-policy --bucket elb-access-logs-prod-123456789012-us-east-1

# 检查 S3 事件通知配置
aws s3api get-bucket-notification-configuration --bucket elb-access-logs-prod-123456789012-us-east-1

# 检查 SQS 队列策略
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-prod-notifications \
  --attribute-names Policy
```

### 检查死信队列
```bash
# 查看死信队列中的消息
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-prod-dlq \
  --max-number-of-messages 10

# 清空死信队列
aws sqs purge-queue \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/elb-logs-prod-dlq
```

### Lambda 函数日志
```bash
# 查看 Lambda 函数日志
aws logs describe-log-groups | grep EnableAccessLogsHandler

# 查看最新的 Lambda 执行日志
LOG_GROUP=$(aws logs describe-log-groups --query 'logGroups[?contains(logGroupName, `EnableAccessLogsHandler`)].logGroupName' --output text)
aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --max-items 1
```

## 清理命令

### 销毁资源
```bash
# 使用销毁脚本
./destroy.sh prod

# 直接使用 CDK
npx cdk destroy ElbLogsStack-prod --force
```

### 手动清理 S3
```bash
# 列出需要清理的存储桶
aws s3 ls | grep elb-access-logs

# 删除存储桶中的所有对象
BUCKET_NAME=elb-access-logs-prod-123456789012-us-east-1
aws s3 rm s3://$BUCKET_NAME --recursive

# 删除存储桶
aws s3 rb s3://$BUCKET_NAME
```

## 有用的查询命令

### 获取部署信息
```bash
# 获取 Stack 输出的所有信息
aws cloudformation describe-stacks \
  --stack-name ElbLogsStack-prod \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

# 获取 SQS 队列 URL
aws cloudformation describe-stacks \
  --stack-name ElbLogsStack-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`NotificationQueueUrl`].OutputValue' \
  --output text

# 获取 S3 存储桶名称
aws cloudformation describe-stacks \
  --stack-name ElbLogsStack-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`ElbLogsBucketName`].OutputValue' \
  --output text
```

### 日志分析
```bash
# 统计日志文件数量
aws s3 ls s3://$BUCKET_NAME/elb-access-logs/ --recursive | wc -l

# 查看日志文件大小统计
aws s3 ls s3://$BUCKET_NAME/elb-access-logs/ --recursive --human-readable --summarize

# 按日期查看日志文件
aws s3 ls s3://$BUCKET_NAME/elb-access-logs/AWSLogs/123456789012/elasticloadbalancing/us-east-1/2024/01/15/ --recursive
```