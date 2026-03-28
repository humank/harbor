import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
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
      <h1 className="text-2xl font-bold text-slate-900">Agent Catalog</h1>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-sm flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search agents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={lifecycle === f.value ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setLifecycle(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {loading ? (
        <p className="text-sm text-slate-500">Loading agents…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-slate-500">No agents found.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <Link key={agent.agent_id} to={`/agents/${agent.agent_id}`} className="cursor-pointer">
              <Card className="h-full transition-shadow duration-200 hover:shadow-md">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-base font-semibold text-slate-900">{agent.name}</h2>
                  <Badge label={agent.lifecycle_status} />
                </div>
                {agent.description && (
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600">{agent.description}</p>
                )}
                {agent.capabilities.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {agent.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="rounded bg-sky-50 px-2 py-0.5 text-xs text-sky-700"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-3 text-xs text-slate-400">
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
