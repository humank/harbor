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
      <h1 className="text-2xl font-bold text-primary">Discovery</h1>

      <Card>
        <div className="space-y-4">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-text-muted">Search mode</legend>
            <div className="flex gap-2">
              {(['capability', 'phase'] as const).map(m => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
                    mode === m
                      ? 'bg-primary/10 text-primary'
                      : 'text-text-muted hover:bg-bg-hover'
                  }`}
                >
                  By {m}
                </button>
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
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading && <p className="text-sm text-text-muted">Searching…</p>}

      {!loading && !error && results.length === 0 && query.trim() !== '' && (
        <p className="text-sm text-text-muted">No agents found.</p>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map(agent => {
            const isResolved = agent.agent_id === resolvedId
            const priority = bestPriority(agent)
            return (
              <Card
                key={agent.agent_id}
                hover
                className={isResolved ? 'ring-2 ring-primary border-primary' : ''}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text">{agent.name}</span>
                      <Badge label={agent.lifecycle_status} />
                      {isResolved && <Badge label="best match" />}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.capabilities.map(c => (
                        <span key={c} className="rounded bg-cta/20 px-2 py-0.5 text-xs text-cta">{c}</span>
                      ))}
                    </div>
                  </div>
                  {priority !== null && (
                    <span className="shrink-0 text-xs font-medium text-text-muted">
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
