import type { AgentRecord, AgentVersion, AuditEntry, CapabilityPolicy, CommunicationRule, HealthStatus, PaginatedResponse, SchedulePolicy } from '../types/agent'

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function getToken(): string {
  const stored = sessionStorage.getItem('harbor_user')
  if (!stored) return ''
  return JSON.parse(stored).token || ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}`, ...init?.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Agents
export const listAgents = (lifecycle?: string, limit = 50, cursor?: string) => {
  const params = new URLSearchParams()
  if (lifecycle) params.set('lifecycle', lifecycle)
  if (limit) params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  return request<PaginatedResponse<AgentRecord>>(`/agents?${params}`)
}
export const getAgent = (id: string) => request<AgentRecord>(`/agents/${id}`)
export const registerAgent = (data: Partial<AgentRecord>) => request<AgentRecord>('/agents', { method: 'POST', body: JSON.stringify(data) })
export const updateAgent = (id: string, data: Record<string, unknown>) => request<AgentRecord>(`/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
export const deleteAgent = (id: string) => request<{ deleted: string }>(`/agents/${id}`, { method: 'DELETE' })

// Lifecycle
export const transitionLifecycle = (id: string, target: string, reason = '') =>
  request<AgentRecord>(`/agents/${id}/lifecycle?target=${target}&reason=${encodeURIComponent(reason)}`, { method: 'PUT' })

// Versions
export const createVersion = (id: string) => request<AgentVersion>(`/agents/${id}/versions`, { method: 'POST' })
export const listVersions = (id: string) => request<AgentVersion[]>(`/agents/${id}/versions`)

// Health
export const heartbeat = (id: string) => request<HealthStatus>(`/agents/${id}/health`, { method: 'PUT' })
export const healthSummary = () => request<Record<string, number>>('/health/summary')

// Audit
export const agentAudit = (id: string, limit = 50) => request<AuditEntry[]>(`/agents/${id}/audit?limit=${limit}`)
export const tenantAudit = (limit = 100) => request<AuditEntry[]>(`/audit?limit=${limit}`)

// Discovery
export const discoverByCapability = (cap: string) => request<AgentRecord[]>(`/discover/capability/${cap}`)
export const discoverByPhase = (phase: string) => request<AgentRecord[]>(`/discover/phase/${phase}`)
export const resolveAgent = (cap?: string, phase?: string) => {
  const params = new URLSearchParams()
  if (cap) params.set('capability', cap)
  if (phase) params.set('phase', phase)
  return request<AgentRecord | null>(`/discover/resolve?${params}`)
}

// Policies
export const putCapabilityPolicy = (p: CapabilityPolicy) => request('/policies/capability', { method: 'POST', body: JSON.stringify(p) })
export const getCapabilityPolicy = (id: string) => request<CapabilityPolicy | null>(`/policies/capability/${id}`)
export const putCommunicationRule = (r: CommunicationRule) => request('/policies/communication', { method: 'POST', body: JSON.stringify(r) })
export const listCommunicationRules = () => request<CommunicationRule[]>('/policies/communication')
export const putSchedulePolicy = (p: SchedulePolicy) => request('/policies/schedule', { method: 'POST', body: JSON.stringify(p) })
export const getSchedulePolicy = (id: string) => request<SchedulePolicy | null>(`/policies/schedule/${id}`)
export const evaluatePolicy = (from: string, to: string) =>
  request<{ allowed: boolean; reason: string }>(`/policies/evaluate?from_agent=${from}&to_agent=${to}`, { method: 'POST' })

// Reviews
export const listPendingReviews = () => request<PaginatedResponse<AgentRecord>>('/reviews/pending')
export const submitReview = (id: string, action: string, reason = '') =>
  request(`/reviews/${id}?action=${action}&reason=${encodeURIComponent(reason)}`, { method: 'POST' })
