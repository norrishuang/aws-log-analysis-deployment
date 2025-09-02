# OSI 配置文件对比分析

## 文件对比：osi-vpcflowlog.yml vs osi-vpcflowlog-fixed.yml

### 主要差异

#### 1. Grok 模式中的字段名差异

**原始文件 (osi-vpcflowlog.yml):**
```yaml
- "%{NOTSPACE:protocol} ... %{NOTSPACE:tcp_flags} ... %{NOTSPACE:pkt_srcaddr} %{NOTSPACE:pkt_dstaddr} ... %{NOTSPACE:sublocation_type} %{NOTSPACE:sublocation_id} ... %{NOTSPACE:traffic-path}"
```

**修复文件 (osi-vpcflowlog-fixed.yml):**
```yaml
- "%{NOTSPACE:protocol-code} ... %{NOTSPACE:tcp-flags} ... %{NOTSPACE:pkt-srcaddr} %{NOTSPACE:pkt-dstaddr} ... %{NOTSPACE:sublocation-type} %{NOTSPACE:sublocation-id} ... %{NOTSPACE:traffic-path}"
```

**字段名变更：**
- `protocol` → `protocol-code`
- `tcp_flags` → `tcp-flags`
- `pkt_srcaddr` → `pkt-srcaddr`
- `pkt_dstaddr` → `pkt-dstaddr`
- `sublocation_type` → `sublocation-type`
- `sublocation_id` → `sublocation-id`

#### 2. substitute_string 处理的字段差异

**原始文件:**
```yaml
- source: "protocol"
```

**修复文件:**
```yaml
- source: "protocol-code"
```

#### 3. 新增的数据类型转换处理器

**修复文件新增了 convert_entry_type 处理器：**
```yaml
# Convert numeric fields to proper types
- convert_entry_type:
    key: "packets"
    type: "long"
- convert_entry_type:
    key: "bytes"
    type: "long"
- convert_entry_type:
    key: "start"
    type: "long"
- convert_entry_type:
    key: "end"
    type: "long"
```

#### 4. 新增的时间戳处理

**修复文件新增了额外的时间戳转换：**
```yaml
# Create end timestamp
- date:
    destination: "end"
    match:
      - key: "end"
        patterns:
          - "epoch_second"

# Create start timestamp  
- date:
    destination: "start"
    match:
      - key: "start"
        patterns:
          - "epoch_second"
```

### 修复目的分析

#### 1. 字段名标准化
- 使用连字符 (`-`) 而不是下划线 (`_`) 来保持字段名一致性
- 与 Dashboard 配置中的字段名保持一致

#### 2. 数据类型优化
- 明确将数值字段转换为 `long` 类型，避免被自动映射为 `text`
- 确保数值字段可以正确进行数学运算和聚合

#### 3. 时间戳处理增强
- 为 `start` 和 `end` 字段创建正确的日期类型
- 提供更好的时间范围查询支持

### 建议使用场景

**使用 osi-vpcflowlog.yml 当：**
- 需要快速部署，不关心字段类型优化
- 使用自定义 Dashboard 配置

**使用 osi-vpcflowlog-fixed.yml 当：**
- 需要与标准 Dashboard 配置兼容
- 需要正确的数据类型映射
- 需要更好的时间戳处理
- 希望避免字段聚合错误

### 总结

`osi-vpcflowlog-fixed.yml` 是一个更加完善的配置，主要改进了：
1. **字段命名一致性** - 与 Dashboard 期望的字段名匹配
2. **数据类型正确性** - 确保数值和时间字段有正确的类型
3. **更好的兼容性** - 与现有的 Dashboard 和索引模板更好地配合

建议使用 `osi-vpcflowlog-fixed.yml` 来避免字段映射和聚合问题。