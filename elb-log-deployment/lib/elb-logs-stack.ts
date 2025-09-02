import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as cr from 'aws-cdk-lib/custom-resources';

import { Construct } from 'constructs';

export interface ElbLogsStackProps extends cdk.StackProps {
  loadBalancerArn: string;
  bucketName?: string;
  environment: string;
  enableSqsNotification?: boolean;
  sqsQueueName?: string;
  logPrefix?: string;
}

export class ElbLogsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ElbLogsStackProps) {
    super(scope, id, props);

    const {
      loadBalancerArn,
      bucketName,
      environment,
      enableSqsNotification = true,
      sqsQueueName,
      logPrefix = 'elb-access-logs'
    } = props;

    // 导入现有的 Application Load Balancer
    const loadBalancer = elbv2.ApplicationLoadBalancer.fromApplicationLoadBalancerAttributes(
      this, 'ExistingLoadBalancer', {
        loadBalancerArn: loadBalancerArn,
        securityGroupId: '', // 这里可以留空，因为我们只需要启用日志
      }
    );

    // 创建 S3 存储桶用于存储 ELB Access Logs
    const elbLogsBucket = new s3.Bucket(this, 'ElbAccessLogsBucket', {
      bucketName: bucketName || `elb-access-logs-${environment}-${this.account}-${this.region}`,
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

    // 为 ELB 服务添加 S3 存储桶策略
    // ELB 服务需要特定的权限来写入访问日志
    const elbServiceAccountIds: { [region: string]: string } = {
      'us-east-1': '127311923021',
      'us-east-2': '033677994240',
      'us-west-1': '027434742980',
      'us-west-2': '797873946194',
      'eu-west-1': '156460612806',
      'eu-west-2': '652711504416',
      'eu-west-3': '009996457667',
      'eu-central-1': '054676820928',
      'ap-northeast-1': '582318560864',
      'ap-northeast-2': '600734575887',
      'ap-southeast-1': '114774131450',
      'ap-southeast-2': '783225319266',
      'ap-south-1': '718504428378',
      'sa-east-1': '507241528517',
      'ca-central-1': '985666609251',
    };

    const elbServiceAccountId = elbServiceAccountIds[this.region];
    if (!elbServiceAccountId) {
      throw new Error(`ELB service account ID not found for region: ${this.region}`);
    }

    // 添加 S3 存储桶策略以允许 ELB 服务写入日志
    elbLogsBucket.addToResourcePolicy(new iam.PolicyStatement({
      sid: 'AWSLogDeliveryWrite',
      effect: iam.Effect.ALLOW,
      principals: [new iam.AccountPrincipal(elbServiceAccountId)],
      actions: ['s3:PutObject'],
      resources: [`${elbLogsBucket.bucketArn}/${logPrefix}/AWSLogs/${this.account}/*`],
    }));

    elbLogsBucket.addToResourcePolicy(new iam.PolicyStatement({
      sid: 'AWSLogDeliveryAclCheck',
      effect: iam.Effect.ALLOW,
      principals: [new iam.AccountPrincipal(elbServiceAccountId)],
      actions: ['s3:GetBucketAcl'],
      resources: [elbLogsBucket.bucketArn],
    }));

    // 创建 SQS 队列用于接收 S3 事件通知
    let notificationQueue: sqs.Queue | undefined;
    let deadLetterQueue: sqs.Queue | undefined;

    if (enableSqsNotification) {
      // 创建死信队列
      deadLetterQueue = new sqs.Queue(this, 'ElbLogsNotificationDLQ', {
        queueName: `${sqsQueueName || `elb-logs-${environment}`}-dlq`,
        retentionPeriod: cdk.Duration.days(14),
        encryption: sqs.QueueEncryption.SQS_MANAGED,
      });

      // 创建主通知队列
      notificationQueue = new sqs.Queue(this, 'ElbLogsNotificationQueue', {
        queueName: sqsQueueName || `elb-logs-${environment}-notifications`,
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
      elbLogsBucket.addEventNotification(
        s3.EventType.OBJECT_CREATED_PUT,
        new s3n.SqsDestination(notificationQueue),
        {
          prefix: `${logPrefix}/`,
          suffix: '.gz',
        }
      );

      // 也监听其他创建事件（如 multipart upload complete）
      elbLogsBucket.addEventNotification(
        s3.EventType.OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD,
        new s3n.SqsDestination(notificationQueue),
        {
          prefix: `${logPrefix}/`,
          suffix: '.gz',
        }
      );
    }

    // 创建 CloudWatch 日志组（可选，用于监控）
    const logGroup = new logs.LogGroup(this, 'ElbAccessLogsGroup', {
      logGroupName: `/aws/elb/accesslogs/${environment}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // 启用 ELB 访问日志
    // 使用 CloudFormation 自定义资源来启用访问日志
    const enableAccessLogsCustomResource = new cdk.CustomResource(this, 'EnableElbAccessLogs', {
      serviceToken: this.createEnableAccessLogsProvider().serviceToken,
      properties: {
        LoadBalancerArn: loadBalancerArn,
        BucketName: elbLogsBucket.bucketName,
        Prefix: logPrefix,
        Enabled: 'true',
      },
    });

    // 输出重要信息
    new cdk.CfnOutput(this, 'LoadBalancerArn', {
      value: loadBalancerArn,
      description: 'Load Balancer ARN for which access logs are enabled',
    });

    new cdk.CfnOutput(this, 'ElbLogsBucketName', {
      value: elbLogsBucket.bucketName,
      description: 'S3 Bucket name for ELB Access Logs',
    });

    new cdk.CfnOutput(this, 'ElbLogsBucketArn', {
      value: elbLogsBucket.bucketArn,
      description: 'S3 Bucket ARN for ELB Access Logs',
    });

    new cdk.CfnOutput(this, 'LogPrefix', {
      value: logPrefix,
      description: 'S3 prefix for ELB Access Logs',
    });

    new cdk.CfnOutput(this, 'CloudWatchLogGroup', {
      value: logGroup.logGroupName,
      description: 'CloudWatch Log Group for ELB Access Logs monitoring',
    });

    new cdk.CfnOutput(this, 'ElbServiceAccountId', {
      value: elbServiceAccountId,
      description: 'ELB Service Account ID for this region',
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

  private createEnableAccessLogsProvider(): cr.Provider {
    // 创建 Lambda 函数来启用 ELB 访问日志
    const onEventHandler = new lambda.Function(this, 'EnableAccessLogsHandler', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    request_type = event['RequestType']
    properties = event['ResourceProperties']
    
    load_balancer_arn = properties['LoadBalancerArn']
    bucket_name = properties['BucketName']
    prefix = properties['Prefix']
    enabled = properties['Enabled'] == 'true'
    
    elbv2_client = boto3.client('elbv2')
    
    try:
        if request_type in ['Create', 'Update']:
            # 启用访问日志
            response = elbv2_client.modify_load_balancer_attributes(
                LoadBalancerArn=load_balancer_arn,
                Attributes=[
                    {
                        'Key': 'access_logs.s3.enabled',
                        'Value': str(enabled).lower()
                    },
                    {
                        'Key': 'access_logs.s3.bucket',
                        'Value': bucket_name
                    },
                    {
                        'Key': 'access_logs.s3.prefix',
                        'Value': prefix
                    }
                ]
            )
            logger.info(f"Successfully enabled access logs: {response}")
            
        elif request_type == 'Delete':
            # 禁用访问日志
            response = elbv2_client.modify_load_balancer_attributes(
                LoadBalancerArn=load_balancer_arn,
                Attributes=[
                    {
                        'Key': 'access_logs.s3.enabled',
                        'Value': 'false'
                    }
                ]
            )
            logger.info(f"Successfully disabled access logs: {response}")
        
        return {
            'Status': 'SUCCESS',
            'PhysicalResourceId': f"elb-access-logs-{load_balancer_arn.split('/')[-1]}",
            'Data': {
                'LoadBalancerArn': load_balancer_arn,
                'BucketName': bucket_name,
                'Prefix': prefix,
                'Enabled': str(enabled)
            }
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'Status': 'FAILED',
            'Reason': str(e),
            'PhysicalResourceId': f"elb-access-logs-{load_balancer_arn.split('/')[-1]}",
        }
      `),
      timeout: cdk.Duration.minutes(5),
    });

    // 为 Lambda 函数添加必要的权限
    onEventHandler.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'elasticloadbalancing:ModifyLoadBalancerAttributes',
        'elasticloadbalancing:DescribeLoadBalancerAttributes',
      ],
      resources: ['*'],
    }));

    return new cr.Provider(this, 'EnableAccessLogsProvider', {
      onEventHandler: onEventHandler,
    });
  }
}