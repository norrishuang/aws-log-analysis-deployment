#!/bin/bash

# ELB Access Logs CDK 部署脚本
# 使用方法: ./deploy.sh <load-balancer-arn> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [log-prefix]

set -e

# 检查参数
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <load-balancer-arn> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [log-prefix]"
    echo "示例: $0 arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-lb/1234567890abcdef my-elb-logs-bucket prod my-queue-name true elb-access-logs"
    echo "参数说明:"
    echo "  load-balancer-arn: Application Load Balancer ARN (必需)"
    echo "  bucket-name: S3 存储桶名称 (可选，默认自动生成)"
    echo "  environment: 环境名称 (可选，默认 dev)"
    echo "  sqs-queue-name: SQS 队列名称 (可选，默认自动生成)"
    echo "  enable-sqs: 是否启用 SQS 通知 (可选，默认 true)"
    echo "  log-prefix: S3 日志前缀 (可选，默认 elb-access-logs)"
    exit 1
fi

LOAD_BALANCER_ARN="$1"
BUCKET_NAME="${2:-}"
ENVIRONMENT="${3:-dev}"
SQS_QUEUE_NAME="${4:-}"
ENABLE_SQS="${5:-true}"
LOG_PREFIX="${6:-elb-access-logs}"

echo "开始部署 ELB Access Logs..."
echo "Load Balancer ARN: $LOAD_BALANCER_ARN"
echo "Bucket Name: ${BUCKET_NAME:-自动生成}"
echo "Environment: $ENVIRONMENT"
echo "SQS Queue Name: ${SQS_QUEUE_NAME:-自动生成}"
echo "Enable SQS Notification: $ENABLE_SQS"
echo "Log Prefix: $LOG_PREFIX"

# 验证 AWS 凭证
echo "验证 AWS 凭证..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "错误: AWS 凭证未配置或无效"
    echo "请运行 'aws configure' 配置凭证"
    exit 1
fi

# 验证 Load Balancer ARN 格式
if [[ ! "$LOAD_BALANCER_ARN" =~ ^arn:aws:elasticloadbalancing:[^:]+:[^:]+:loadbalancer/app/.+ ]]; then
    echo "错误: Load Balancer ARN 格式无效"
    echo "正确格式: arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/load-balancer-name/load-balancer-id"
    exit 1
fi

# 从 ARN 中提取区域和账户信息
IFS=':' read -ra ARN_PARTS <<< "$LOAD_BALANCER_ARN"
REGION="${ARN_PARTS[3]}"
ACCOUNT_ID="${ARN_PARTS[4]}"

echo "检测到的区域: $REGION"
echo "检测到的账户: $ACCOUNT_ID"

# 验证 Load Balancer 是否存在
echo "验证 Load Balancer 是否存在..."
if ! aws elbv2 describe-load-balancers --load-balancer-arns "$LOAD_BALANCER_ARN" --region "$REGION" > /dev/null 2>&1; then
    echo "错误: Load Balancer $LOAD_BALANCER_ARN 不存在或无权限访问"
    echo "请确保:"
    echo "1. Load Balancer ARN 正确"
    echo "2. Load Balancer 在指定区域 ($REGION)"
    echo "3. 有足够的权限访问 Load Balancer"
    exit 1
fi

# 验证 SQS 参数
if [[ "$ENABLE_SQS" != "true" && "$ENABLE_SQS" != "false" ]]; then
    echo "错误: SQS 通知参数必须是 'true' 或 'false'"
    exit 1
fi

echo "验证通过，继续部署..."

# 安装依赖
echo "安装 NPM 依赖..."
npm install

# 构建项目
echo "构建 TypeScript 项目..."
npm run build

# 部署 CDK Stack
echo "部署 CDK Stack..."

# 基础参数
npx cdk deploy \
    --require-approval never \
    -c "loadBalancerArn=$LOAD_BALANCER_ARN" \
    -c "environment=$ENVIRONMENT" \
    -c "enableSqsNotification=$ENABLE_SQS" \
    -c "logPrefix=$LOG_PREFIX" \
    ${BUCKET_NAME:+-c "bucketName=$BUCKET_NAME"} \
    ${SQS_QUEUE_NAME:+-c "sqsQueueName=$SQS_QUEUE_NAME"}

echo ""
echo "部署完成！"
echo ""
echo "Stack 名称: ElbLogsStack-$ENVIRONMENT"
echo ""
echo "查看部署的资源:"
echo "1. CloudFormation Stack:"
echo "   aws cloudformation describe-stacks --stack-name ElbLogsStack-$ENVIRONMENT --region $REGION"
echo ""
echo "2. S3 存储桶:"
echo "   aws s3 ls | grep elb-access-logs"
echo ""
echo "3. SQS 队列:"
echo "   aws sqs list-queues --region $REGION | grep elb-logs"
echo ""
echo "4. Load Balancer 访问日志配置:"
echo "   aws elbv2 describe-load-balancer-attributes --load-balancer-arn $LOAD_BALANCER_ARN --region $REGION | grep access_logs"
echo ""
echo "5. 查看 S3 中的日志文件 (需要等待几分钟):"
echo "   BUCKET_NAME=\$(aws s3 ls | grep elb-access-logs | awk '{print \$3}')"
echo "   aws s3 ls s3://\$BUCKET_NAME/$LOG_PREFIX/ --recursive"
echo ""
echo "6. 测试访问日志生成:"
echo "   # 向 Load Balancer 发送一些请求，然后检查 S3 存储桶"
echo "   # 日志文件通常在 5 分钟内生成"
echo ""
echo "OpenSearch Ingestion Pipeline 配置文件位置:"
echo "   dashborad-script/osi-elb-logs.yml"
echo ""
echo "记得更新 OSI 配置文件中的 SQS 队列 URL 和 OpenSearch 集群端点！"