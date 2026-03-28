import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Bot, Activity, AlertTriangle, Plus } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { listAgents, healthSummary, tenantAudit } from '../api/client'
import type { AgentRecord, AuditEntry } from '../types/agent'

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
    return <div className="flex items-center justify-center py-20 text-text-muted">Loading dashboard…</div>
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-20 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-red-500" />
        <p className="text-sm text-red-400">{error}</p>
      </div>
    )
  }

  const count = (status: string) => agents.filter((a) => a.lifecycle_status === status).length

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: 'Total Agents', value: agents.length, icon: Bot },
          { label: 'Published', value: count('published'), icon: Activity },
          { label: 'Suspended', value: count('suspended'), icon: AlertTriangle },
          { label: 'Pending Review', value: count('in_review'), icon: Bot },
        ].map((s) => (
          <Card key={s.label} hover>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-text-muted">{s.label}</p>
                <p className="mt-1 text-2xl font-semibold text-primary">{s.value}</p>
              </div>
              <s.icon className="h-8 w-8 text-text-muted" />
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-text">Health Summary</h2>
        <div className="flex gap-4">
          {['healthy', 'unhealthy', 'unknown'].map((state) => (
            <div key={state} className="flex items-center gap-2">
              <Badge label={state} />
              <span className="text-sm font-medium text-text">{health[state] ?? 0}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold text-text">Recent Activity</h2>
        {audit.length === 0 ? (
          <p className="text-sm text-text-muted">No recent activity.</p>
        ) : (
          <ul className="divide-y divide-border">
            {audit.map((e, i) => (
              <li key={i} className="flex items-center gap-3 py-2 text-sm">
                <span className="shrink-0 text-xs text-text-muted">{new Date(e.timestamp).toLocaleString()}</span>
                <Badge label={e.action} />
                <span className="truncate text-text">{e.agent_id}</span>
                <span className="ml-auto text-xs text-text-muted">{e.actor}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="flex gap-3">
        <Link to="/register">
          <Button variant="primary">
            <Plus className="mr-1.5 h-4 w-4" />
            Register Agent
          </Button>
        </Link>
        <Link to="/discovery">
          <Button variant="secondary">
            <Activity className="mr-1.5 h-4 w-4" />
            Discovery
          </Button>
        </Link>
      </div>
    </div>
  )
}
