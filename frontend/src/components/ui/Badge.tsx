const colors: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700',
  submitted: 'bg-amber-100 text-amber-800',
  in_review: 'bg-blue-100 text-blue-800',
  approved: 'bg-emerald-100 text-emerald-800',
  published: 'bg-green-100 text-green-800',
  suspended: 'bg-red-100 text-red-800',
  deprecated: 'bg-orange-100 text-orange-800',
  retired: 'bg-slate-200 text-slate-500',
  healthy: 'bg-green-100 text-green-800',
  unhealthy: 'bg-red-100 text-red-800',
  unknown: 'bg-slate-100 text-slate-600',
}

export function Badge({ label, className = '' }: { label: string; className?: string }) {
  const color = colors[label] || 'bg-slate-100 text-slate-700'
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${color} ${className}`}>{label}</span>
}
