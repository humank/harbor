const colors: Record<string, string> = {
  draft: 'bg-slate-700 text-slate-300',
  submitted: 'bg-amber-900/50 text-amber-400',
  in_review: 'bg-blue-900/50 text-blue-400',
  approved: 'bg-emerald-900/50 text-emerald-400',
  published: 'bg-green-900/50 text-green-400',
  suspended: 'bg-red-900/50 text-red-400',
  deprecated: 'bg-orange-900/50 text-orange-400',
  retired: 'bg-slate-800 text-slate-500',
  healthy: 'bg-green-900/50 text-green-400',
  unhealthy: 'bg-red-900/50 text-red-400',
  unknown: 'bg-slate-700 text-slate-400',
}

export function Badge({ label, className = '' }: { label: string; className?: string }) {
  const color = colors[label] || 'bg-slate-700 text-slate-300'
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${color} ${className}`}>{label}</span>
}
