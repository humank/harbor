#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { HarborStack } from "../lib/harbor-stack";
import { devConfig } from "../lib/config";

const app = new cdk.App();

new HarborStack(app, "HarborStack", {
  config: devConfig,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
  tags: {
    Project: "Harbor",
    Environment: devConfig.environment,
  },
});
