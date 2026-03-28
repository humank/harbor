import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export function Input({ label, className = '', id, ...props }: InputProps) {
  return (
    <div>
      {label && <label htmlFor={id} className="mb-1 block text-sm font-medium text-slate-700">{label}</label>}
      <input id={id} className={`w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:ring-1 focus:ring-sky-500 outline-none ${className}`} {...props} />
    </div>
  )
}
