#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ElbLogsStack } from '../lib/elb-logs-stack';

const app = new cdk.App();

// 从 context 或环境变量获取配置
const loadBalancerArn = app.node.tryGetContext('loadBalancerArn') || process.env.LOAD_BALANCER_ARN;
const bucketName = app.node.tryGetContext('bucketName') || process.env.BUCKET_NAME;
const environment = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';
const enableSqsNotification = app.node.tryGetContext('enableSqsNotification') === 'true' || 
                              process.env.ENABLE_SQS_NOTIFICATION === 'true' || 
                              true;
const sqsQueueName = app.node.tryGetContext('sqsQueueName') || process.env.SQS_QUEUE_NAME;
const logPrefix = app.node.tryGetContext('logPrefix') || process.env.LOG_PREFIX || 'elb-access-logs';

// 验证必需参数
if (!loadBalancerArn) {
  throw new Error('Load Balancer ARN is required. Set via context (-c loadBalancerArn=...) or environment variable LOAD_BALANCER_ARN');
}

// 从 ARN 中提取区域和账户信息
const arnParts = loadBalancerArn.split(':');
if (arnParts.length < 6) {
  throw new Error('Invalid Load Balancer ARN format');
}

const account = arnParts[4];
const region = arnParts[3];

new ElbLogsStack(app, `ElbLogsStack-${environment}`, {
  loadBalancerArn,
  bucketName,
  environment,
  enableSqsNotification,
  sqsQueueName,
  logPrefix,
  env: {
    account: account,
    region: region,
  },
  description: `ELB Access Logs Stack for ${environment} environment`,
  tags: {
    Environment: environment,
    Purpose: 'ELB Access Logs',
    ManagedBy: 'CDK',
  },
});

app.synth();