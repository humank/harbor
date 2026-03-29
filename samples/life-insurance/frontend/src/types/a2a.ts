/* A2A v1.0 TypeScript types */

export interface Part {
  text?: string;
  data?: Record<string, unknown>;
  raw?: string;
  url?: string;
  mediaType?: string;
  filename?: string;
}

export interface Message {
  messageId: string;
  role: 'ROLE_USER' | 'ROLE_AGENT';
  contextId?: string;
  taskId?: string;
  parts: Part[];
}

export interface Artifact {
  artifactId: string;
  name?: string;
  description?: string;
  parts: Part[];
}

export interface TaskStatus {
  state: string;
  message?: Message;
  timestamp?: string;
}

export interface Task {
  id: string;
  contextId?: string;
  status: TaskStatus;
  artifacts?: Artifact[];
}

export interface TaskStatusUpdateEvent {
  taskId: string;
  contextId: string;
  status: TaskStatus;
}

export interface TaskArtifactUpdateEvent {
  taskId: string;
  contextId: string;
  artifact: Artifact;
}

export interface StreamResponse {
  task?: Task;
  message?: Message;
  statusUpdate?: TaskStatusUpdateEvent;
  artifactUpdate?: TaskArtifactUpdateEvent;
}

export interface AgentStatus {
  agent_id: string;
  name: string;
  lifecycle: string;
  health: string;
  a2a_url: string;
}

/* Domain types */

export interface RiskFactor {
  name: string;
  score: number;
  weight: number;
  level: string;
  detail: string;
}

export interface RiskData {
  score: number;
  risk_class: string;
  bmi: number;
  factors: RiskFactor[];
  prediction: string;
  premium_impact: string;
}

export interface ProductData {
  product_id: string;
  provider: string;
  name: string;
  category: string;
  base_premium_monthly: number;
  coverage: Record<string, unknown>;
  highlights: string[];
}

export interface PremiumItem {
  product_id: string;
  product_name: string;
  monthly_premium: number;
  annual_premium: number;
  risk_adjustment: number;
  breakdown: { base: number; risk_loading: number; discount: number };
}

export interface PremiumData {
  results: PremiumItem[];
  total_monthly: number;
  total_annual: number;
}
