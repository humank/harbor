import type { ButtonHTMLAttributes } from 'react'

const variants = {
  primary: 'bg-primary text-white shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30 hover:-translate-y-0.5',
  secondary: 'bg-bg-card text-primary border border-primary/30 hover:bg-primary-light',
  danger: 'bg-red-500 text-white shadow-md shadow-red-500/20 hover:shadow-lg hover:shadow-red-500/30 hover:-translate-y-0.5',
  ghost: 'text-text-muted hover:text-text hover:bg-bg-hover',
  cta: 'bg-cta text-white shadow-md shadow-cta/20 hover:shadow-lg hover:shadow-cta/30 hover:-translate-y-0.5',
} as const

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants
  size?: 'sm' | 'md'
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }: ButtonProps) {
  const sizeClass = size === 'sm' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2.5 text-sm'
  return (
    <button
      className={`inline-flex items-center justify-center rounded-xl font-semibold transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizeClass} ${className}`}
      {...props}
    />
  )
}
