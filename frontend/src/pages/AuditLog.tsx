import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { tenantAudit } from '../api/client'
import type { AuditEntry } from '../types/agent'

function formatTs(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function truncate(obj: Record<string, unknown>, max = 80) {
  const s = JSON.stringify(obj)
  return s.length > max ? s.slice(0, max) + '…' : s
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    tenantAudit().then(setEntries).finally(() => setLoading(false))
  }, [])

  const sorted = [...entries]
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .filter(e => !filter || e.agent_id.includes(filter) || e.action.includes(filter))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-primary" />
        <h1 className="font-heading text-2xl font-bold text-text">Audit Log</h1>
      </div>

      <Input
        placeholder="Filter by agent ID or action…"
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />

      {loading ? (
        <p className="text-sm text-text-muted">Loading audit entries…</p>
      ) : sorted.length === 0 ? (
        <Card className="py-12 text-center text-text-muted">No audit entries found.</Card>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-bg-hover text-text-muted">
                <th className="rounded-tl-xl px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Actor</th>
                <th className="rounded-tr-xl px-4 py-3 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((e, i) => (
                <tr key={`${e.timestamp}-${e.agent_id}-${i}`} className="border-b border-border transition-colors duration-200 hover:bg-bg-hover">
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-text-muted">{formatTs(e.timestamp)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text">{e.agent_id}</td>
                  <td className="px-4 py-3"><Badge label={e.action} /></td>
                  <td className="px-4 py-3 text-text">{e.actor}</td>
                  <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-text-muted">{truncate(e.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
