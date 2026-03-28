import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export function Input({ label, className = '', id, ...props }: InputProps) {
  return (
    <div>
      {label && <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-text-muted">{label}</label>}
      <input
        id={id}
        className={`w-full rounded-xl border border-border bg-bg-card px-4 py-2.5 text-sm text-text placeholder:text-text-muted/60 shadow-sm shadow-shadow transition-all duration-200 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:shadow-md outline-none ${className}`}
        {...props}
      />
    </div>
  )
}
