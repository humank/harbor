import type { ReactNode } from 'react'

export function Card({ children, className = '', hover = false }: { children: ReactNode; className?: string; hover?: boolean }) {
  return (
    <div className={`rounded-xl border border-border bg-bg-card p-5 transition-all duration-200 ${hover ? 'cursor-pointer hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5' : ''} ${className}`}>
      {children}
    </div>
  )
}
