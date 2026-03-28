import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { LayoutDashboard, Bot, PlusCircle, Search, ClipboardCheck, Shield, FileText, LogOut } from 'lucide-react'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/register', icon: PlusCircle, label: 'Register' },
  { to: '/discovery', icon: Search, label: 'Discovery' },
  { to: '/reviews', icon: ClipboardCheck, label: 'Reviews' },
  { to: '/policies', icon: Shield, label: 'Policies' },
  { to: '/audit', icon: FileText, label: 'Audit Log' },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  return (
    <div className="flex h-screen">
      <aside className="flex w-60 flex-col border-r border-border bg-bg-card shadow-sm shadow-shadow">
        <div className="flex items-center gap-2.5 border-b border-border px-6 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white text-sm font-bold">H</div>
          <span className="text-lg font-heading font-semibold text-text">Harbor</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-primary-light text-primary shadow-sm shadow-primary/10'
                    : 'text-text-muted hover:bg-bg-hover hover:text-text'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border px-5 py-4">
          <div className="text-xs font-medium text-text-muted truncate">{user?.email}</div>
          <button onClick={logout} className="mt-2 flex items-center gap-1.5 text-xs text-text-muted hover:text-red-500 transition-colors duration-200 cursor-pointer">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto bg-bg p-8">
        <Outlet />
      </main>
    </div>
  )
}
