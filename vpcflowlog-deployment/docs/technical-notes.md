# 技术说明

## AWS CloudFormation FileFormat 参数

### 问题描述
在配置 VPC Flow Logs 的文件格式时，AWS CloudFormation 的 `AWS::EC2::FlowLog` 资源的 `DestinationOptions.FileFormat` 参数对大小写敏感。

### 参数值要求

| 用户输入 | CloudFormation 值 | 说明 |
|----------|-------------------|------|
| `text` | `Text` | 纯文本格式，gzip 压缩 |
| `parquet` | `Parquet` | Apache Parquet 列式存储格式 |

### 错误示例
```json
// ❌ 错误：小写会导致验证失败
{
  "DestinationOptions": {
    "FileFormat": "text"  // 会报错
  }
}

// ✅ 正确：首字母大写
{
  "DestinationOptions": {
    "FileFormat": "Text"  // 正确
  }
}
```

### 错误信息
```
Model validation failed (#/DestinationOptions/FileFormat: #: only 1 subschema matches out of 2)
#/DestinationOptions/FileFormat: failed validation constraint for keyword [enum]
```

### 代码实现
我们的 CDK 代码自动处理了这个转换：

```typescript
DestinationOptions: {
  FileFormat: fileFormat === 'parquet' ? 'Parquet' : 'Text',
  HiveCompatiblePartitions: true,
  PerHourPartition: enableHourlyPartitions,
}
```

### AWS 文档参考
- [VPC Flow Logs 文档](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-s3.html#flow-logs-s3-path-format)
- [CloudFormation AWS::EC2::FlowLog](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-flowlog.html)

## CDK vs CloudFormation 差异

### CDK 高级构造 vs 原生资源

我们选择使用 CloudFormation 原生资源 (`CfnResource`) 而不是 CDK 高级构造 (`ec2.FlowLog`) 的原因：

1. **功能支持**: CDK 高级构造可能不支持最新的 AWS 功能
2. **参数控制**: 原生资源提供更精确的参数控制
3. **文件格式**: 需要 `DestinationOptions` 来配置文件格式

### 代码对比

#### CDK 高级构造（功能受限）
```typescript
new ec2.FlowLog(this, 'FlowLog', {
  resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
  destination: ec2.FlowLogDestination.toS3(bucket),
  // ❌ 无法配置文件格式
});
```

#### CloudFormation 原生资源（功能完整）
```typescript
new cdk.CfnResource(this, 'FlowLog', {
  type: 'AWS::EC2::FlowLog',
  properties: {
    // ✅ 完整的参数控制
    DestinationOptions: {
      FileFormat: 'Parquet',
      HiveCompatiblePartitions: true,
      PerHourPartition: false,
    }
  }
});
```

## SQS 事件过滤器

### 文件扩展名映射

根据文件格式，SQS 事件通知会监控不同的文件扩展名：

```typescript
const fileExtension = fileFormat === 'parquet' ? '.parquet' : '.gz';

flowLogsBucket.addEventNotification(
  s3.EventType.OBJECT_CREATED_PUT,
  new s3n.SqsDestination(notificationQueue),
  {
    prefix: 'vpc-flow-logs/',
    suffix: fileExtension,  // 动态设置扩展名
  }
);
```

### 文件扩展名说明

| 格式 | 扩展名 | 压缩 | 说明 |
|------|--------|------|------|
| Text | `.gz` | Gzip | 传统文本格式 |
| Parquet | `.parquet` | 内置压缩 | 列式存储格式 |

## 部署参数验证

### 输入验证
```typescript
// 验证文件格式参数
if (fileFormat !== 'text' && fileFormat !== 'parquet') {
  throw new Error('File format must be either "text" or "parquet"');
}
```

### 参数转换
```typescript
// 用户友好的小写输入 -> CloudFormation 要求的大写
const cfnFileFormat = fileFormat === 'parquet' ? 'Parquet' : 'Text';
```

## 最佳实践

### 1. 参数验证
- 在应用程序入口点验证所有参数
- 提供清晰的错误消息
- 使用 TypeScript 类型约束

### 2. 文档同步
- 保持用户文档与实际实现同步
- 说明 AWS API 的特殊要求
- 提供故障排除指南

### 3. 错误处理
- 捕获并解释 CloudFormation 错误
- 提供具体的解决方案
- 记录常见问题和解决方法

### 4. 测试覆盖
- 测试所有支持的参数组合
- 验证 CloudFormation 模板生成
- 确保部署成功

## 版本兼容性

### AWS CDK 版本
- 当前使用: AWS CDK v2
- 最低要求: 2.0.0
- 推荐版本: 最新稳定版

### Node.js 版本
- 最低要求: Node.js 16
- 推荐版本: Node.js 18+
- TypeScript: 4.7+

### AWS CLI 版本
- 最低要求: AWS CLI v2
- 推荐版本: 最新版本
- 区域支持: 所有支持 VPC Flow Logs 的区域