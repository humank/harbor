import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bot, Activity, AlertTriangle, Clock, Plus, Search } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { listAgents, healthSummary, tenantAudit } from '../api/client'
import type { AgentRecord, AuditEntry } from '../types/agent'

const STATS = [
  { label: 'Total Agents', key: 'total', icon: Bot },
  { label: 'Published', key: 'published', icon: Activity },
  { label: 'Suspended', key: 'suspended', icon: AlertTriangle },
  { label: 'Pending Review', key: 'in_review', icon: Clock },
] as const

export default function Dashboard() {
  const [agents, setAgents] = useState<AgentRecord[]>([])
  const [health, setHealth] = useState<Record<string, number>>({})
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([listAgents(), healthSummary(), tenantAudit(10)])
      .then(([agentsRes, h, a]) => {
        setAgents(agentsRes.items)
        setHealth(h)
        setAudit(a)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <p className="py-20 text-center text-text-muted">Loading dashboard…</p>
  }

  if (error) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-red-500" />
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  const count = (key: string) => (key === 'total' ? agents.length : agents.filter((a) => a.lifecycle_status === key).length)

  return (
    <div className="space-y-8">
      <h1 className="font-heading text-2xl font-bold text-text">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map((s) => (
          <Card key={s.label} hover>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-text-muted">{s.label}</p>
                <p className="mt-1 font-heading text-3xl font-bold text-primary">{count(s.key)}</p>
              </div>
              <div className="rounded-xl bg-primary-light p-3">
                <s.icon className="h-5 w-5 text-primary" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Health summary */}
      <Card>
        <h2 className="font-heading text-lg font-semibold text-text">Health Summary</h2>
        <div className="mt-4 flex gap-6">
          {['healthy', 'unhealthy', 'unknown'].map((state) => (
            <div key={state} className="flex items-center gap-2">
              <Badge label={state} />
              <span className="font-heading text-lg font-bold text-primary">{health[state] ?? 0}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent activity */}
      <Card>
        <h2 className="font-heading text-lg font-semibold text-text">Recent Activity</h2>
        {audit.length === 0 ? (
          <p className="mt-3 text-sm text-text-muted">No recent activity.</p>
        ) : (
          <ul className="mt-4 divide-y divide-border">
            {audit.map((e, i) => (
              <li key={i} className="flex items-center gap-3 py-3 text-sm">
                <span className="shrink-0 text-xs text-text-muted">{new Date(e.timestamp).toLocaleString()}</span>
                <Badge label={e.action} />
                <Link to={`/agents/${e.agent_id}`} className="cursor-pointer truncate text-primary hover:underline">{e.agent_id}</Link>
                <span className="ml-auto text-xs text-text-muted">{e.actor}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Quick actions */}
      <div className="flex gap-3">
        <Link to="/register">
          <Button variant="cta">
            <Plus className="mr-1.5 h-4 w-4" />
            Register Agent
          </Button>
        </Link>
        <Link to="/discovery">
          <Button variant="secondary">
            <Search className="mr-1.5 h-4 w-4" />
            Discovery
          </Button>
        </Link>
      </div>
    </div>
  )
}
