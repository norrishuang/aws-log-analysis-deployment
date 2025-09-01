# VPC Flow Logs 字段对照表

## 完整字段列表 (30个字段)

本文档提供了完整的 VPC Flow Logs 字段对照表，包括字段名称、CDK 配置名称和 Athena 表字段名称。

### 基础字段 (1-14)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 1 | `${version}` | version | int | Flow Log 版本 | 5 |
| 2 | `${account-id}` | account_id | string | AWS 账户 ID | 123456789012 |
| 3 | `${interface-id}` | interface_id | string | 网络接口 ID | eni-1235b8ca123456789 |
| 4 | `${srcaddr}` | srcaddr | string | 源 IP 地址 | 172.31.16.139 |
| 5 | `${dstaddr}` | dstaddr | string | 目标 IP 地址 | 172.31.16.21 |
| 6 | `${srcport}` | srcport | int | 源端口 | 20641 |
| 7 | `${dstport}` | dstport | int | 目标端口 | 22 |
| 8 | `${protocol}` | protocol | int | IANA 协议号 | 6 |
| 9 | `${packets}` | packets | bigint | 数据包数量 | 20 |
| 10 | `${bytes}` | bytes | bigint | 字节数 | 4249 |
| 11 | `${start}` | start_time | bigint | 捕获窗口开始时间 | 1418530010 |
| 12 | `${end}` | end_time | bigint | 捕获窗口结束时间 | 1418530070 |
| 13 | `${action}` | action | string | 流量动作 | ACCEPT |
| 14 | `${log-status}` | log_status | string | Flow Log 状态 | OK |

### VPC 和实例字段 (15-17)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 15 | `${vpc-id}` | vpc_id | string | VPC ID | vpc-12345678 |
| 16 | `${subnet-id}` | subnet_id | string | 子网 ID | subnet-12345678 |
| 17 | `${instance-id}` | instance_id | string | 实例 ID | i-1234567890abcdef0 |

### 网络详细信息字段 (18-21)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 18 | `${tcp-flags}` | tcp_flags | int | TCP 标志 | 19 |
| 19 | `${type}` | type | string | 流量类型 | IPv4 |
| 20 | `${pkt-srcaddr}` | pkt_srcaddr | string | 数据包源地址 | 172.31.16.139 |
| 21 | `${pkt-dstaddr}` | pkt_dstaddr | string | 数据包目标地址 | 172.31.16.21 |

### 区域和位置字段 (22-25)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 22 | `${region}` | region | string | AWS 区域 | us-east-1 |
| 23 | `${az-id}` | az_id | string | 可用区 ID | use1-az1 |
| 24 | `${sublocation-type}` | sublocation_type | string | 子位置类型 | wavelength |
| 25 | `${sublocation-id}` | sublocation_id | string | 子位置 ID | wl-bos-wlz-1 |

### AWS 服务字段 (26-27)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 26 | `${pkt-src-aws-service}` | pkt_src_aws_service | string | 源 AWS 服务 | AMAZON |
| 27 | `${pkt-dst-aws-service}` | pkt_dst_aws_service | string | 目标 AWS 服务 | S3 |

### 流量路径字段 (28-29)

| 序号 | CDK 字段名 | Athena 字段名 | 类型 | 描述 | 示例值 |
|------|------------|---------------|------|------|--------|
| 28 | `${flow-direction}` | flow_direction | string | 流方向 | ingress |
| 29 | `${traffic-path}` | traffic_path | int | 流量路径 | 1 |

## 字段变更说明

### 与传统格式的差异

1. **时间字段名称变更**:
   - 旧: `windowstart` / `windowend`
   - 新: `start` / `end`

2. **状态字段名称变更**:
   - 旧: `flowlogstatus`
   - 新: `log-status`

3. **新增字段 (22-29)**:
   - 区域和位置信息 (4个字段)
   - AWS 服务标识 (2个字段)
   - 流量路径信息 (2个字段)

### 向后兼容性

- 前 21 个字段与传统格式基本兼容
- 新增的 9 个字段提供更丰富的网络分析能力
- 所有字段都支持 `-` 作为缺失值

## 使用建议

### 查询优化

1. **使用分区字段**:
   ```sql
   WHERE year='2024' AND month='01' AND day='15'
   ```

2. **过滤非空字段**:
   ```sql
   WHERE pkt_src_aws_service != '-'
   ```

3. **利用新字段进行分析**:
   ```sql
   GROUP BY region, flow_direction, traffic_path
   ```

### 存储优化

1. **选择性字段**: 如果不需要所有字段，可以修改 CDK 配置
2. **压缩格式**: 考虑转换为 Parquet 格式以提高查询性能
3. **分区策略**: 根据查询模式优化分区设计

## 参考资料

- [AWS VPC Flow Logs 官方文档](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html#flow-logs-fields)
- [Amazon Athena 最佳实践](https://docs.aws.amazon.com/athena/latest/ug/best-practices.html)
- [VPC Flow Logs 分析指南](https://aws.amazon.com/blogs/networking-and-content-delivery/analyzing-vpc-flow-logs-with-amazon-kinesis-data-analytics/)