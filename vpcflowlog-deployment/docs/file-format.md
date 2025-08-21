# VPC Flow Logs 文件格式详解

## 文件基本信息

### 文件命名规则
```
{account-id}_vpcflowlogs_{region}_{flow-log-id}_{end-time}_{hash}.gz
```

**示例**:
```
123456789012_vpcflowlogs_us-east-1_fl-1234abcd_20240115T1005Z_a1b2c3d4.gz
```

**字段说明**:
- `account-id`: AWS 账户 ID
- `region`: AWS 区域
- `flow-log-id`: Flow Log 资源 ID
- `end-time`: 捕获窗口结束时间 (ISO 8601 格式)
- `hash`: 文件唯一标识符

### 文件压缩
- **格式**: gzip 压缩
- **扩展名**: `.gz`
- **压缩比**: 通常 80-90%

## 目录结构

### Hive 兼容分区
```
vpc-flow-logs/
├── year=2024/
│   ├── month=01/
│   │   ├── day=15/
│   │   │   ├── hour=10/
│   │   │   │   ├── 123456789012_vpcflowlogs_us-east-1_fl-1234abcd_20240115T1000Z_hash1.gz
│   │   │   │   ├── 123456789012_vpcflowlogs_us-east-1_fl-1234abcd_20240115T1005Z_hash2.gz
│   │   │   │   └── ...
│   │   │   ├── hour=11/
│   │   │   └── ...
│   │   ├── day=16/
│   │   └── ...
│   ├── month=02/
│   └── ...
├── year=2025/
└── ...
```

## 日志格式

### 字段定义
我们的配置包含以下 21 个字段（按顺序）：

| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 1 | version | int | Flow Log 版本 | 5 |
| 2 | account-id | string | AWS 账户 ID | 123456789012 |
| 3 | interface-id | string | 网络接口 ID | eni-1235b8ca123456789 |
| 4 | srcaddr | string | 源 IP 地址 | 172.31.16.139 |
| 5 | dstaddr | string | 目标 IP 地址 | 172.31.16.21 |
| 6 | srcport | int | 源端口 | 20641 |
| 7 | dstport | int | 目标端口 | 22 |
| 8 | protocol | int | IANA 协议号 | 6 (TCP) |
| 9 | packets | int | 数据包数量 | 20 |
| 10 | bytes | int | 字节数 | 4249 |
| 11 | windowstart | int | 捕获窗口开始时间 (Unix 时间戳) | 1418530010 |
| 12 | windowend | int | 捕获窗口结束时间 (Unix 时间戳) | 1418530070 |
| 13 | action | string | 流量动作 | ACCEPT/REJECT |
| 14 | flowlogstatus | string | Flow Log 状态 | OK/NODATA/SKIPDATA |
| 15 | vpc-id | string | VPC ID | vpc-12345678 |
| 16 | subnet-id | string | 子网 ID | subnet-12345678 |
| 17 | instance-id | string | 实例 ID | i-1234567890abcdef0 |
| 18 | tcp-flags | int | TCP 标志 | 19 |
| 19 | type | string | 流量类型 | IPv4/IPv6 |
| 20 | pkt-srcaddr | string | 数据包源地址 | 172.31.16.139 |
| 21 | pkt-dstaddr | string | 数据包目标地址 | 172.31.16.21 |

### 字段分隔符
- **分隔符**: 单个空格 ` `
- **编码**: UTF-8
- **换行符**: `\n` (Unix 格式)

### 示例记录
```
5 123456789012 eni-1235b8ca123456789 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.16.139 172.31.16.21
5 123456789012 eni-1235b8ca123456789 172.31.9.69 172.31.9.12 49761 3389 6 20 4249 1418530010 1418530070 REJECT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.9.69 172.31.9.12
```

## 特殊值说明

### 协议号 (protocol)
- `1`: ICMP
- `6`: TCP
- `17`: UDP
- `58`: ICMPv6

### 动作 (action)
- `ACCEPT`: 流量被安全组或网络 ACL 允许
- `REJECT`: 流量被安全组或网络 ACL 拒绝

### Flow Log 状态 (flowlogstatus)
- `OK`: 数据正常记录
- `NODATA`: 在捕获窗口内没有网络流量
- `SKIPDATA`: 在捕获窗口内跳过了一些流量记录

### 缺失值
- 当字段值不可用时，显示为 `-`
- 例如：`srcport` 和 `dstport` 对于 ICMP 流量可能显示为 `-`

## 文件大小和频率

### 典型特征
- **文件大小**: 通常 1KB - 50MB (压缩后)
- **生成频率**: 每 5-10 分钟一个文件
- **记录数量**: 每个文件包含数百到数万条记录

### 影响因素
- 网络流量量
- VPC 大小和活跃度
- 捕获窗口设置
- 过滤规则

## 处理建议

### 解压缩
```bash
# 下载并解压文件
aws s3 cp s3://bucket/path/file.gz ./
gunzip file.gz
```

### 解析示例 (Python)
```python
def parse_flow_log_line(line):
    fields = line.strip().split(' ')
    return {
        'version': int(fields[0]),
        'account_id': fields[1],
        'interface_id': fields[2],
        'srcaddr': fields[3],
        'dstaddr': fields[4],
        'srcport': int(fields[5]) if fields[5] != '-' else None,
        'dstport': int(fields[6]) if fields[6] != '-' else None,
        'protocol': int(fields[7]),
        'packets': int(fields[8]),
        'bytes': int(fields[9]),
        'windowstart': int(fields[10]),
        'windowend': int(fields[11]),
        'action': fields[12],
        'flowlogstatus': fields[13],
        'vpc_id': fields[14],
        'subnet_id': fields[15],
        'instance_id': fields[16],
        'tcp_flags': int(fields[17]) if fields[17] != '-' else None,
        'type': fields[18],
        'pkt_srcaddr': fields[19],
        'pkt_dstaddr': fields[20]
    }
```

### Athena 表定义
```sql
CREATE EXTERNAL TABLE vpc_flow_logs (
  version int,
  account_id string,
  interface_id string,
  srcaddr string,
  dstaddr string,
  srcport int,
  dstport int,
  protocol int,
  packets bigint,
  bytes bigint,
  windowstart bigint,
  windowend bigint,
  action string,
  flowlogstatus string,
  vpc_id string,
  subnet_id string,
  instance_id string,
  tcp_flags int,
  type string,
  pkt_srcaddr string,
  pkt_dstaddr string
)
PARTITIONED BY (
  year string,
  month string,
  day string,
  hour string
)
STORED AS TEXTFILE
LOCATION 's3://your-bucket/vpc-flow-logs/'
TBLPROPERTIES (
  'skip.header.line.count'='0',
  'field.delim'=' '
);
```

## 成本优化

### 存储类别转换
我们的配置自动管理生命周期：
- **30 天**: 转换到 IA (Infrequent Access)
- **90 天**: 转换到 Glacier
- **365 天**: 转换到 Deep Archive

### 查询优化
- 使用分区字段进行过滤
- 限制查询的时间范围
- 使用列式存储格式 (如 Parquet) 进行长期存储