// Mirrors backend Pydantic models

export type AgentLifecycle = 'draft' | 'submitted' | 'in_review' | 'approved' | 'published' | 'suspended' | 'deprecated' | 'retired'
export type Visibility = 'private' | 'ou_shared' | 'org_wide'
export type HealthState = 'healthy' | 'unhealthy' | 'unknown'

export interface OwnerInfo {
  owner_id: string
  team: string
  org_id: string
}

export interface AgentSkill {
  id: string
  name: string
  description: string
  tags: string[]
}

export interface RoutingRule {
  phase?: string
  capability?: string
  priority: number
}

export interface AgentRecord {
  agent_id: string
  name: string
  description: string
  version: string
  tenant_id: string
  owner: OwnerInfo
  visibility: Visibility
  lifecycle_status: AgentLifecycle
  url?: string
  skills: AgentSkill[]
  capabilities: string[]
  phase_affinity: string[]
  routing_rules: RoutingRule[]
  tags: Record<string, string>
  model_id?: string
  timeout_seconds: number
  sunset_date?: string
  created_at: string
  updated_at: string
  created_by: string
}

export interface AgentVersion {
  agent_id: string
  tenant_id: string
  version: string
  snapshot: Record<string, unknown>
  created_at: string
  created_by: string
}

export interface HealthStatus {
  agent_id: string
  tenant_id: string
  state: HealthState
  last_seen?: string
  consecutive_failures: number
  error_message?: string
}

export interface AuditEntry {
  agent_id: string
  tenant_id: string
  action: string
  actor: string
  timestamp: string
  details: Record<string, unknown>
}

export interface CapabilityPolicy {
  agent_id: string
  tenant_id: string
  tools: ResourcePermission
  mcp_servers: ResourcePermission
  apis: ResourcePermission
  data_classification_max: string
}

export interface ResourcePermission {
  allowed: string[]
  denied: string[]
  require_human: string[]
}

export interface CommunicationRule {
  rule_id: string
  from_agent: string
  to_agent: string
  allowed: boolean
  required: boolean
  conditions: string[]
}

export interface SchedulePolicy {
  agent_id: string
  tenant_id: string
  active_windows: TimeWindow[]
  blackout_windows: TimeWindow[]
  out_of_window_action: string
}

export interface TimeWindow {
  cron: string
  timezone: string
}

export interface PaginatedResponse<T> {
  items: T[]
  cursor: string | null
}
