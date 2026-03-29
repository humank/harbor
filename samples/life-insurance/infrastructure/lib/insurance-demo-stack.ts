import * as cdk from "aws-cdk-lib";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import { AGENTS, DemoConfig } from "./config";
import { AgentRuntime } from "./constructs/agent-runtime";

interface InsuranceDemoStackProps extends cdk.StackProps {
  config: DemoConfig;
}

export class InsuranceDemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: InsuranceDemoStackProps) {
    super(scope, id, props);

    // Import existing ECR repo (created before CDK deploy so images exist)
    const repo = ecr.Repository.fromRepositoryName(
      this, "AgentRepo", props.config.ecrRepoName
    );

    const agentRole = new iam.Role(this, "AgentRole", {
      roleName: "InsuranceDemoAgentRole",
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
    });

    // Bedrock model access (foundation models + cross-region inference profiles)
    agentRole.addToPolicy(new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: [
        "arn:aws:bedrock:*::foundation-model/*",
        `arn:aws:bedrock:*:${this.account}:inference-profile/*`,
      ],
    }));

    // ECR pull + auth token
    repo.grantPull(agentRole);
    agentRole.addToPolicy(new iam.PolicyStatement({
      actions: ["ecr:GetAuthorizationToken"],
      resources: ["*"],
    }));

    // CloudWatch logs
    agentRole.addToPolicy(new iam.PolicyStatement({
      actions: ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      resources: ["*"],
    }));

    // Get the default policy CFN resource so Runtimes depend on it
    const policyResource = agentRole.node.findChild("DefaultPolicy").node.defaultChild as cdk.CfnResource;

    for (const agent of AGENTS) {
      const rt = new AgentRuntime(this, `Agent-${agent.name}`, {
        agentName: agent.name,
        description: agent.description,
        ecrImageUri: `${repo.repositoryUri}:${agent.ecrTag}`,
        role: agentRole,
        protocol: agent.protocol,
        environmentVariables: agent.envVars,
        dependsOn: [policyResource],
      });
      new cdk.CfnOutput(this, `${agent.name}-arn`, {
        value: rt.runtimeArn,
        description: `AgentCore Runtime ARN for ${agent.name}`,
      });
    }

    new cdk.CfnOutput(this, "EcrRepoUri", { value: repo.repositoryUri });
  }
}
