import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Layers, ScrollText } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { getAgent, transitionLifecycle, listVersions, agentAudit } from '../api/client'
import type { AgentRecord, AgentVersion, AuditEntry } from '../types/agent'

const TRANSITIONS: Record<string, string[]> = {
  draft: ['submitted'],
  submitted: ['in_review', 'draft'],
  in_review: ['approved', 'draft'],
  approved: ['published', 'draft'],
  published: ['suspended', 'deprecated'],
  suspended: ['published', 'deprecated'],
  deprecated: ['retired', 'published'],
}

const tabs = [
  { key: 'versions', label: 'Versions', icon: Layers },
  { key: 'audit', label: 'Audit', icon: ScrollText },
] as const

export default function AgentDetail() {
  const { agentId } = useParams<{ agentId: string }>()
  const navigate = useNavigate()
  const [agent, setAgent] = useState<AgentRecord | null>(null)
  const [versions, setVersions] = useState<AgentVersion[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [tab, setTab] = useState<'versions' | 'audit'>('versions')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    getAgent(agentId)
      .then(setAgent)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [agentId])

  useEffect(() => {
    if (!agentId) return
    if (tab === 'versions') listVersions(agentId).then(setVersions).catch(() => {})
    else agentAudit(agentId).then(setAudit).catch(() => {})
  }, [agentId, tab])

  async function handleTransition(target: string) {
    if (!agentId) return
    try {
      const updated = await transitionLifecycle(agentId, target)
      setAgent(updated)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Transition failed')
    }
  }

  if (loading)
    return <div className="flex items-center justify-center py-20 text-text-muted">Loading…</div>
  if (error)
    return (
      <div className="mx-auto max-w-3xl py-20 text-center">
        <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      </div>
    )
  if (!agent) return null

  const transitions = TRANSITIONS[agent.lifecycle_status] || []

  return (
    <div className="mx-auto max-w-4xl space-y-6 py-8">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-primary cursor-pointer transition-colors duration-200"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      {/* Header */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-heading text-2xl font-bold text-text">{agent.name}</h1>
            <p className="mt-1 text-sm text-text-muted font-mono">{agent.agent_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge label={agent.lifecycle_status} />
            <Badge label={agent.visibility} />
            <span className="text-xs text-text-muted">v{agent.version}</span>
          </div>
        </div>
      </Card>

      {/* Metadata */}
      <Card>
        <h2 className="font-heading mb-4 text-lg font-semibold text-text">Metadata</h2>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          {[
            ['Description', agent.description || '—'],
            ['URL', agent.url || '—'],
            ['Model', agent.model_id || '—'],
            ['Timeout', `${agent.timeout_seconds}s`],
            ['Created by', agent.created_by],
            ['Created', new Date(agent.created_at).toLocaleString()],
            ['Updated', new Date(agent.updated_at).toLocaleString()],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-text-muted">{label}</dt>
              <dd className={`text-text ${label === 'URL' ? 'break-all' : ''}`}>{value}</dd>
            </div>
          ))}
          <div className="sm:col-span-2">
            <dt className="text-text-muted">Capabilities</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {agent.capabilities.length
                ? agent.capabilities.map((c) => <Badge key={c} label={c} />)
                : <span className="text-text-muted">—</span>}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-text-muted">Phase Affinity</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {agent.phase_affinity.length
                ? agent.phase_affinity.map((p) => <Badge key={p} label={p} />)
                : <span className="text-text-muted">—</span>}
            </dd>
          </div>
        </dl>
      </Card>

      {/* Lifecycle Actions */}
      {transitions.length > 0 && (
        <Card>
          <h2 className="font-heading mb-3 text-lg font-semibold text-text">Lifecycle Actions</h2>
          <div className="flex flex-wrap gap-2">
            {transitions.map((t) => (
              <Button
                key={t}
                variant={t === 'draft' ? 'secondary' : t === 'suspended' ? 'danger' : 'primary'}
                size="sm"
                onClick={() => handleTransition(t)}
              >
                → {t.replace('_', ' ')}
              </Button>
            ))}
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <div className="mb-4 flex gap-4 border-b border-border">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`cursor-pointer inline-flex items-center gap-1.5 pb-2 text-sm font-medium transition-colors duration-200 ${
                tab === key
                  ? 'border-b-2 border-primary text-primary'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {tab === 'versions' &&
          (versions.length === 0 ? (
            <p className="text-sm text-text-muted">No versions recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-muted border-b border-border">
                    <th className="pb-2 font-medium">Version</th>
                    <th className="pb-2 font-medium">Created</th>
                    <th className="pb-2 font-medium">By</th>
                  </tr>
                </thead>
                <tbody className="bg-bg-card">
                  {versions.map((v) => (
                    <tr
                      key={v.version}
                      className="border-t border-border hover:bg-bg-hover transition-colors duration-200"
                    >
                      <td className="py-2.5 font-mono text-text">{v.version}</td>
                      <td className="py-2.5 text-text-muted">
                        {new Date(v.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 text-text-muted">{v.created_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

        {tab === 'audit' &&
          (audit.length === 0 ? (
            <p className="text-sm text-text-muted">No audit entries.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-muted border-b border-border">
                    <th className="pb-2 font-medium">Action</th>
                    <th className="pb-2 font-medium">Actor</th>
                    <th className="pb-2 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody className="bg-bg-card">
                  {audit.map((a, i) => (
                    <tr
                      key={i}
                      className="border-t border-border hover:bg-bg-hover transition-colors duration-200"
                    >
                      <td className="py-2.5 text-text">{a.action}</td>
                      <td className="py-2.5 text-text-muted">{a.actor}</td>
                      <td className="py-2.5 text-text-muted">
                        {new Date(a.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </Card>
    </div>
  )
}
