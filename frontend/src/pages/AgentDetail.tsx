import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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

  if (loading) return <div className="flex items-center justify-center py-20 text-slate-500">Loading…</div>
  if (error) return <div className="mx-auto max-w-3xl py-20 text-center text-red-600">{error}</div>
  if (!agent) return null

  const transitions = TRANSITIONS[agent.lifecycle_status] || []

  return (
    <div className="mx-auto max-w-4xl space-y-6 py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-700 cursor-pointer">← Back</button>

      {/* Header */}
      <Card>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{agent.name}</h1>
            <p className="mt-1 text-sm text-slate-500 font-mono">{agent.agent_id}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge label={agent.lifecycle_status} />
            <Badge label={agent.visibility} />
            <span className="text-xs text-slate-400">v{agent.version}</span>
          </div>
        </div>
      </Card>

      {/* Metadata */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Metadata</h2>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <div><dt className="text-slate-500">Description</dt><dd className="text-slate-800">{agent.description || '—'}</dd></div>
          <div><dt className="text-slate-500">URL</dt><dd className="text-slate-800 break-all">{agent.url || '—'}</dd></div>
          <div><dt className="text-slate-500">Model</dt><dd className="text-slate-800">{agent.model_id || '—'}</dd></div>
          <div><dt className="text-slate-500">Timeout</dt><dd className="text-slate-800">{agent.timeout_seconds}s</dd></div>
          <div><dt className="text-slate-500">Created by</dt><dd className="text-slate-800">{agent.created_by}</dd></div>
          <div><dt className="text-slate-500">Created</dt><dd className="text-slate-800">{new Date(agent.created_at).toLocaleString()}</dd></div>
          <div><dt className="text-slate-500">Updated</dt><dd className="text-slate-800">{new Date(agent.updated_at).toLocaleString()}</dd></div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Capabilities</dt>
            <dd className="mt-1 flex flex-wrap gap-1">{agent.capabilities.length ? agent.capabilities.map((c) => <Badge key={c} label={c} />) : '—'}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Phase Affinity</dt>
            <dd className="mt-1 flex flex-wrap gap-1">{agent.phase_affinity.length ? agent.phase_affinity.map((p) => <Badge key={p} label={p} />) : '—'}</dd>
          </div>
        </dl>
      </Card>

      {/* Lifecycle Actions */}
      {transitions.length > 0 && (
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Lifecycle Actions</h2>
          <div className="flex flex-wrap gap-2">
            {transitions.map((t) => (
              <Button key={t} variant={t === 'draft' ? 'secondary' : t === 'suspended' ? 'danger' : 'primary'} size="sm" onClick={() => handleTransition(t)}>
                → {t.replace('_', ' ')}
              </Button>
            ))}
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <div className="mb-4 flex gap-4 border-b border-slate-200">
          {(['versions', 'audit'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`cursor-pointer pb-2 text-sm font-medium transition-colors ${tab === t ? 'border-b-2 border-sky-600 text-sky-600' : 'text-slate-500 hover:text-slate-700'}`}
            >
              {t === 'versions' ? 'Versions' : 'Audit'}
            </button>
          ))}
        </div>

        {tab === 'versions' && (
          versions.length === 0
            ? <p className="text-sm text-slate-400">No versions recorded.</p>
            : <table className="w-full text-sm">
                <thead><tr className="text-left text-slate-500"><th className="pb-2">Version</th><th className="pb-2">Created</th><th className="pb-2">By</th></tr></thead>
                <tbody>
                  {versions.map((v) => (
                    <tr key={v.version} className="border-t border-slate-100">
                      <td className="py-2 font-mono text-slate-800">{v.version}</td>
                      <td className="py-2 text-slate-600">{new Date(v.created_at).toLocaleString()}</td>
                      <td className="py-2 text-slate-600">{v.created_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
        )}

        {tab === 'audit' && (
          audit.length === 0
            ? <p className="text-sm text-slate-400">No audit entries.</p>
            : <table className="w-full text-sm">
                <thead><tr className="text-left text-slate-500"><th className="pb-2">Action</th><th className="pb-2">Actor</th><th className="pb-2">Time</th></tr></thead>
                <tbody>
                  {audit.map((a, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="py-2 text-slate-800">{a.action}</td>
                      <td className="py-2 text-slate-600">{a.actor}</td>
                      <td className="py-2 text-slate-600">{new Date(a.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
        )}
      </Card>
    </div>
  )
}
