#!/bin/bash

# VPC Flow Logs CDK 部署脚本
# 使用方法: ./deploy.sh <vpc-id> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [hourly-partitions]

set -e

# 检查参数
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <vpc-id> [bucket-name] [environment] [sqs-queue-name] [enable-sqs] [hourly-partitions]"
    echo "示例: $0 vpc-12345678 my-flow-logs-bucket prod my-queue-name true true"
    echo "参数说明:"
    echo "  vpc-id: VPC ID (必需)"
    echo "  bucket-name: S3 存储桶名称 (可选，默认自动生成)"
    echo "  environment: 环境名称 (可选，默认 dev)"
    echo "  sqs-queue-name: SQS 队列名称 (可选，默认自动生成)"
    echo "  enable-sqs: 是否启用 SQS 通知 (可选，默认 true)"
    echo "  hourly-partitions: 是否启用小时级分区 true/false (可选，默认 false)"
    exit 1
fi

VPC_ID="$1"
BUCKET_NAME="${2:-}"
ENVIRONMENT="${3:-dev}"
SQS_QUEUE_NAME="${4:-}"
ENABLE_SQS="${5:-true}"
HOURLY_PARTITIONS="${6:-false}"

echo "开始部署 VPC Flow Logs..."
echo "VPC ID: $VPC_ID"
echo "Bucket Name: ${BUCKET_NAME:-自动生成}"
echo "Environment: $ENVIRONMENT"
echo "SQS Queue Name: ${SQS_QUEUE_NAME:-自动生成}"
echo "Enable SQS Notification: $ENABLE_SQS"
echo "Hourly Partitions: $HOURLY_PARTITIONS"

# 验证 AWS 凭证
echo "验证 AWS 凭证..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "错误: AWS 凭证未配置或无效"
    echo "请运行 'aws configure' 配置凭证"
    exit 1
fi

# 验证 VPC 是否存在
echo "验证 VPC 是否存在..."
if ! aws ec2 describe-vpcs --vpc-ids "$VPC_ID" > /dev/null 2>&1; then
    echo "错误: VPC $VPC_ID 不存在或无权限访问"
    echo "请确保:"
    echo "1. VPC ID 正确"
    echo "2. VPC 在当前 AWS 区域"
    echo "3. 有足够的权限访问 VPC"
    exit 1
fi

# 验证小时分区参数
if [[ "$HOURLY_PARTITIONS" != "true" && "$HOURLY_PARTITIONS" != "false" ]]; then
    echo "错误: 小时分区参数必须是 'true' 或 'false'"
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
    -c "vpcId=$VPC_ID" \
    -c "environment=$ENVIRONMENT" \
    -c "enableSqsNotification=$ENABLE_SQS" \
    -c "enableHourlyPartitions=$HOURLY_PARTITIONS" \
    ${BUCKET_NAME:+-c "bucketName=$BUCKET_NAME"} \
    ${SQS_QUEUE_NAME:+-c "sqsQueueName=$SQS_QUEUE_NAME"}

echo ""
echo "部署完成！"
echo ""
echo "Stack 名称: VpcFlowLogsStack-$ENVIRONMENT"
echo ""
echo "查看部署的资源:"
echo "1. CloudFormation Stack:"
echo "   aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-$ENVIRONMENT"
echo ""
echo "2. S3 存储桶:"
echo "   aws s3 ls | grep vpc-flow-logs"
echo ""
echo "3. SQS 队列:"
echo "   aws sqs list-queues | grep vpc-flow-logs"
echo ""
echo "4. VPC Flow Logs:"
echo "   aws ec2 describe-flow-logs --filter \"Name=resource-id,Values=$VPC_ID\""
echo ""
echo "5. 查看 S3 中的日志文件 (需要等待几分钟):"
echo "   aws s3 ls s3://\$(aws s3 ls | grep vpc-flow-logs | awk '{print \$3}')/vpc-flow-logs/ --recursive"