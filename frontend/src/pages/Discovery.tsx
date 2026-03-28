import { useState } from 'react'
import { Search, Zap } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { discoverByCapability, discoverByPhase, resolveAgent } from '../api/client'
import type { AgentRecord } from '../types/agent'

type Mode = 'capability' | 'phase'

export default function Discovery() {
  const [mode, setMode] = useState<Mode>('capability')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AgentRecord[]>([])
  const [resolvedId, setResolvedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch() {
    const term = query.trim()
    if (!term) return
    setLoading(true)
    setError(null)
    setResolvedId(null)
    try {
      const data = mode === 'capability'
        ? await discoverByCapability(term)
        : await discoverByPhase(term)
      setResults(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  async function handleResolve() {
    const term = query.trim()
    if (!term) return
    setLoading(true)
    setError(null)
    try {
      const cap = mode === 'capability' ? term : undefined
      const phase = mode === 'phase' ? term : undefined
      const best = await resolveAgent(cap, phase)
      if (best) {
        setResolvedId(best.agent_id)
        if (!results.find(r => r.agent_id === best.agent_id)) {
          setResults(prev => [best, ...prev])
        }
      } else {
        setError('No agent resolved for this query')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Resolve failed')
    } finally {
      setLoading(false)
    }
  }

  function bestPriority(agent: AgentRecord): number | null {
    const term = query.trim()
    const rule = agent.routing_rules.find(r =>
      mode === 'capability' ? r.capability === term : r.phase === term
    )
    return rule?.priority ?? null
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Discovery</h1>

      <Card>
        <div className="space-y-4">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-700">Search mode</legend>
            <div className="flex gap-4">
              {(['capability', 'phase'] as const).map(m => (
                <label key={m} className="flex items-center gap-2 cursor-pointer text-sm text-slate-700">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === m}
                    onChange={() => setMode(m)}
                    className="accent-sky-600"
                  />
                  By {m}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                placeholder={mode === 'capability' ? 'e.g. cobol_analysis' : 'e.g. discovery'}
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button onClick={handleSearch} disabled={loading || !query.trim()}>
              <Search className="mr-1.5 h-4 w-4" />
              Search
            </Button>
            <Button variant="secondary" onClick={handleResolve} disabled={loading || !query.trim()}>
              <Zap className="mr-1.5 h-4 w-4" />
              Resolve Best
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">Searching…</p>}

      {!loading && !error && results.length === 0 && query.trim() !== '' && (
        <p className="text-sm text-slate-500">No agents found.</p>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map(agent => {
            const isResolved = agent.agent_id === resolvedId
            const priority = bestPriority(agent)
            return (
              <Card
                key={agent.agent_id}
                className={isResolved ? 'ring-2 ring-sky-500 border-sky-300' : ''}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900">{agent.name}</span>
                      <Badge label={agent.lifecycle_status} />
                      {isResolved && <Badge label="best match" className="bg-sky-100 text-sky-800" />}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.capabilities.map(c => (
                        <span key={c} className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{c}</span>
                      ))}
                    </div>
                  </div>
                  {priority !== null && (
                    <span className="shrink-0 text-xs font-medium text-slate-500">
                      priority {priority}
                    </span>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
