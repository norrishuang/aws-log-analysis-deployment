# Amazon OpenSearch Ingestion (OSI) 兼容性指南

## 🚨 问题诊断

你遇到的错误表明某些处理器不被 Amazon OpenSearch Ingestion 支持：

```
A processor was found that is not in the list of processors supported by Amazon OpenSearch Ingestion: 
"$['vpclogs-to-opensearch']['processor'][3]"
"$['vpclogs-to-opensearch']['processor'][6]"  
"$['vpclogs-to-opensearch']['processor'][7]"
```

## 🔧 解决方案

### 使用简化配置

我已经创建了两个版本的配置：

1. **`osi-vpcflowlog.yml`** - 修正版（移除了不支持的处理器）
2. **`osi-vpcflowlog-simple.yml`** - 极简版（最大兼容性）

### 推荐使用简化版本

```yaml
# 使用简化版本以确保最大兼容性
cp osi-vpcflowlog-simple.yml osi-vpcflowlog.yml
```

## 📋 OSI 支持的处理器

### ✅ 支持的处理器

| 处理器 | 功能 | 限制 |
|--------|------|------|
| `grok` | 模式匹配和字段提取 | 基础模式支持 |
| `date` | 时间戳解析 | 标准格式 |
| `mutate` | 字段操作 | 仅基础操作 |
| `substitute_string` | 字符串替换 | 简单替换 |
| `delete_entries` | 删除字段 | 基础删除 |
| `drop_events` | 丢弃事件 | 简单条件 |

### ❌ 不支持的功能

| 功能 | 原因 | 替代方案 |
|------|------|----------|
| 复杂的 `mutate` 表达式 | OSI 限制 | 使用基础操作 |
| 条件处理 | 不支持 | 预处理或后处理 |
| 高级计算 | 不支持 | 在 OpenSearch 中计算 |
| 自定义函数 | 不支持 | 使用标准处理器 |
| 复杂模板 | 不支持 | 简化配置 |

## 🔄 配置迁移步骤

### 1. 字段名标准化

**问题**: 字段名包含特殊字符
```yaml
# ❌ 不兼容
aws.vpc.version
aws.vpc.account-id

# ✅ 兼容
aws_vpc_version
aws_vpc_account_id
```

### 2. 简化处理器链

**原始配置** (不兼容):
```yaml
processor:
  - drop_events:
      drop_when: '/message =~ /^version account-id/'  # 复杂条件
  - mutate:
      add_entries:
        - key: "aws.vpc.duration"
          value: '#{aws.vpc.end} - #{aws.vpc.start}'  # 表达式计算
          convert_type: "integer"
  - mutate:
      add_entries:
        - key: "aws.vpc.bytes_per_packet"
          value: '#{aws.vpc.bytes} / #{aws.vpc.packets}'  # 条件表达式
          condition: '#{aws.vpc.packets} != null and #{aws.vpc.packets} > 0'
```

**简化配置** (兼容):
```yaml
processor:
  - grok:
      match:
        message: 
          - "%{NOTSPACE:aws_vpc_version} %{NOTSPACE:aws_vpc_account_id} ..."
  - substitute_string:
      entries:
        - source: "aws_vpc_srcaddr"
          from: "-"
          to: ""
  - date:
      destination: '@timestamp'
      match:
        - key: "aws_vpc_start"
          patterns:
            - "epoch_second"
  - delete_entries:
      with_keys:
        - message
        - s3
```

### 3. 移除复杂功能

**移除的功能**:
- 条件字段计算
- 复杂的数据类型转换
- 高级元数据添加
- 模板配置

**保留的核心功能**:
- 基础字段解析
- 时间戳处理
- 简单字符串替换
- 字段清理

## 🧪 验证配置

使用提供的测试脚本验证配置：

```bash
# 测试简化版配置
python3 test-osi-simple.py

# 验证字段映射
python3 test-osi-config.py
```

## 📊 字段映射对比

### 原始映射 (复杂)
```json
{
  "aws.vpc.version": "5",
  "aws.vpc.account-id": "812046859005",
  "aws.vpc.bytes_per_packet": 150.0,
  "aws.vpc.duration": 77
}
```

### 简化映射 (兼容)
```json
{
  "aws_vpc_version": "5",
  "aws_vpc_account_id": "812046859005",
  "aws_vpc_bytes": "1500",
  "aws_vpc_packets": "10"
}
```

## 🚀 部署建议

### 1. 使用简化配置
```bash
# 部署简化版本
aws osis create-pipeline \
  --pipeline-name "vpc-logs-pipeline" \
  --pipeline-configuration-body file://osi-vpcflowlog-simple.yml \
  --min-units 1 \
  --max-units 4
```

### 2. 后处理增强

在 OpenSearch 中添加计算字段：
```json
{
  "script": {
    "source": """
      if (doc['aws_vpc_bytes'].size() > 0 && doc['aws_vpc_packets'].size() > 0) {
        def bytes = doc['aws_vpc_bytes'].value;
        def packets = doc['aws_vpc_packets'].value;
        if (packets > 0) {
          ctx._source.bytes_per_packet = bytes / packets;
        }
      }
    """
  }
}
```

### 3. 使用 Ingest Pipeline

在 OpenSearch 中创建 ingest pipeline 进行后处理：
```json
{
  "processors": [
    {
      "script": {
        "source": """
          if (ctx.aws_vpc_end != null && ctx.aws_vpc_start != null) {
            ctx.aws_vpc_duration = ctx.aws_vpc_end - ctx.aws_vpc_start;
          }
        """
      }
    },
    {
      "convert": {
        "field": "aws_vpc_srcport",
        "type": "integer",
        "ignore_missing": true
      }
    }
  ]
}
```

## 🔍 故障排除

### 常见错误

1. **处理器不支持**
   ```
   A processor was found that is not in the list of processors supported
   ```
   **解决**: 使用简化配置

2. **字段名错误**
   ```
   Invalid field name containing special characters
   ```
   **解决**: 使用下划线替代点号和连字符

3. **表达式不支持**
   ```
   Expression evaluation not supported
   ```
   **解决**: 移除复杂表达式，使用基础操作

### 调试步骤

1. **验证配置语法**
   ```bash
   aws osis validate-pipeline --pipeline-configuration-body file://config.yml
   ```

2. **检查处理器支持**
   ```bash
   # 查看 OSI 文档中支持的处理器列表
   aws osis describe-pipeline-blueprint --blueprint-name vpc-logs
   ```

3. **测试数据流**
   ```bash
   # 监控管道状态
   aws osis get-pipeline --pipeline-name vpc-logs-pipeline
   ```

## 📚 参考资料

- [Amazon OpenSearch Ingestion 文档](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ingestion.html)
- [支持的处理器列表](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/creating-pipeline.html#pipeline-processors)
- [Data Prepper 处理器参考](https://opensearch.org/docs/latest/data-prepper/pipelines/configuration/processors/)

## 💡 最佳实践

1. **保持简单**: 使用最少的处理器完成任务
2. **避免复杂性**: 将复杂逻辑移到 OpenSearch 端
3. **测试优先**: 在部署前充分测试配置
4. **监控性能**: 关注管道性能和错误率
5. **渐进式增强**: 从基础配置开始，逐步添加功能