import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';

import { Construct } from 'constructs';

export interface VpcFlowLogsStackProps extends cdk.StackProps {
  vpcId: string;
  bucketName?: string;
  environment: string;
  enableSqsNotification?: boolean;
  sqsQueueName?: string;
  enableHourlyPartitions?: boolean;
}

export class VpcFlowLogsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: VpcFlowLogsStackProps) {
    super(scope, id, props);

    const {
      vpcId,
      bucketName,
      environment,
      enableSqsNotification = true,
      sqsQueueName,
      enableHourlyPartitions = false
    } = props;

    // 导入现有的 VPC
    const vpc = ec2.Vpc.fromLookup(this, 'ExistingVpc', {
      vpcId: vpcId,
    });

    // 创建 S3 存储桶用于存储 VPC Flow Logs
    const flowLogsBucket = new s3.Bucket(this, 'VpcFlowLogsBucket', {
      bucketName: bucketName || `vpc-flow-logs-${environment}-${this.account}-${this.region}`,
      // 启用版本控制
      versioned: true,
      // 设置生命周期规则
      lifecycleRules: [
        {
          id: 'DeleteOldVersions',
          enabled: true,
          noncurrentVersionExpiration: cdk.Duration.days(30),
        },
        {
          id: 'TransitionToIA',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
            {
              storageClass: s3.StorageClass.DEEP_ARCHIVE,
              transitionAfter: cdk.Duration.days(365),
            },
          ],
        },
      ],
      // 阻止公共访问
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      // 启用服务器端加密
      encryption: s3.BucketEncryption.S3_MANAGED,
      // 删除保护
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // 使用默认文件扩展名
    const fileExtension = '.gz';

    // 创建 SQS 队列用于接收 S3 事件通知
    let notificationQueue: sqs.Queue | undefined;
    let deadLetterQueue: sqs.Queue | undefined;

    if (enableSqsNotification) {
      // 创建死信队列
      deadLetterQueue = new sqs.Queue(this, 'FlowLogsNotificationDLQ', {
        queueName: `${sqsQueueName || `vpc-flow-logs-${environment}`}-dlq`,
        retentionPeriod: cdk.Duration.days(14),
        encryption: sqs.QueueEncryption.SQS_MANAGED,
      });

      // 创建主通知队列
      notificationQueue = new sqs.Queue(this, 'FlowLogsNotificationQueue', {
        queueName: sqsQueueName || `vpc-flow-logs-${environment}-notifications`,
        // 设置可见性超时
        visibilityTimeout: cdk.Duration.minutes(5),
        // 设置消息保留期
        retentionPeriod: cdk.Duration.days(14),
        // 启用加密
        encryption: sqs.QueueEncryption.SQS_MANAGED,
        // 配置死信队列
        deadLetterQueue: {
          queue: deadLetterQueue,
          maxReceiveCount: 3,
        },
      });

      // 添加 S3 事件通知到 SQS
      flowLogsBucket.addEventNotification(
        s3.EventType.OBJECT_CREATED_PUT,
        new s3n.SqsDestination(notificationQueue),
        {
          prefix: 'vpc-flow-logs/',
          suffix: fileExtension,
        }
      );

      // 也监听其他创建事件（如 multipart upload complete）
      flowLogsBucket.addEventNotification(
        s3.EventType.OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD,
        new s3n.SqsDestination(notificationQueue),
        {
          prefix: 'vpc-flow-logs/',
          suffix: fileExtension,
        }
      );
    }

    // 创建 IAM 角色用于 VPC Flow Logs 服务
    const flowLogsRole = new iam.Role(this, 'VpcFlowLogsRole', {
      assumedBy: new iam.ServicePrincipal('vpc-flow-logs.amazonaws.com'),
      description: 'Role for VPC Flow Logs to write to S3',
    });

    // 为 Flow Logs 角色添加 S3 权限
    flowLogsBucket.grantWrite(flowLogsRole);

    // 添加额外的权限以支持分区
    flowLogsRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetBucketLocation',
        's3:ListBucket',
      ],
      resources: [flowLogsBucket.bucketArn],
    }));

    // 创建 CloudWatch 日志组（可选，用于监控）
    const logGroup = new logs.LogGroup(this, 'VpcFlowLogsGroup', {
      logGroupName: `/aws/vpc/flowlogs/${environment}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // 创建 VPC Flow Logs 到 S3
    // 使用 CloudFormation 原生资源来确保正确的文件格式配置
    const flowLogsToS3 = new cdk.CfnResource(this, 'VpcFlowLogsToS3', {
      type: 'AWS::EC2::FlowLog',
      properties: {
        ResourceType: 'VPC',
        ResourceId: vpc.vpcId,
        TrafficType: 'ALL',
        LogDestinationType: 's3',
        LogDestination: `${flowLogsBucket.bucketArn}/vpc-flow-logs/`,
        LogFormat: [
          // 基础字段
          '${version}',           // Flow Log 版本
          '${account-id}',        // AWS 账户 ID
          '${interface-id}',      // 网络接口 ID
          '${srcaddr}',           // 源 IP 地址
          '${dstaddr}',           // 目标 IP 地址
          '${srcport}',           // 源端口
          '${dstport}',           // 目标端口
          '${protocol}',          // IANA 协议号
          '${packets}',           // 数据包数量
          '${bytes}',             // 字节数
          '${start}',             // 捕获窗口开始时间
          '${end}',               // 捕获窗口结束时间
          '${action}',            // 动作 (ACCEPT/REJECT)
          '${log-status}',        // Flow Log 状态

          // VPC 相关字段
          '${vpc-id}',            // VPC ID
          '${subnet-id}',         // 子网 ID
          '${instance-id}',       // 实例 ID

          // 网络详细信息
          '${tcp-flags}',         // TCP 标志
          '${type}',              // 流量类型 (IPv4/IPv6)
          '${pkt-srcaddr}',       // 数据包源地址
          '${pkt-dstaddr}',       // 数据包目标地址

          // 区域和可用区信息
          '${region}',            // AWS 区域
          '${az-id}',             // 可用区 ID

          // 流量路径信息
          '${sublocation-type}',  // 子位置类型
          '${sublocation-id}',    // 子位置 ID

          // 数据包采样信息
          '${pkt-src-aws-service}',  // 源 AWS 服务
          '${pkt-dst-aws-service}',  // 目标 AWS 服务

          // 流方向
          '${flow-direction}',    // 流方向 (ingress/egress)

          // 流量类别
          '${traffic-path}',      // 流量路径
        ].join(' '),
        // 分区配置 - 使用正确的 FileFormat 值
        DestinationOptions: {
          FileFormat: 'plain-text',
          HiveCompatiblePartitions: true,
          PerHourPartition: enableHourlyPartitions,
        },
        Tags: [
          {
            Key: 'Environment',
            Value: environment,
          },
          {
            Key: 'Purpose',
            Value: 'VPC Flow Logs',
          },
        ],
      },
    });

    // 创建 VPC Flow Logs 到 CloudWatch（可选，用于实时监控）
    const flowLogsToCloudWatch = new ec2.FlowLog(this, 'VpcFlowLogsToCloudWatch', {
      resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
      destination: ec2.FlowLogDestination.toCloudWatchLogs(logGroup, flowLogsRole),
      trafficType: ec2.FlowLogTrafficType.REJECT, // 只记录被拒绝的流量到 CloudWatch
    });

    // 输出重要信息
    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'VPC ID for which Flow Logs are enabled',
    });

    new cdk.CfnOutput(this, 'FlowLogsBucketName', {
      value: flowLogsBucket.bucketName,
      description: 'S3 Bucket name for VPC Flow Logs',
    });

    new cdk.CfnOutput(this, 'FlowLogsBucketArn', {
      value: flowLogsBucket.bucketArn,
      description: 'S3 Bucket ARN for VPC Flow Logs',
    });

    new cdk.CfnOutput(this, 'FlowLogsRoleArn', {
      value: flowLogsRole.roleArn,
      description: 'IAM Role ARN for VPC Flow Logs',
    });

    new cdk.CfnOutput(this, 'CloudWatchLogGroup', {
      value: logGroup.logGroupName,
      description: 'CloudWatch Log Group for VPC Flow Logs monitoring',
    });

    new cdk.CfnOutput(this, 'S3FlowLogId', {
      value: flowLogsToS3.ref,
      description: 'Flow Log ID for S3 destination',
    });

    new cdk.CfnOutput(this, 'FileFormat', {
      value: 'plain-text',
      description: 'VPC Flow Logs file format (CloudFormation: plain-text)',
    });

    new cdk.CfnOutput(this, 'HourlyPartitions', {
      value: enableHourlyPartitions.toString(),
      description: 'Whether hourly partitions are enabled',
    });

    new cdk.CfnOutput(this, 'MonitoredFileExtension', {
      value: fileExtension,
      description: 'File extension being monitored by SQS notifications',
    });

    new cdk.CfnOutput(this, 'CloudWatchFlowLogId', {
      value: flowLogsToCloudWatch.flowLogId,
      description: 'Flow Log ID for CloudWatch destination',
    });

    // SQS 相关输出
    if (enableSqsNotification && notificationQueue) {
      new cdk.CfnOutput(this, 'NotificationQueueUrl', {
        value: notificationQueue.queueUrl,
        description: 'SQS Queue URL for S3 event notifications',
      });

      new cdk.CfnOutput(this, 'NotificationQueueArn', {
        value: notificationQueue.queueArn,
        description: 'SQS Queue ARN for S3 event notifications',
      });

      new cdk.CfnOutput(this, 'NotificationQueueName', {
        value: notificationQueue.queueName,
        description: 'SQS Queue Name for S3 event notifications',
      });

      if (deadLetterQueue) {
        new cdk.CfnOutput(this, 'DeadLetterQueueUrl', {
          value: deadLetterQueue.queueUrl,
          description: 'Dead Letter Queue URL for failed notifications',
        });

        new cdk.CfnOutput(this, 'DeadLetterQueueArn', {
          value: deadLetterQueue.queueArn,
          description: 'Dead Letter Queue ARN for failed notifications',
        });
      }
    }
  }
}