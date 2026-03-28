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
      <aside className="flex w-56 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
          <span className="text-lg font-bold text-slate-800">⚓ Harbor</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 py-3">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors cursor-pointer ${
                  isActive ? 'bg-sky-50 text-sky-700' : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-4 py-3">
          <div className="text-xs text-slate-500 truncate">{user?.email}</div>
          <button onClick={logout} className="mt-1 flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 cursor-pointer">
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto bg-slate-50 p-6">
        <Outlet />
      </main>
    </div>
  )
}
