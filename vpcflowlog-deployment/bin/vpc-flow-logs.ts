#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcFlowLogsStack } from '../lib/vpc-flow-logs-stack';

const app = new cdk.App();

// 从 context 或环境变量获取配置
const vpcId = app.node.tryGetContext('vpcId') || process.env.VPC_ID;
const bucketName = app.node.tryGetContext('bucketName') || process.env.BUCKET_NAME;
const environment = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const enableSqsNotification = app.node.tryGetContext('enableSqsNotification') !== 'false';
const sqsQueueName = app.node.tryGetContext('sqsQueueName') || process.env.SQS_QUEUE_NAME;
const enableHourlyPartitions = app.node.tryGetContext('enableHourlyPartitions') === 'true' || process.env.ENABLE_HOURLY_PARTITIONS === 'true';

if (!vpcId) {
  throw new Error('VPC ID is required. Please provide it via context (-c vpcId=vpc-xxx) or environment variable VPC_ID');
}

new VpcFlowLogsStack(app, `VpcFlowLogsStack-${environment}`, {
  vpcId: vpcId,
  bucketName: bucketName,
  environment: environment,
  enableSqsNotification: enableSqsNotification,
  sqsQueueName: sqsQueueName,
  enableHourlyPartitions: enableHourlyPartitions,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});