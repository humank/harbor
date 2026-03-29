import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as apigwv2int from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as apigwv2auth from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as sns from "aws-cdk-lib/aws-sns";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import { Construct } from "constructs";
import { HarborConfig } from "./config";

interface HarborStackProps extends cdk.StackProps {
  config: HarborConfig;
}

export class HarborStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: HarborStackProps) {
    super(scope, id, props);

    const { config } = props;
    const isDev = config.environment === "dev";

    // ── DynamoDB ────────────────────────────────────────

    const table = new dynamodb.Table(this, "AgentRegistryTable", {
      tableName: config.tableName,
      partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      timeToLiveAttribute: "ttl",
      removalPolicy: isDev ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN,
    });

    table.addGlobalSecondaryIndex({
      indexName: "status-index",
      partitionKey: { name: "status", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "updated_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    table.addGlobalSecondaryIndex({
      indexName: "tenant-index",
      partitionKey: { name: "tenant_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "updated_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    table.addGlobalSecondaryIndex({
      indexName: "lifecycle-index",
      partitionKey: { name: "lifecycle_status", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "updated_at", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // ── Cognito ──────────────────────────────────────────

    const userPool = new cognito.UserPool(this, "UserPool", {
      userPoolName: "harbor-users",
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 12,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: isDev ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN,
      customAttributes: {
        tenant_id: new cognito.StringAttribute({ mutable: true }),
        role: new cognito.StringAttribute({ mutable: true }),
      },
    });

    // SPA client (PKCE flow, no secret)
    const spaClient = userPool.addClient("SpaClient", {
      userPoolClientName: "harbor-spa",
      authFlows: { userSrp: true },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        callbackUrls: isDev ? ["http://localhost:5173/callback"] : [],
        logoutUrls: isDev ? ["http://localhost:5173/"] : [],
      },
      preventUserExistenceErrors: true,
      generateSecret: false,
    });

    // M2M client (client credentials for cross-account agents)
    const resourceServer = userPool.addResourceServer("ResourceServer", {
      identifier: "harbor-api",
      scopes: [
        { scopeName: "agents.read", scopeDescription: "Read agents" },
        { scopeName: "agents.write", scopeDescription: "Write agents" },
      ],
    });

    const m2mClient = userPool.addClient("M2mClient", {
      userPoolClientName: "harbor-m2m",
      oAuth: {
        flows: { clientCredentials: true },
        scopes: [
          cognito.OAuthScope.resourceServer(resourceServer, {
            scopeName: "agents.read",
            scopeDescription: "Read agents",
          }),
          cognito.OAuthScope.resourceServer(resourceServer, {
            scopeName: "agents.write",
            scopeDescription: "Write agents",
          }),
        ],
      },
      generateSecret: true,
    });

    // Domain for hosted UI / token endpoint
    userPool.addDomain("Domain", {
      cognitoDomain: {
        domainPrefix: isDev ? `harbor-dev-${cdk.Aws.ACCOUNT_ID}` : `harbor-${cdk.Aws.ACCOUNT_ID}`,
      },
    });

    // ── Lambda ─────────────────────────────────────────

    const apiFunction = new lambda.Function(this, "ApiFunction", {
      functionName: "harbor-api",
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "harbor.main.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../"), {
        bundling: {
          image: lambda.Runtime.PYTHON_3_12.bundlingImage,
          command: [
            "bash", "-c",
            "pip install . -t /asset-output && cp -r src/harbor /asset-output/harbor",
          ],
        },
      }),
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      environment: {
        TABLE_NAME: table.tableName,
        POWERTOOLS_SERVICE_NAME: "harbor",
        COGNITO_USER_POOL_ID: userPool.userPoolId,
        COGNITO_APP_CLIENT_ID: spaClient.userPoolClientId,
        HARBOR_AUTH_DISABLED: isDev ? "true" : "false",
      },
    });

    table.grantReadWriteData(apiFunction);

    // ── API Gateway HTTP API ───────────────────────────

    const httpApi = new apigwv2.HttpApi(this, "HttpApi", {
      apiName: "harbor-api",
      corsPreflight: {
        allowOrigins: ["*"],
        allowMethods: [apigwv2.CorsHttpMethod.ANY],
        allowHeaders: ["Content-Type", "Authorization"],
        maxAge: cdk.Duration.hours(1),
      },
    });

    // JWT authorizer (enabled via config)
    const jwtAuthorizer = config.enableAuth
      ? new apigwv2auth.HttpJwtAuthorizer("JwtAuthorizer", userPool.userPoolProviderUrl, {
          jwtAudience: [spaClient.userPoolClientId, m2mClient.userPoolClientId],
        })
      : undefined;

    const lambdaIntegration = new apigwv2int.HttpLambdaIntegration(
      "LambdaIntegration",
      apiFunction,
    );

    httpApi.addRoutes({
      path: "/api/{proxy+}",
      methods: [apigwv2.HttpMethod.ANY],
      integration: lambdaIntegration,
      authorizer: jwtAuthorizer,
    });

    // Throttling via stage
    const stage = httpApi.defaultStage?.node.defaultChild as apigwv2.CfnStage;
    stage.defaultRouteSettings = {
      throttlingBurstLimit: 100,
      throttlingRateLimit: 50,
    };

    // ── S3 Bucket (Frontend) ───────────────────────────

    const frontendBucket = new s3.Bucket(this, "FrontendBucket", {
      bucketName: isDev ? undefined : "harbor-frontend",
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: isDev ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN,
      autoDeleteObjects: isDev,
    });

    // ── WAF WebACL ─────────────────────────────────────

    const webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
      name: "harbor-waf",
      scope: "CLOUDFRONT",
      defaultAction: { allow: {} },
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: "harbor-waf",
        sampledRequestsEnabled: true,
      },
      rules: [
        {
          name: "AWSManagedRulesCommonRuleSet",
          priority: 1,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesCommonRuleSet",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: "common-rules",
            sampledRequestsEnabled: true,
          },
        },
        {
          name: "RateLimitPerIP",
          priority: 2,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: 1000,
              aggregateKeyType: "IP",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: "rate-limit",
            sampledRequestsEnabled: true,
          },
        },
      ],
    });

    // ── CloudFront Distribution ────────────────────────

    const oac = new cloudfront.S3OriginAccessControl(this, "OAC", {
      originAccessControlName: "harbor-oac",
    });

    const apiOrigin = new origins.HttpOrigin(
      `${httpApi.httpApiId}.execute-api.${this.region}.amazonaws.com`,
    );

    const distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(frontendBucket, {
          originAccessControl: oac,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      additionalBehaviors: {
        "/api/*": {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
      defaultRootObject: "index.html",
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: "/index.html" },
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: "/index.html" },
      ],
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      webAclId: webAcl.attrArn,
    });

    // ── EventBridge + SNS ─────────────────────────────────

    const eventBus = new events.EventBus(this, "EventBus", {
      eventBusName: "harbor-events",
    });

    // Cross-account: allow workload accounts in the org to put events
    if (config.orgId) {
      new events.CfnEventBusPolicy(this, "OrgPutEventsPolicy", {
        eventBusName: eventBus.eventBusName,
        statementId: "AllowOrgPutEvents",
        action: "events:PutEvents",
        principal: "*",
        condition: {
          type: "StringEquals",
          key: "aws:PrincipalOrgID",
          value: config.orgId,
        },
      });
    }

    // Grant Lambda permission to put events
    eventBus.grantPutEventsTo(apiFunction);
    apiFunction.addEnvironment("EVENT_BUS_NAME", eventBus.eventBusName);

    // SNS topic for alerts
    const alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: "harbor-alerts",
    });

    // Rule: lifecycle transitions → SNS
    new events.Rule(this, "LifecycleRule", {
      eventBus,
      eventPattern: {
        source: ["harbor"],
        detailType: ["AgentLifecycleChanged"],
      },
      targets: [new targets.SnsTopic(alertTopic)],
    });

    // Rule: policy violations → SNS
    new events.Rule(this, "PolicyViolationRule", {
      eventBus,
      eventPattern: {
        source: ["harbor"],
        detailType: ["PolicyViolation"],
      },
      targets: [new targets.SnsTopic(alertTopic)],
    });

    // ── Agent Proxy Lambda (streaming to AgentCore Runtime) ──

    const agentProxyFunction = new lambda.Function(this, "AgentProxyFunction", {
      functionName: "harbor-agent-proxy",
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "agent-proxy.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "lambda")),
      memorySize: 256,
      timeout: cdk.Duration.minutes(5),
      environment: {
        AGENT_RUNTIME_ARN: config.agentRuntimeArn || "",
      },
    });

    // Grant permission to invoke AgentCore Runtime
    agentProxyFunction.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeAgentRuntime"],
        resources: ["*"],
      }),
    );

    const proxyIntegration = new apigwv2int.HttpLambdaIntegration(
      "AgentProxyIntegration",
      agentProxyFunction,
    );

    httpApi.addRoutes({
      path: "/api/v1/agent-proxy",
      methods: [apigwv2.HttpMethod.POST],
      integration: proxyIntegration,
    });

    // ── Outputs ────────────────────────────────────────

    new cdk.CfnOutput(this, "TableName", { value: table.tableName });
    new cdk.CfnOutput(this, "ApiUrl", { value: httpApi.apiEndpoint });
    new cdk.CfnOutput(this, "DistributionUrl", {
      value: `https://${distribution.distributionDomainName}`,
    });
    new cdk.CfnOutput(this, "FrontendBucketName", { value: frontendBucket.bucketName });
    new cdk.CfnOutput(this, "UserPoolId", { value: userPool.userPoolId });
    new cdk.CfnOutput(this, "SpaClientId", { value: spaClient.userPoolClientId });
    new cdk.CfnOutput(this, "M2mClientId", { value: m2mClient.userPoolClientId });
    new cdk.CfnOutput(this, "EventBusName", { value: eventBus.eventBusName });
    new cdk.CfnOutput(this, "AlertTopicArn", { value: alertTopic.topicArn });
  }
}
