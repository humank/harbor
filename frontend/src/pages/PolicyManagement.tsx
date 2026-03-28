import { useState, useEffect } from 'react'
import { Shield } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { listCommunicationRules, putCommunicationRule } from '../api/client'
import type { CommunicationRule } from '../types/agent'

function PolicyManagement() {
  const [rules, setRules] = useState<CommunicationRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ rule_id: '', from_agent: '', to_agent: '', allowed: true, conditions: '' })
  const [submitting, setSubmitting] = useState(false)

  const fetchRules = async () => {
    setLoading(true)
    setError('')
    try {
      setRules(await listCommunicationRules())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load rules')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRules() }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await putCommunicationRule({
        rule_id: form.rule_id,
        from_agent: form.from_agent,
        to_agent: form.to_agent,
        allowed: form.allowed,
        required: false,
        conditions: form.conditions ? form.conditions.split(',').map(s => s.trim()).filter(Boolean) : [],
      })
      setForm({ rule_id: '', from_agent: '', to_agent: '', allowed: true, conditions: '' })
      await fetchRules()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save rule')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold text-primary">Policy Management</h1>
      </div>

      {error && <div className="rounded-lg bg-red-900/50 p-3 text-sm text-red-400">{error}</div>}

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-primary">Communication Rules</h2>

        {loading ? (
          <p className="text-sm text-text-muted">Loading rules…</p>
        ) : rules.length === 0 ? (
          <p className="text-sm text-text-muted">No communication rules defined yet.</p>
        ) : (
          <div className="mb-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted">
                  <th className="pb-2 pr-4 font-medium">Rule ID</th>
                  <th className="pb-2 pr-4 font-medium">From</th>
                  <th className="pb-2 pr-4 font-medium">To</th>
                  <th className="pb-2 pr-4 font-medium">Allowed</th>
                  <th className="pb-2 font-medium">Conditions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map(r => (
                  <tr key={r.rule_id} className="border-b border-border transition-colors duration-200 hover:bg-bg-hover">
                    <td className="py-2 pr-4 font-mono text-text">{r.rule_id}</td>
                    <td className="py-2 pr-4 text-text">{r.from_agent}</td>
                    <td className="py-2 pr-4 text-text">{r.to_agent}</td>
                    <td className="py-2 pr-4">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${r.allowed ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                        {r.allowed ? 'Allowed' : 'Denied'}
                      </span>
                    </td>
                    <td className="py-2 text-text-muted">{r.conditions.length ? r.conditions.join(', ') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid gap-3 border-t border-border pt-4 sm:grid-cols-2 lg:grid-cols-3">
          <Input id="rule_id" label="Rule ID" value={form.rule_id} onChange={e => setForm(f => ({ ...f, rule_id: e.target.value }))} required />
          <Input id="from_agent" label="From Agent" value={form.from_agent} onChange={e => setForm(f => ({ ...f, from_agent: e.target.value }))} required />
          <Input id="to_agent" label="To Agent" value={form.to_agent} onChange={e => setForm(f => ({ ...f, to_agent: e.target.value }))} required />
          <Input id="conditions" label="Conditions (comma-separated)" value={form.conditions} onChange={e => setForm(f => ({ ...f, conditions: e.target.value }))} />
          <div className="flex items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-text-muted cursor-pointer">
              <input type="checkbox" checked={form.allowed} onChange={e => setForm(f => ({ ...f, allowed: e.target.checked }))} className="h-4 w-4 rounded border-border accent-primary" />
              Allowed
            </label>
          </div>
          <div className="flex items-end">
            <Button type="submit" variant="primary" disabled={submitting}>{submitting ? 'Saving…' : 'Add Rule'}</Button>
          </div>
        </form>
      </Card>

      <Card>
        <h2 className="mb-2 text-lg font-semibold text-primary">Capability Policies</h2>
        <p className="text-sm text-text-muted">Capability policy editor coming soon.</p>
      </Card>

      <Card>
        <h2 className="mb-2 text-lg font-semibold text-primary">Schedule Policies</h2>
        <p className="text-sm text-text-muted">Schedule policy editor coming soon.</p>
      </Card>
    </div>
  )
}

export default PolicyManagement
