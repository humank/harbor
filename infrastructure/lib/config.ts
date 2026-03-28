export interface HarborConfig {
  tableName: string;
  environment: "dev" | "prod";
  enableAuth: boolean;
  orgId: string;
}

export const devConfig: HarborConfig = {
  tableName: "harbor-agent-registry",
  environment: "dev",
  enableAuth: false,
  orgId: "",
};

export const prodConfig: HarborConfig = {
  tableName: "harbor-agent-registry",
  environment: "prod",
  enableAuth: true,
  orgId: "",
};
