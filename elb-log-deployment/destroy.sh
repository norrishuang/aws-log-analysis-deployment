#!/bin/bash

# ELB Access Logs CDK 销毁脚本
# 使用方法: ./destroy.sh [environment]

set -e

ENVIRONMENT="${1:-dev}"

echo "开始销毁 ELB Access Logs Stack..."
echo "Environment: $ENVIRONMENT"
echo "Stack Name: ElbLogsStack-$ENVIRONMENT"

# 验证 AWS 凭证
echo "验证 AWS 凭证..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "错误: AWS 凭证未配置或无效"
    echo "请运行 'aws configure' 配置凭证"
    exit 1
fi

# 确认销毁操作
echo ""
echo "警告: 这将删除以下资源:"
echo "- CloudFormation Stack: ElbLogsStack-$ENVIRONMENT"
echo "- SQS 队列和死信队列"
echo "- CloudWatch 日志组"
echo "- Lambda 函数 (用于启用/禁用访问日志)"
echo ""
echo "注意: S3 存储桶将被保留 (设置了 RETAIN 策略)"
echo "如需删除 S3 存储桶，请手动删除"
echo ""

read -p "确定要继续吗? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

# 构建项目
echo "构建 TypeScript 项目..."
npm run build

# 销毁 CDK Stack
echo "销毁 CDK Stack..."
npx cdk destroy ElbLogsStack-$ENVIRONMENT --force

echo ""
echo "Stack 销毁完成！"
echo ""
echo "手动清理步骤 (如需要):"
echo "1. 删除 S3 存储桶中的所有对象:"
echo "   BUCKET_NAME=\$(aws s3 ls | grep elb-access-logs-$ENVIRONMENT | awk '{print \$3}')"
echo "   aws s3 rm s3://\$BUCKET_NAME --recursive"
echo ""
echo "2. 删除 S3 存储桶:"
echo "   aws s3 rb s3://\$BUCKET_NAME"
echo ""
echo "3. 检查 Load Balancer 访问日志是否已禁用:"
echo "   aws elbv2 describe-load-balancer-attributes --load-balancer-arn <YOUR_LB_ARN> | grep access_logs"