import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { listPendingReviews, submitReview } from '../api/client'
import type { AgentRecord } from '../types/agent'

function ReviewCard({
  agent,
  onReviewed,
}: {
  agent: AgentRecord
  onReviewed: (id: string) => void
}) {
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit() {
    if (!action) return
    setSubmitting(true)
    try {
      await submitReview(agent.agent_id, action, reason)
      onReviewed(agent.agent_id)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card hover>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            to={`/agents/${agent.agent_id}`}
            className="font-heading text-lg font-semibold text-text transition-colors duration-200 hover:text-primary cursor-pointer"
          >
            {agent.name}
          </Link>
          <div className="mt-1">
            <Badge label={agent.lifecycle_status} />
          </div>
          {agent.description && (
            <p className="mt-2 text-sm text-text-muted">{agent.description}</p>
          )}
          {agent.capabilities.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {agent.capabilities.map(cap => (
                <span
                  key={cap}
                  className="rounded-lg bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600"
                >
                  {cap}
                </span>
              ))}
            </div>
          )}
          {agent.created_by && (
            <p className="mt-2 text-xs text-text-muted">Submitted by {agent.created_by}</p>
          )}
        </div>
      </div>

      {action === null ? (
        <div className="mt-4 flex gap-2">
          <Button variant="primary" onClick={() => setAction('approve')}>Approve</Button>
          <Button variant="danger" onClick={() => setAction('reject')}>Reject</Button>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <Input
            label={`Reason for ${action}`}
            placeholder={`Reason for ${action}...`}
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? 'Submitting...' : `Confirm ${action}`}
            </Button>
            <Button
              variant="secondary"
              onClick={() => { setAction(null); setReason('') }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function ReviewQueue() {
  const [agents, setAgents] = useState<AgentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listPendingReviews()
      .then(data => setAgents(data.items))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function handleReviewed(id: string) {
    setAgents(prev => prev.filter(a => a.agent_id !== id))
  }

  if (loading) return <p className="p-6 text-text-muted">Loading pending reviews...</p>
  if (error) return <p className="p-6 text-red-600">Error: {error}</p>

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="font-heading text-2xl font-bold text-text">Review Queue</h1>
      {agents.length === 0 ? (
        <p className="text-text-muted">No pending reviews</p>
      ) : (
        agents.map(agent => (
          <ReviewCard key={agent.agent_id} agent={agent} onReviewed={handleReviewed} />
        ))
      )}
    </div>
  )
}
