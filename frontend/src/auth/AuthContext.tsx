import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface User {
  email: string
  tenantId: string
  role: string
  token: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: () => void
  logout: () => void
  isAuthenticated: boolean
  hasRole: (role: string) => boolean
}

const ROLES = ['viewer', 'developer', 'project_admin', 'risk_officer', 'compliance_officer', 'admin']
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN || ''
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || ''
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || window.location.origin + '/callback'
const AUTH_DISABLED = import.meta.env.VITE_AUTH_DISABLED === 'true'

const DEV_USER: User = { email: 'dev@harbor.local', tenantId: 'dev-tenant-000000000000', role: 'admin', token: '' }

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(AUTH_DISABLED ? DEV_USER : null)
  const [loading, setLoading] = useState(!AUTH_DISABLED)

  useEffect(() => {
    if (AUTH_DISABLED) return
    // Check for callback code
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    if (code) {
      exchangeCode(code).then(setUser).finally(() => setLoading(false))
      window.history.replaceState({}, '', window.location.pathname)
    } else {
      // Check stored token
      const stored = sessionStorage.getItem('harbor_user')
      if (stored) setUser(JSON.parse(stored))
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user && !AUTH_DISABLED) sessionStorage.setItem('harbor_user', JSON.stringify(user))
  }, [user])

  const login = useCallback(() => {
    if (AUTH_DISABLED) return
    const url = `${COGNITO_DOMAIN}/oauth2/authorize?response_type=code&client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=openid+email+profile`
    window.location.href = url
  }, [])

  const logout = useCallback(() => {
    sessionStorage.removeItem('harbor_user')
    setUser(null)
    if (!AUTH_DISABLED && COGNITO_DOMAIN) {
      window.location.href = `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${encodeURIComponent(window.location.origin)}`
    }
  }, [])

  const hasRole = useCallback((required: string) => {
    if (!user) return false
    const userIdx = ROLES.indexOf(user.role)
    const reqIdx = ROLES.indexOf(required)
    return userIdx >= reqIdx
  }, [user])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user, hasRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}

async function exchangeCode(code: string): Promise<User> {
  const res = await fetch(`${COGNITO_DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      code,
    }),
  })
  const data = await res.json()
  const payload = JSON.parse(atob(data.id_token.split('.')[1]))
  return {
    email: payload.email || '',
    tenantId: payload['custom:tenant_id'] || 'unknown',
    role: payload['custom:role'] || 'viewer',
    token: data.access_token,
  }
}
