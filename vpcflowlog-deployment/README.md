# VPC Flow Logs CDK 部署

这个 CDK 项目用于部署 VPC Flow Logs 到 S3 存储桶，支持按时间分区存储。

## 功能特性

- ✅ 可配置的 VPC ID
- ✅ S3 存储桶自动创建或使用指定名称
- ✅ 按时间分区存储（Hive 兼容格式）
- ✅ 生命周期管理（IA、Glacier、Deep Archive）
- ✅ 服务器端加密
- ✅ CloudWatch 日志组用于监控
- ✅ 完整的 IAM 权限配置
- ✅ 自定义日志格式包含详细字段

## 前置要求

1. AWS CLI 已配置
2. Node.js 和 npm 已安装
3. AWS CDK CLI 已安装: `npm install -g aws-cdk`
4. 有效的 AWS 凭证和权限

## 安装依赖

```bash
cd vpcflowlog-deployment
npm install
```

## 部署方式

### 方式 1: 使用部署脚本

```bash
# 基本部署（自动生成 bucket 名称）
./deploy.sh vpc-12345678

# 指定 bucket 名称
./deploy.sh vpc-12345678 my-custom-bucket-name

# 指定环境
./deploy.sh vpc-12345678 my-custom-bucket-name prod
```

### 方式 2: 直接使用 CDK 命令

```bash
# 构建项目
npm run build

# 部署（必须指定 VPC ID）
npx cdk deploy -c vpcId=vpc-12345678

# 指定 bucket 名称和环境
npx cdk deploy -c vpcId=vpc-12345678 -c bucketName=my-bucket -c environment=prod
```

### 方式 3: 使用环境变量

```bash
export VPC_ID=vpc-12345678
export BUCKET_NAME=my-flow-logs-bucket
export ENVIRONMENT=prod

npx cdk deploy
```

## 配置参数

| 参数 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| vpcId | ✅ | - | 要启用 Flow Logs 的 VPC ID |
| bucketName | ❌ | 自动生成 | S3 存储桶名称 |
| environment | ❌ | dev | 环境标识 |

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

## 日志格式

包含以下字段：
- version, account-id, interface-id
- srcaddr, dstaddr, srcport, dstport
- protocol, packets, bytes
- windowstart, windowend
- action, flowlogstatus
- vpc-id, subnet-id, instance-id
- tcp-flags, type
- pkt-srcaddr, pkt-dstaddr

## 生命周期管理

- 30 天后转换到 IA (Infrequent Access)
- 90 天后转换到 Glacier
- 365 天后转换到 Deep Archive
- 旧版本在 30 天后删除

## 监控

- CloudWatch 日志组：`/aws/vpc/flowlogs/{environment}`
- 只有被拒绝的流量会记录到 CloudWatch（节省成本）
- 所有流量都会记录到 S3

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
```

## 成本优化建议

1. 根据需要调整日志格式字段
2. 考虑只记录特定类型的流量（ACCEPT/REJECT）
3. 定期审查生命周期策略
4. 监控 S3 存储成本