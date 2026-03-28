import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { Sidebar } from './components/layout/Sidebar'
import Dashboard from './pages/Dashboard'
import AgentCatalog from './pages/AgentCatalog'
import AgentDetail from './pages/AgentDetail'
import RegisterAgent from './pages/RegisterAgent'
import ReviewQueue from './pages/ReviewQueue'
import PolicyManagement from './pages/PolicyManagement'
import Discovery from './pages/Discovery'
import AuditLog from './pages/AuditLog'

export default function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <Routes>
          <Route element={<Sidebar />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<AgentCatalog />} />
            <Route path="/agents/:agentId" element={<AgentDetail />} />
            <Route path="/register" element={<RegisterAgent />} />
            <Route path="/discovery" element={<Discovery />} />
            <Route path="/reviews" element={<ReviewQueue />} />
            <Route path="/policies" element={<PolicyManagement />} />
            <Route path="/audit" element={<AuditLog />} />
          </Route>
        </Routes>
      </ProtectedRoute>
    </AuthProvider>
  )
}
