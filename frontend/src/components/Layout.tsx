import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { 
  LayoutDashboard, 
  FolderKanban, 
  GitBranch, 
  UserCheck, 
  Briefcase,
  LogOut,
  Menu,
  Moon,
  Sun,
  Settings,
  Blocks,
  Building2,
  ChevronsUpDown,
  Wallet,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import MatrixBackground from './MatrixBackground'
import NexusLogo from './NexusLogo'
import ChatSidecar from './ChatSidecar'
import { api } from '../lib/api'

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [creditBalance, setCreditBalance] = useState<number | null>(null)

  useEffect(() => {
    api.getBillingBalance().then((b: any) => setCreditBalance(b?.credit_balance ?? null)).catch(() => {})
  }, [])

  const orgs = user?.organizations || []
  const activeOrgId = localStorage.getItem('activeOrgId')
  const activeOrg = orgs.find((o: any) => o.id === activeOrgId)

  const navigation = [
    { name: 'Dashboard', href: '/app', icon: LayoutDashboard },
    { name: 'Projects', href: '/app/projects', icon: FolderKanban },
    { name: 'Repositories', href: '/app/repositories', icon: GitBranch },
    { name: 'Leads', href: '/app/leads', icon: UserCheck },
    { name: 'Jobs', href: '/app/jobs', icon: Briefcase },
    { name: 'separator', href: '', icon: Blocks },
    { name: 'Integrations', href: '/app/integrations', icon: Blocks },
    { name: 'Settings', href: '/app/settings', icon: Settings },
  ]

  const isActive = (href: string) => {
    if (href === '/app') {
      return location.pathname === '/app'
    }
    return location.pathname.startsWith(href)
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900 relative">
      <MatrixBackground />

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } relative z-10 bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl border-r border-gray-200/80 dark:border-gray-700/80 transition-all duration-300 flex flex-col`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200/80 dark:border-gray-700/80">
          <div className="flex items-center space-x-2.5 min-w-0">
            <NexusLogo size={28} className="flex-shrink-0" />
            {sidebarOpen && (
              <div className="min-w-0">
                <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-500 via-violet-500 to-cyan-500 bg-clip-text text-transparent leading-tight">
                  NexusLeads
                </h1>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>

        {/* Org switcher */}
        {activeOrg && sidebarOpen && (
          <div className="px-3 pt-3">
            {orgs.length > 1 ? (
              <div className="relative">
                <select
                  value={activeOrgId || ''}
                  onChange={(e) => {
                    localStorage.setItem('activeOrgId', e.target.value)
                    window.location.reload()
                  }}
                  className="w-full appearance-none bg-gray-100 dark:bg-gray-700/60 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 pr-8 text-sm text-gray-900 dark:text-gray-100 cursor-pointer"
                >
                  {orgs.map((o: any) => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </select>
                <ChevronsUpDown className="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                <Building2 className="w-4 h-4" />
                <span className="truncate">{activeOrg.name}</span>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navigation.map((item) => {
            if (item.name === 'separator') {
              return <div key="sep" className="my-2 border-t border-gray-200/60 dark:border-gray-700/60" />
            }
            const Icon = item.icon
            const active = isActive(item.href)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2 rounded-lg transition-all duration-150 ${
                  active
                    ? 'bg-gradient-to-r from-cyan-500/20 to-violet-500/20 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30 dark:border-cyan-400/20'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100/80 dark:hover:bg-gray-700/60'
                }`}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-cyan-600 dark:text-cyan-400' : ''}`} />
                {sidebarOpen && <span className="ml-3 text-sm font-medium">{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Credit Balance */}
        {creditBalance !== null && sidebarOpen && (
          <div className="mx-3 mb-1">
            <Link
              to="/app/settings"
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 dark:border-emerald-400/15 hover:border-emerald-500/40 transition-colors"
            >
              <Wallet className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">${creditBalance.toFixed(2)}</span>
              <span className="text-[10px] text-gray-500 dark:text-gray-400">credits</span>
            </Link>
          </div>
        )}
        {creditBalance !== null && !sidebarOpen && (
          <div className="mx-3 mb-1 flex justify-center">
            <Link
              to="/app/settings"
              className="p-2 rounded-lg bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 hover:border-emerald-500/40"
              title={`$${creditBalance.toFixed(2)} credits`}
            >
              <Wallet className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
            </Link>
          </div>
        )}

        {/* User section */}
        <div className="p-4 border-t border-gray-200/80 dark:border-gray-700/80 space-y-2">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center px-3 py-2 rounded-lg hover:bg-gray-100/80 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-300 transition-colors"
            title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            {sidebarOpen && (
              <span className="ml-3 text-sm">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
            )}
          </button>
          
          {/* User Info & Logout */}
          <div className="flex items-center justify-between pt-2">
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
              </div>
            )}
            <button
              onClick={logout}
              className="p-2 rounded-lg hover:bg-gray-100/80 dark:hover:bg-gray-700/60 text-gray-700 dark:text-gray-300 transition-colors"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto relative z-10">
        <Outlet />
      </main>

      {/* Chat Assistant */}
      <ChatSidecar />
    </div>
  )
}
