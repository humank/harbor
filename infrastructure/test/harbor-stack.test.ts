import * as cdk from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { HarborStack } from "../lib/harbor-stack";
import { devConfig } from "../lib/config";

let template: Template;

beforeAll(() => {
  const app = new cdk.App();
  const stack = new HarborStack(app, "TestStack", {
    config: devConfig,
    env: { account: "123456789012", region: "us-east-1" },
  });
  template = Template.fromStack(stack);
});

describe("DynamoDB", () => {
  test("table created with correct key schema", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      KeySchema: [
        { AttributeName: "pk", KeyType: "HASH" },
        { AttributeName: "sk", KeyType: "RANGE" },
      ],
      BillingMode: "PAY_PER_REQUEST",
    });
  });

  test("has 3 GSIs", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      GlobalSecondaryIndexes: Match.arrayWith([
        Match.objectLike({ IndexName: "status-index" }),
        Match.objectLike({ IndexName: "tenant-index" }),
        Match.objectLike({ IndexName: "lifecycle-index" }),
      ]),
    });
  });

  test("PITR enabled", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });
});

describe("Lambda", () => {
  test("function with Python 3.12 ARM64", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Runtime: "python3.12",
      Architectures: ["arm64"],
      MemorySize: 256,
      Timeout: 30,
    });
  });

  test("has DynamoDB and EventBridge env vars", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: Match.objectLike({
          TABLE_NAME: Match.anyValue(),
          EVENT_BUS_NAME: Match.anyValue(),
          COGNITO_USER_POOL_ID: Match.anyValue(),
        }),
      },
    });
  });
});

describe("API Gateway", () => {
  test("HTTP API created", () => {
    template.resourceCountIs("AWS::ApiGatewayV2::Api", 1);
  });

  test("has route", () => {
    template.resourceCountIs("AWS::ApiGatewayV2::Route", 1);
  });
});

describe("Cognito", () => {
  test("user pool created", () => {
    template.resourceCountIs("AWS::Cognito::UserPool", 1);
  });

  test("two app clients (SPA + M2M)", () => {
    template.resourceCountIs("AWS::Cognito::UserPoolClient", 2);
  });

  test("resource server created", () => {
    template.resourceCountIs("AWS::Cognito::UserPoolResourceServer", 1);
  });
});

describe("CloudFront + S3", () => {
  test("S3 bucket with block public access", () => {
    template.hasResourceProperties("AWS::S3::Bucket", {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test("CloudFront distribution created", () => {
    template.resourceCountIs("AWS::CloudFront::Distribution", 1);
  });

  test("OAC created", () => {
    template.resourceCountIs("AWS::CloudFront::OriginAccessControl", 1);
  });
});

describe("WAF", () => {
  test("WebACL with 2 rules", () => {
    template.hasResourceProperties("AWS::WAFv2::WebACL", {
      Rules: Match.arrayWith([
        Match.objectLike({ Name: "AWSManagedRulesCommonRuleSet" }),
        Match.objectLike({ Name: "RateLimitPerIP" }),
      ]),
    });
  });
});

describe("EventBridge + SNS", () => {
  test("event bus created", () => {
    template.resourceCountIs("AWS::Events::EventBus", 1);
  });

  test("2 event rules", () => {
    template.resourceCountIs("AWS::Events::Rule", 2);
  });

  test("SNS topic created", () => {
    template.resourceCountIs("AWS::SNS::Topic", 1);
  });
});

describe("Snapshot", () => {
  test("matches snapshot", () => {
    expect(template.toJSON()).toMatchSnapshot();
  });
});
