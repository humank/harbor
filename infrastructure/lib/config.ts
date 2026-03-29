export interface HarborConfig {
  tableName: string;
  environment: "dev" | "prod";
  enableAuth: boolean;
  orgId: string;
  /** ARN of the orchestrator AgentCore Runtime (for agent proxy) */
  agentRuntimeArn: string;
}

export const devConfig: HarborConfig = {
  tableName: "harbor-agent-registry",
  environment: "dev",
  enableAuth: false,
  orgId: "",
  agentRuntimeArn: "",
};

export const prodConfig: HarborConfig = {
  tableName: "harbor-agent-registry",
  environment: "prod",
  enableAuth: true,
  orgId: "",
  agentRuntimeArn: "",
};
