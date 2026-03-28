const colors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-600',
  submitted: 'bg-amber-50 text-amber-700',
  in_review: 'bg-blue-50 text-blue-700',
  approved: 'bg-emerald-50 text-emerald-700',
  published: 'bg-green-50 text-green-700',
  suspended: 'bg-red-50 text-red-700',
  deprecated: 'bg-orange-50 text-orange-700',
  retired: 'bg-slate-100 text-slate-400',
  healthy: 'bg-green-50 text-green-700',
  unhealthy: 'bg-red-50 text-red-700',
  unknown: 'bg-slate-100 text-slate-500',
}

export function Badge({ label, className = '' }: { label: string; className?: string }) {
  const color = colors[label] || 'bg-slate-100 text-slate-600'
  return <span className={`inline-block rounded-lg px-2.5 py-1 text-xs font-semibold ${color} ${className}`}>{label}</span>
}
