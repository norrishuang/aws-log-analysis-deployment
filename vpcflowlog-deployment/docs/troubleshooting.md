# 故障排除指南

## 常见部署错误

### 1. TypeScript 编译错误

#### 错误: `Property 'WINDOW_START' does not exist on type 'typeof LogFormat'`

**原因**: CDK 版本不同，LogFormat 字段名称可能有变化。

**解决方案**: 
我们已经使用自定义日志格式字符串来避免这个问题：
```typescript
logFormat: [
  ec2.LogFormat.custom([
    '${version}',
    '${account-id}',
    // ... 其他字段
  ].join(' '))
]
```

#### 错误: `Cannot find module 'aws-cdk-lib'`

**原因**: CDK 依赖未安装。

**解决方案**:
```bash
cd vpcflowlog-deployment
npm install
```

### 2. AWS 权限错误

#### 错误: `User is not authorized to perform: ec2:CreateFlowLogs`

**原因**: IAM 用户/角色缺少必要权限。

**解决方案**: 确保 IAM 用户/角色有以下权限：
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateFlowLogs",
        "ec2:DescribeFlowLogs",
        "ec2:DescribeVpcs",
        "s3:CreateBucket",
        "s3:PutBucketPolicy",
        "s3:PutBucketNotification",
        "sqs:CreateQueue",
        "sqs:SetQueueAttributes",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 错误: `VPC vpc-12345678 does not exist`

**原因**: VPC ID 不存在或不在当前区域。

**解决方案**:
1. 验证 VPC ID: `aws ec2 describe-vpcs --vpc-ids vpc-12345678`
2. 检查当前区域: `aws configure get region`
3. 切换到正确区域: `aws configure set region us-east-1`

### 3. S3 相关错误

#### 错误: `Bucket name already exists`

**原因**: S3 存储桶名称必须全局唯一。

**解决方案**:
1. 使用自定义存储桶名称:
   ```bash
   ./deploy.sh vpc-12345678 my-unique-bucket-name-$(date +%s)
   ```
2. 或让系统自动生成唯一名称（默认行为）

#### 错误: `Access Denied when calling PutBucketNotification`

**原因**: 缺少 S3 通知配置权限。

**解决方案**: 确保有 `s3:PutBucketNotification` 权限。

### 4. SQS 相关错误

#### 错误: `Queue name must be unique within the region`

**原因**: SQS 队列名称在区域内重复。

**解决方案**:
```bash
./deploy.sh vpc-12345678 "" dev "my-unique-queue-$(date +%s)"
```

### 5. CDK 部署错误

#### 错误: `This stack uses assets, so the toolkit stack must be deployed`

**原因**: CDK Bootstrap 未执行。

**解决方案**:
```bash
npx cdk bootstrap
```

#### 错误: `Stack VpcFlowLogsStack-dev already exists`

**原因**: Stack 已存在。

**解决方案**:
1. 更新现有 Stack: `npx cdk deploy`
2. 或删除后重新部署: `npx cdk destroy && npx cdk deploy`

#### 错误: `No stacks match the name(s) prod,vpcflow-sqs-1,true`

**原因**: 部署脚本参数传递错误，CDK 把参数当作了 stack 名称。

**解决方案**:
1. 使用修复后的部署脚本
2. 或直接使用 CDK 命令:
   ```bash
   npx cdk deploy -c "vpcId=vpc-12345678" -c "environment=prod"
   ```
3. 使用快速部署脚本:
   ```bash
   ./quick-deploy.sh vpc-12345678
   ```

### 6. 网络连接错误

#### 错误: `Could not connect to the endpoint URL`

**原因**: 网络连接问题或区域配置错误。

**解决方案**:
1. 检查网络连接
2. 验证 AWS 区域配置
3. 检查代理设置

## 验证步骤

### 1. 验证部署状态

```bash
# 检查 CloudFormation Stack
aws cloudformation describe-stacks --stack-name VpcFlowLogsStack-dev

# 检查 Flow Logs
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-12345678"

# 检查 S3 存储桶
aws s3 ls | grep vpc-flow-logs

# 检查 SQS 队列
aws sqs list-queues | grep vpc-flow-logs
```

### 2. 验证 Flow Logs 数据

```bash
# 等待几分钟后检查 S3 中的文件
aws s3 ls s3://your-bucket-name/vpc-flow-logs/ --recursive

# 下载并查看文件内容
aws s3 cp s3://your-bucket-name/vpc-flow-logs/year=2024/month=01/day=15/hour=10/file.gz ./
gunzip file.gz
head -5 file
```

### 3. 验证 SQS 通知

```bash
# 检查 SQS 消息
aws sqs receive-message --queue-url https://sqs.region.amazonaws.com/account/queue-name

# 检查队列属性
aws sqs get-queue-attributes --queue-url https://sqs.region.amazonaws.com/account/queue-name --attribute-names All
```

## 性能优化

### 1. 减少日志字段

如果不需要所有字段，可以修改 `lib/vpc-flow-logs-stack.ts` 中的 `logFormat`：

```typescript
// 最小化字段集
logFormat: [
  ec2.LogFormat.custom([
    '${version}',
    '${srcaddr}',
    '${dstaddr}',
    '${srcport}',
    '${dstport}',
    '${protocol}',
    '${action}',
    '${start}',
    '${end}'
  ].join(' '))
]
```

### 2. 调整流量类型

```typescript
// 只记录被拒绝的流量
trafficType: ec2.FlowLogTrafficType.REJECT,

// 只记录被接受的流量
trafficType: ec2.FlowLogTrafficType.ACCEPT,
```

### 3. 优化 S3 生命周期

根据需求调整生命周期规则：

```typescript
lifecycleRules: [
  {
    id: 'QuickArchive',
    enabled: true,
    transitions: [
      {
        storageClass: s3.StorageClass.INFREQUENT_ACCESS,
        transitionAfter: cdk.Duration.days(7), // 更快转换
      },
    ],
  },
]
```

## 成本控制

### 1. 监控成本

- 使用 AWS Cost Explorer 监控 S3 存储成本
- 设置 CloudWatch 计费告警
- 定期审查 Flow Logs 数据量

### 2. 数据保留策略

```typescript
// 设置数据过期删除
lifecycleRules: [
  {
    id: 'DeleteOldData',
    enabled: true,
    expiration: cdk.Duration.days(90), // 90天后删除
  },
]
```

## 联系支持

如果遇到无法解决的问题：

1. 检查 AWS CloudTrail 日志
2. 查看 CloudFormation 事件
3. 联系 AWS 技术支持
4. 在项目 GitHub 仓库提交 Issue