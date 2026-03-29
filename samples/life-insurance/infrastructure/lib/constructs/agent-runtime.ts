import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export interface AgentRuntimeProps {
  agentName: string;
  description: string;
  ecrImageUri: string;
  role: iam.IRole;
  protocol: "A2A" | "HTTP" | "MCP";
  environmentVariables?: Record<string, string>;
  /** Pass the IAM policy resource so Runtime waits for it */
  dependsOn?: cdk.CfnResource[];
}

export class AgentRuntime extends Construct {
  public readonly runtimeArn: string;

  constructor(scope: Construct, id: string, props: AgentRuntimeProps) {
    super(scope, id);

    const runtime = new cdk.CfnResource(this, "Runtime", {
      type: "AWS::BedrockAgentCore::Runtime",
      properties: {
        AgentRuntimeName: `insuranceDemo_${props.agentName.replace(/-/g, "_")}`,
        Description: props.description,
        AgentRuntimeArtifact: {
          ContainerConfiguration: {
            ContainerUri: props.ecrImageUri,
          },
        },
        NetworkConfiguration: { NetworkMode: "PUBLIC" },
        ProtocolConfiguration: props.protocol,
        RoleArn: props.role.roleArn,
        EnvironmentVariables: props.environmentVariables,
        Tags: { Project: "harbor-insurance-demo", Agent: props.agentName },
      },
    });

    this.runtimeArn = runtime.getAtt("AgentRuntimeArn").toString();

    if (props.dependsOn) {
      for (const dep of props.dependsOn) {
        runtime.addDependency(dep);
      }
    }
  }
}
