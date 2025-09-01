#!/bin/bash

# VPC Flow Logs CDK 销毁脚本
# 使用方法: ./destroy.sh [environment] [--force]

set -e

ENVIRONMENT="${1:-dev}"
FORCE_FLAG="${2}"

echo "🗑️  准备销毁 VPC Flow Logs 资源..."
echo "Environment: $ENVIRONMENT"
echo "Stack Name: VpcFlowLogsStack-$ENVIRONMENT"

# 验证 AWS 凭证
echo "验证 AWS 凭证..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ 错误: AWS 凭证未配置或无效"
    echo "请运行 'aws configure' 配置凭证"
    exit 1
fi

# 检查 Stack 是否存在
echo "检查 Stack 是否存在..."
STACK_NAME="VpcFlowLogsStack-$ENVIRONMENT"

if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" > /dev/null 2>&1; then
    echo "❌ Stack '$STACK_NAME' 不存在"
    echo "可用的 Stack:"
    aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[?contains(StackName, `VpcFlowLogsStack`)].StackName' --output table
    exit 1
fi

# 显示将要删除的资源
echo ""
echo "📋 将要删除的资源:"
aws cloudformation describe-stack-resources --stack-name "$STACK_NAME" --query 'StackResources[].{Type:ResourceType,LogicalId:LogicalResourceId,PhysicalId:PhysicalResourceId}' --output table

echo ""
echo "⚠️  重要提醒:"
echo "1. S3 存储桶中的数据不会被自动删除（保护策略）"
echo "2. 如需删除 S3 数据，请手动清空存储桶"
echo "3. CloudWatch 日志组会被删除"
echo "4. SQS 队列会被删除"
echo "5. VPC Flow Logs 配置会被删除"

# 确认删除
if [ "$FORCE_FLAG" != "--force" ]; then
    echo ""
    read -p "❓ 确定要删除这些资源吗? (输入 'yes' 确认): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        echo "❌ 操作已取消"
        exit 0
    fi
fi

echo ""
echo "🚀 开始销毁 Stack..."

# 从现有 Stack 获取部署参数
echo "📋 获取 Stack 参数..."
VPC_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Parameters[?ParameterKey==`VpcId`].ParameterValue' --output text 2>/dev/null || echo "")

# 如果无法从参数获取，尝试从输出获取
if [ -z "$VPC_ID" ] || [ "$VPC_ID" = "None" ]; then
    VPC_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' --output text 2>/dev/null || echo "")
fi

# 如果还是无法获取，使用默认值（CDK destroy 实际上不会使用这个值创建资源）
if [ -z "$VPC_ID" ] || [ "$VPC_ID" = "None" ]; then
    echo "⚠️  无法从 Stack 获取 VPC ID，使用占位符值"
    VPC_ID="vpc-placeholder"
fi

echo "   VPC ID: $VPC_ID"

# 执行销毁（传递必要的上下文参数）
npx cdk destroy "$STACK_NAME" \
    --force \
    -c "vpcId=$VPC_ID" \
    -c "environment=$ENVIRONMENT"

# 在销毁前获取存储桶名称
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Outputs[?OutputKey==`FlowLogsBucketName`].OutputValue' --output text 2>/dev/null || echo "")

echo ""
echo "✅ Stack 销毁完成!"

# 检查 S3 存储桶
echo ""
echo "🔍 检查 S3 存储桶状态..."

if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "None" ]; then
    echo "📦 S3 存储桶 '$BUCKET_NAME' 仍然存在（保护策略）"
    
    # 检查存储桶大小
    BUCKET_SIZE=$(aws s3 ls s3://"$BUCKET_NAME" --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3, $4}' || echo "未知")
    echo "   存储桶大小: $BUCKET_SIZE"
    
    echo ""
    echo "🗂️  如需完全删除存储桶和数据:"
    echo "   1. 清空存储桶: aws s3 rm s3://$BUCKET_NAME --recursive"
    echo "   2. 删除存储桶: aws s3 rb s3://$BUCKET_NAME"
    echo ""
    echo "⚠️  注意: 删除后数据无法恢复!"
else
    echo "✅ 没有发现遗留的 S3 存储桶"
fi

echo ""
echo "🎉 销毁操作完成!"
echo ""
echo "📋 后续清理建议:"
echo "1. 检查是否有其他相关资源需要手动清理"
echo "2. 验证 VPC Flow Logs 配置已被移除"
echo "3. 检查 CloudWatch 中是否还有相关日志组"
echo "4. 如不再需要，删除 S3 存储桶中的历史数据"

# 显示清理命令
echo ""
echo "🛠️  常用清理命令:"
echo "   查看 VPC Flow Logs: aws ec2 describe-flow-logs"
echo "   查看 S3 存储桶: aws s3 ls | grep vpc-flow-logs"
echo "   查看 CloudWatch 日志组: aws logs describe-log-groups --log-group-name-prefix /aws/vpc/flowlogs"