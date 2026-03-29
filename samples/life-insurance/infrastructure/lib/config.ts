export interface AgentConfig {
  name: string;
  description: string;
  ecrTag: string;
  protocol: "A2A" | "HTTP" | "MCP";
  usesLlm: boolean;
  envVars?: Record<string, string>;
  /** Capabilities registered in Harbor for discovery */
  capabilities: string[];
}

export const AGENTS: AgentConfig[] = [
  {
    name: "recommendation",
    description: "保險規劃推薦引擎 (Orchestrator) v6",
    ecrTag: "recommendation",
    protocol: "A2A",
    usesLlm: true,
    capabilities: ["plan_recommendation", "needs_analysis"],
    envVars: {
      BEDROCK_MODEL: "us.anthropic.claude-sonnet-4-20250514-v1:0",
      AGENTCORE_RUNTIME: "true",
    },
  },
  {
    name: "product-catalog",
    description: "壽險商品目錄查詢 v2",
    ecrTag: "product-catalog",
    protocol: "A2A",
    usesLlm: false,
    capabilities: ["product_search", "product_comparison"],
  },
  {
    name: "underwriting-risk",
    description: "核保風險預評估 v2",
    ecrTag: "underwriting-risk",
    protocol: "A2A",
    usesLlm: true,
    capabilities: ["risk_assessment", "risk_scoring"],
    envVars: {
      BEDROCK_MODEL: "us.anthropic.claude-sonnet-4-20250514-v1:0",
    },
  },
  {
    name: "premium-calculator",
    description: "保費試算 v2",
    ecrTag: "premium-calculator",
    protocol: "A2A",
    usesLlm: false,
    capabilities: ["premium_calculation", "quote_generation"],
  },
  {
    name: "compliance-check",
    description: "投保資格合規檢查 v2",
    ecrTag: "compliance-check",
    protocol: "A2A",
    usesLlm: false,
    capabilities: ["kyc_check", "regulatory_compliance"],
  },
  {
    name: "explanation",
    description: "保險知識解釋 v2",
    ecrTag: "explanation",
    protocol: "A2A",
    usesLlm: true,
    capabilities: ["term_explanation", "faq"],
    envVars: {
      BEDROCK_MODEL: "us.anthropic.claude-haiku-3-20250620-v1:0",
    },
  },
];

export interface DemoConfig {
  environment: "dev" | "prod";
  ecrRepoName: string;
  /** Harbor API URL for agent registration */
  harborApiUrl: string;
  harborTenant: string;
  harborOwner: string;
}

export const devConfig: DemoConfig = {
  environment: "dev",
  ecrRepoName: "harbor-insurance-demo",
  harborApiUrl: "", // Set via CDK context or env: --context harborApiUrl=https://xxx
  harborTenant: "demo-tenant",
  harborOwner: "cdk-deploy@harbor.local",
};
