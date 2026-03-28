import type { ButtonHTMLAttributes } from 'react'

const variants = {
  primary: 'bg-cta text-white hover:opacity-90',
  secondary: 'border-2 border-primary text-primary bg-transparent hover:bg-primary/10',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-text-muted hover:bg-bg-hover hover:text-text',
} as const

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants
  size?: 'sm' | 'md'
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }: ButtonProps) {
  const sizeClass = size === 'sm' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2 text-sm'
  return (
    <button
      className={`inline-flex items-center justify-center rounded-lg font-semibold transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 ${variants[variant]} ${sizeClass} ${className}`}
      {...props}
    />
  )
}
