import type { ReactNode } from 'react'

export function Card({ children, className = '', hover = false }: { children: ReactNode; className?: string; hover?: boolean }) {
  return (
    <div className={`rounded-2xl border border-border bg-bg-card p-6 shadow-sm shadow-shadow transition-all duration-200 ${hover ? 'cursor-pointer hover:shadow-md hover:shadow-shadow-lg hover:-translate-y-0.5' : ''} ${className}`}>
      {children}
    </div>
  )
}
