import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Repositories from './pages/Repositories'
import Leads from './pages/Leads'
import Jobs from './pages/Jobs'
import Settings from './pages/Settings'
import Register from './pages/Register'
import SelectOrg from './pages/SelectOrg'
import Integrations from './pages/Integrations'
import Layout from './components/Layout'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, needsOrgSelection } = useAuth()
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }
  
  if (!isAuthenticated) return <Navigate to="/" />
  if (needsOrgSelection) return <Navigate to="/select-org" />
  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, needsOrgSelection } = useAuth()

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  if (isAuthenticated && needsOrgSelection) return <Navigate to="/select-org" />
  return isAuthenticated ? <Navigate to="/app" /> : <>{children}</>
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={<PublicRoute><Landing /></PublicRoute>} />
            <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
            <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
            <Route path="/select-org" element={<SelectOrg />} />
            <Route
              path="/app"
              element={
                <PrivateRoute>
                  <Layout />
                </PrivateRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="projects" element={<Projects />} />
              <Route path="projects/:projectId" element={<ProjectDetail />} />
              <Route path="repositories" element={<Repositories />} />
              <Route path="leads" element={<Leads />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="integrations" element={<Integrations />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
