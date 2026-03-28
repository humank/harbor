import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import type { ReactNode } from 'react'

export function ProtectedRoute({ children, role }: { children: ReactNode; role?: string }) {
  const { isAuthenticated, loading, hasRole, login } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen text-slate-500">Loading...</div>
  if (!isAuthenticated) { login(); return null }
  if (role && !hasRole(role)) return <Navigate to="/" replace />
  return <>{children}</>
}
