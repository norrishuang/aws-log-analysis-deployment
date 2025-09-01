# VPC Flow Logs 文件格式详解

## 文件格式选项

### 支持的格式
VPC Flow Logs 支持两种输出格式：

#### 1. Text 格式 (默认)
- **格式**: 纯文本，字段用空格分隔
- **压缩**: Gzip 压缩
- **扩展名**: `.gz`
- **优势**: 简单易读，兼容性好
- **适用场景**: 小规模数据，临时分析

#### 2. Parquet 格式 (推荐)
- **格式**: Apache Parquet 列式存储
- **压缩**: Gzip 压缩
- **扩展名**: `.parquet`
- **优势**: 
  - 查询速度比文本格式快 10-100 倍
  - 存储空间节省 20%
  - 更好的压缩率和查询性能
- **适用场景**: 大规模数据分析，长期存储

### 格式选择建议
- **小于 100KB 的数据**: 使用 Text 格式
- **大于 100KB 的数据**: 使用 Parquet 格式
- **频繁查询**: 强烈推荐 Parquet 格式
- **长期存储**: 推荐 Parquet 格式

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
- **Text 格式**: gzip 压缩，扩展名 `.gz`
- **Parquet 格式**: gzip 压缩，扩展名 `.parquet`
- **压缩比**: 通常 80-90% (Text)，85-95% (Parquet)

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
我们的配置包含所有可用的 30 个字段（按顺序）：

#### 基础字段 (1-14)
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
| 11 | start | int | 捕获窗口开始时间 (Unix 时间戳) | 1418530010 |
| 12 | end | int | 捕获窗口结束时间 (Unix 时间戳) | 1418530070 |
| 13 | action | string | 流量动作 | ACCEPT/REJECT |
| 14 | log-status | string | Flow Log 状态 | OK/NODATA/SKIPDATA |

#### VPC 和实例字段 (15-17)
| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 15 | vpc-id | string | VPC ID | vpc-12345678 |
| 16 | subnet-id | string | 子网 ID | subnet-12345678 |
| 17 | instance-id | string | 实例 ID | i-1234567890abcdef0 |

#### 网络详细信息字段 (18-21)
| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 18 | tcp-flags | int | TCP 标志 | 19 |
| 19 | type | string | 流量类型 | IPv4/IPv6 |
| 20 | pkt-srcaddr | string | 数据包源地址 | 172.31.16.139 |
| 21 | pkt-dstaddr | string | 数据包目标地址 | 172.31.16.21 |

#### 区域和位置字段 (22-25)
| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 22 | region | string | AWS 区域 | us-east-1 |
| 23 | az-id | string | 可用区 ID | use1-az1 |
| 24 | sublocation-type | string | 子位置类型 | wavelength/localzone/outpost |
| 25 | sublocation-id | string | 子位置 ID | wl-bos-wlz-1 |

#### AWS 服务字段 (26-27)
| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 26 | pkt-src-aws-service | string | 源 AWS 服务 | AMAZON/S3/EC2/DYNAMODB |
| 27 | pkt-dst-aws-service | string | 目标 AWS 服务 | AMAZON/S3/EC2/DYNAMODB |

#### 流量路径字段 (28-29)
| 序号 | 字段名 | 类型 | 描述 | 示例值 |
|------|--------|------|------|--------|
| 28 | flow-direction | string | 流方向 | ingress/egress |
| 29 | traffic-path | int | 流量路径 | 1-8 (详见下表) |

### 字段分隔符
- **分隔符**: 单个空格 ` `
- **编码**: UTF-8
- **换行符**: `\n` (Unix 格式)

### 示例记录
```
5 123456789012 eni-1235b8ca123456789 172.31.16.139 172.31.16.21 20641 22 6 20 4249 1418530010 1418530070 ACCEPT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.16.139 172.31.16.21 us-east-1 use1-az1 - - - - ingress 1
5 123456789012 eni-1235b8ca123456789 172.31.9.69 172.31.9.12 49761 3389 6 20 4249 1418530010 1418530070 REJECT OK vpc-12345678 subnet-12345678 i-1234567890abcdef0 19 IPv4 172.31.9.69 172.31.9.12 us-east-1 use1-az1 - - AMAZON S3 egress 2
```

**说明**:
- 第一条记录：VPC 内部通信，新增字段大多为 `-`
- 第二条记录：访问 S3 服务，显示了 AWS 服务标识符和流量路径

## 特殊值说明

### 协议号 (protocol)
- `1`: ICMP
- `6`: TCP
- `17`: UDP
- `58`: ICMPv6

### 动作 (action)
- `ACCEPT`: 流量被安全组或网络 ACL 允许
- `REJECT`: 流量被安全组或网络 ACL 拒绝

### Flow Log 状态 (log-status)
- `OK`: 数据正常记录
- `NODATA`: 在捕获窗口内没有网络流量
- `SKIPDATA`: 在捕获窗口内跳过了一些流量记录

### 流方向 (flow-direction)
- `ingress`: 入站流量
- `egress`: 出站流量

### 流量路径 (traffic-path)
| 值 | 描述 |
|----|------|
| 1 | 通过同一 VPC 内的另一个资源 |
| 2 | 通过 Internet Gateway 或 Gateway VPC Endpoint |
| 3 | 通过 Virtual Private Gateway |
| 4 | 通过 Intra-region VPC Peering |
| 5 | 通过 Inter-region VPC Peering |
| 6 | 通过 Local Gateway |
| 7 | 通过 Gateway Load Balancer Endpoint |
| 8 | 通过 Internet Gateway (IPv6) |

### AWS 服务标识符
常见的 AWS 服务标识符：
- `AMAZON`: Amazon 服务
- `S3`: Amazon S3
- `EC2`: Amazon EC2
- `DYNAMODB`: Amazon DynamoDB
- `CLOUDFRONT`: Amazon CloudFront
- `API_GATEWAY`: Amazon API Gateway
- `LAMBDA`: AWS Lambda

### 子位置类型 (sublocation-type)
- `wavelength`: AWS Wavelength
- `localzone`: AWS Local Zones
- `outpost`: AWS Outposts

### 缺失值
- 当字段值不可用时，显示为 `-`
- 例如：`srcport` 和 `dstport` 对于 ICMP 流量可能显示为 `-`
- 新增字段在某些情况下可能不适用，也会显示为 `-`

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
- **推荐使用 Parquet 格式**:
  - 查询速度提升 10-100 倍
  - 存储成本降低 20%
  - 更好的压缩和查询性能

### Parquet 格式的 Athena 表定义
```sql
CREATE EXTERNAL TABLE vpc_flow_logs_parquet (
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
STORED AS PARQUET
LOCATION 's3://your-bucket/vpc-flow-logs/'
TBLPROPERTIES (
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2020,2030',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.month.digits'='2',
  'projection.day.type'='integer',
  'projection.day.range'='1,31',
  'projection.day.digits'='2',
  'projection.hour.type'='integer',
  'projection.hour.range'='0,23',
  'projection.hour.digits'='2',
  'storage.location.template'='s3://your-bucket/vpc-flow-logs/year=${year}/month=${month}/day=${day}/hour=${hour}/'
);
```