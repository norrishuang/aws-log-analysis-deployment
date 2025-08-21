#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcFlowLogsStack } from '../lib/vpc-flow-logs-stack';

const app = new cdk.App();

// 从 context 或环境变量获取配置
const vpcId = app.node.tryGetContext('vpcId') || process.env.VPC_ID;
const bucketName = app.node.tryGetContext('bucketName') || process.env.BUCKET_NAME;
const environment = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'dev';

if (!vpcId) {
  throw new Error('VPC ID is required. Please provide it via context (-c vpcId=vpc-xxx) or environment variable VPC_ID');
}

new VpcFlowLogsStack(app, `VpcFlowLogsStack-${environment}`, {
  vpcId: vpcId,
  bucketName: bucketName,
  environment: environment,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});