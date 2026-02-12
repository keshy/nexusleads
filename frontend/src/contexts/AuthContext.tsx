import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../lib/api'

interface Organization {
  id: string
  name: string
  slug: string
  role: string
}

interface User {
  id: string
  username: string
  email: string
  full_name: string
  is_admin: boolean
  organizations?: Organization[]
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  needsOrgSelection: boolean
  activeOrg: Organization | null
  login: (username: string, password: string) => Promise<void>
  register: (data: { username: string; email: string; password: string; full_name?: string }) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  selectOrg: (orgId: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      loadUser()
    } else {
      setIsLoading(false)
    }
  }, [])

  const loadUser = async () => {
    try {
      const userData = await api.getCurrentUser()
      setUser(userData)

      // Auto-select org if user has exactly one, or restore saved selection
      const orgs: Organization[] = userData.organizations || []
      const savedOrgId = localStorage.getItem('activeOrgId')
      if (orgs.length === 1) {
        localStorage.setItem('activeOrgId', orgs[0].id)
      } else if (savedOrgId && orgs.some((o: Organization) => o.id === savedOrgId)) {
        // keep saved
      } else if (orgs.length > 1) {
        // needs selection — don't auto-pick
        localStorage.removeItem('activeOrgId')
      }
    } catch (error) {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    const data = await api.login(username, password)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await loadUser()
  }

  const register = async (data: { username: string; email: string; password: string; full_name?: string }) => {
    await api.register(data)
  }

  const refreshUser = async () => {
    await loadUser()
  }

  const selectOrg = (orgId: string) => {
    localStorage.setItem('activeOrgId', orgId)
    window.location.href = '/app'
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('activeOrgId')
    setUser(null)
    window.location.href = '/'
  }

  const needsOrgSelection =
    !!user &&
    (user.organizations || []).length > 1 &&
    !localStorage.getItem('activeOrgId')

  const activeOrgId = localStorage.getItem('activeOrgId')
  const activeOrg: Organization | null =
    (user?.organizations || []).find((o) => o.id === activeOrgId) || null

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        needsOrgSelection,
        activeOrg,
        login,
        register,
        logout,
        refreshUser,
        selectOrg,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
