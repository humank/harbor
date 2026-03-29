import { useEffect, useState } from 'react';
import type { AgentStatus } from '../types/a2a';

export function AgentPanel() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);

  useEffect(() => {
    const harborUrl = import.meta.env.VITE_HARBOR_API_URL || '/agents/status';
    const poll = async () => {
      try {
        // Try Harbor API first, fall back to local proxy
        const url = harborUrl.startsWith('http') ? `${harborUrl}/agents?limit=20` : harborUrl;
        const resp = await fetch(url);
        if (resp.ok) {
          const data = await resp.json();
          const items = data.items || data.agents || [];
          setAgents(items.map((a: Record<string, unknown>) => ({
            agent_id: String(a.agent_id || a.name || ''),
            name: String(a.name || a.agent_id || ''),
            lifecycle: String(a.lifecycle_status || 'unknown'),
            health: a.lifecycle_status === 'published' ? 'healthy' : 'unknown',
            a2a_url: '',
          })));
        }
      } catch { /* ignore */ }
    };
    poll();
    const id = setInterval(poll, 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider">Agent 狀態</h2>
      <div className="space-y-1.5">
        {agents.map((a) => (
          <div key={a.agent_id} className="flex items-center gap-2 text-sm">
            <span className={`w-2 h-2 rounded-full shrink-0 ${a.lifecycle === 'published' ? 'bg-success' : a.lifecycle === 'suspended' ? 'bg-error' : 'bg-warning'}`} />
            <span className="text-text truncate">{a.name}</span>
          </div>
        ))}
        {agents.length === 0 && <p className="text-xs text-text-muted">等待連線...</p>}
      </div>
    </div>
  );
}
