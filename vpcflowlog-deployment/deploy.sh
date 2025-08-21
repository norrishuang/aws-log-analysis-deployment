#!/bin/bash

# VPC Flow Logs CDK 部署脚本
# 使用方法: ./deploy.sh <vpc-id> [bucket-name] [environment]

set -e

# 检查参数
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <vpc-id> [bucket-name] [environment]"
    echo "示例: $0 vpc-12345678 my-flow-logs-bucket prod"
    exit 1
fi

VPC_ID=$1
BUCKET_NAME=${2:-""}
ENVIRONMENT=${3:-"dev"}

echo "开始部署 VPC Flow Logs..."
echo "VPC ID: $VPC_ID"
echo "Bucket Name: ${BUCKET_NAME:-"自动生成"}"
echo "Environment: $ENVIRONMENT"

# 安装依赖
echo "安装 NPM 依赖..."
npm install

# 构建项目
echo "构建 TypeScript 项目..."
npm run build

# 部署 CDK Stack
echo "部署 CDK Stack..."
if [ -n "$BUCKET_NAME" ]; then
    npx cdk deploy --require-approval never \
        -c vpcId=$VPC_ID \
        -c bucketName=$BUCKET_NAME \
        -c environment=$ENVIRONMENT
else
    npx cdk deploy --require-approval never \
        -c vpcId=$VPC_ID \
        -c environment=$ENVIRONMENT
fi

echo "部署完成！"