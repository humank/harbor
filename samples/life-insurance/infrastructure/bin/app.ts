#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { InsuranceDemoStack } from "../lib/insurance-demo-stack";
import { devConfig } from "../lib/config";

const app = new cdk.App();

new InsuranceDemoStack(app, "InsuranceDemoStack", {
  config: devConfig,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || "us-west-2",
  },
});
