import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { listAgents } from '../api/client'
import type { AgentRecord, AgentLifecycle } from '../types/agent'

const FILTERS: { label: string; value: AgentLifecycle | undefined }[] = [
  { label: 'All', value: undefined },
  { label: 'Draft', value: 'draft' },
  { label: 'Published', value: 'published' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Deprecated', value: 'deprecated' },
]

export default function AgentCatalog() {
  const [agents, setAgents] = useState<AgentRecord[]>([])
  const [search, setSearch] = useState('')
  const [lifecycle, setLifecycle] = useState<AgentLifecycle | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    listAgents(lifecycle)
      .then((res) => setAgents(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [lifecycle])

  const filtered = agents.filter((a) => a.name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="space-y-6">
      <h1 className="font-heading text-2xl font-bold text-text">Agent Catalog</h1>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search agents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => setLifecycle(f.value)}
              className={`cursor-pointer rounded-xl px-3.5 py-1.5 text-sm font-semibold transition-all duration-200 ${
                lifecycle === f.value
                  ? 'bg-primary text-white shadow-sm shadow-primary/20'
                  : 'text-text-muted hover:bg-bg-hover hover:text-text'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-text-muted">Loading agents…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-text-muted">No agents found.</p>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <Link key={agent.agent_id} to={`/agents/${agent.agent_id}`} className="cursor-pointer">
              <Card hover className="h-full">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="font-heading text-base font-semibold text-text">{agent.name}</h2>
                  <Badge label={agent.lifecycle_status} />
                </div>
                {agent.description && (
                  <p className="mt-1.5 line-clamp-2 text-sm text-text-muted">{agent.description}</p>
                )}
                {agent.capabilities.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {agent.capabilities.map((cap) => (
                      <span key={cap} className="rounded-lg bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600">
                        {cap}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-3 text-xs text-text-muted">
                  Updated {new Date(agent.updated_at).toLocaleDateString()}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
