import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as iam from "aws-cdk-lib/aws-iam";
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

    userPool.addDomain("Domain", {
      cognitoDomain: {
        domainPrefix: isDev ? `harbor-dev-${cdk.Aws.ACCOUNT_ID}` : `harbor-${cdk.Aws.ACCOUNT_ID}`,
      },
    });

    // ── Lambda: Control Plane (FastAPI + Mangum) ────────

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

    // ── Lambda: Agent Proxy (custom runtime, streaming) ─

    const agentProxyFunction = new lambda.DockerImageFunction(this, "AgentProxyFunction", {
      functionName: "harbor-agent-proxy-stream",
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "lambda/agent-proxy-streaming"),
      ),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 512,
      timeout: cdk.Duration.minutes(5),
      environment: {
        AGENT_RUNTIME_ARN: config.agentRuntimeArn || "",
      },
    });

    agentProxyFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeAgentRuntime"],
        resources: ["*"],
      }),
    );

    // ── REST API (unified, supports streaming) ─────────

    const restApi = new apigw.RestApi(this, "RestApi", {
      restApiName: "harbor-api",
      deployOptions: {
        stageName: "prod",
        throttlingBurstLimit: 100,
        throttlingRateLimit: 50,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
        allowHeaders: ["Content-Type", "Authorization"],
        maxAge: cdk.Duration.hours(1),
      },
    });

    // Control plane: /api/{proxy+} → Lambda (Mangum)
    const apiResource = restApi.root.addResource("api");
    apiResource.addProxy({
      defaultIntegration: new apigw.LambdaIntegration(apiFunction),
      anyMethod: true,
    });

    // Data plane: /stream/agent-proxy → Lambda (streaming, custom runtime)
    // Separate path to avoid conflict with /api/{proxy+}
    const streamResource = restApi.root.addResource("stream");
    const agentProxyResource = streamResource.addResource("agent-proxy");

    // Use CfnMethod to set responseTransferMode: STREAM
    // CDK L2 doesn't expose this yet, so we use escape hatch
    const proxyMethod = agentProxyResource.addMethod(
      "POST",
      new apigw.LambdaIntegration(agentProxyFunction, {
        proxy: true,
      }),
    );

    // Escape hatch: set responseTransferMode to STREAM
    const cfnMethod = proxyMethod.node.defaultChild as apigw.CfnMethod;
    cfnMethod.addPropertyOverride("Integration.TimeoutInMillis", 300000);

    // For streaming, we need to override the integration URI to use
    // response-streaming-invocations instead of /invocations
    const streamingUri = cdk.Fn.join("", [
      "arn:aws:apigateway:",
      this.region,
      ":lambda:path/2021-11-15/functions/",
      agentProxyFunction.functionArn,
      "/response-streaming-invocations",
    ]);
    cfnMethod.addPropertyOverride("Integration.Uri", streamingUri);
    cfnMethod.addPropertyOverride("Integration.ResponseTransferMode", "STREAM");

    // Grant API Gateway permission to invoke with streaming
    agentProxyFunction.addPermission("ApiGwStreamInvoke", {
      principal: new iam.ServicePrincipal("apigateway.amazonaws.com"),
      sourceArn: restApi.arnForExecuteApi("POST", "/stream/agent-proxy", "prod"),
    });

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

    // REST API origin — includes /prod stage prefix
    const apiOrigin = new origins.HttpOrigin(
      `${restApi.restApiId}.execute-api.${this.region}.amazonaws.com`,
      { originPath: "/prod" },
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
        // Control plane: /api/*
        "/api/*": {
          origin: apiOrigin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
        // Data plane (streaming): /stream/*
        "/stream/*": {
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

    eventBus.grantPutEventsTo(apiFunction);
    apiFunction.addEnvironment("EVENT_BUS_NAME", eventBus.eventBusName);

    const alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: "harbor-alerts",
    });

    new events.Rule(this, "LifecycleRule", {
      eventBus,
      eventPattern: { source: ["harbor"], detailType: ["AgentLifecycleChanged"] },
      targets: [new targets.SnsTopic(alertTopic)],
    });

    new events.Rule(this, "PolicyViolationRule", {
      eventBus,
      eventPattern: { source: ["harbor"], detailType: ["PolicyViolation"] },
      targets: [new targets.SnsTopic(alertTopic)],
    });

    // ── Outputs ────────────────────────────────────────

    new cdk.CfnOutput(this, "TableName", { value: table.tableName });
    new cdk.CfnOutput(this, "ApiUrl", { value: restApi.url });
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
