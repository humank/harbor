import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { registerAgent } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function RegisterAgent() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    agent_id: '',
    name: '',
    description: '',
    capabilities: '',
    phase_affinity: '',
    url: '',
  })

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }))

  const splitCsv = (v: string) => v.split(',').map(s => s.trim()).filter(Boolean)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!user) return
    setError('')
    setSubmitting(true)
    try {
      await registerAgent({
        agent_id: form.agent_id,
        name: form.name,
        description: form.description,
        capabilities: splitCsv(form.capabilities),
        phase_affinity: splitCsv(form.phase_affinity),
        url: form.url || undefined,
        tenant_id: user.tenantId,
        owner: { owner_id: user.email, team: '', org_id: user.tenantId },
      })
      navigate(`/agents/${form.agent_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="mb-6 text-2xl font-semibold text-primary">Register Agent</h1>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <p className="rounded-lg bg-red-900/30 border border-red-800 px-4 py-2 text-sm text-red-400">{error}</p>
          )}
          <Input id="agent_id" label="Agent ID" value={form.agent_id} onChange={set('agent_id')} required placeholder="e.g. agent-code-reviewer" />
          <Input id="name" label="Name" value={form.name} onChange={set('name')} required placeholder="e.g. Code Reviewer" />
          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-text-muted">Description</label>
            <textarea id="description" value={form.description} onChange={set('description')} rows={3} className="w-full rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text placeholder:text-text-muted/50 transition-colors duration-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none" placeholder="What does this agent do?" />
          </div>
          <Input id="capabilities" label="Capabilities (comma-separated)" value={form.capabilities} onChange={set('capabilities')} placeholder="e.g. code_review, static_analysis" />
          <Input id="phase_affinity" label="Phase Affinity (comma-separated)" value={form.phase_affinity} onChange={set('phase_affinity')} placeholder="e.g. discovery, implementation" />
          <Input id="url" label="URL (optional)" value={form.url} onChange={set('url')} placeholder="https://agent.example.com" />
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" onClick={() => navigate(-1)}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? 'Registering…' : 'Register'}</Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
