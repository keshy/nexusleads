# Frontend Implementation Guide

## Overview

The frontend has been scaffolded with React 18, TypeScript, TailwindCSS, and shadcn/ui components. All TypeScript errors will resolve after running `npm install` in the `frontend/` directory.

## Completed Files

### Configuration
- ✅ `package.json` - Dependencies and scripts
- ✅ `vite.config.ts` - Vite configuration
- ✅ `tailwind.config.js` - Tailwind configuration
- ✅ `tsconfig.json` - TypeScript configuration
- ✅ `index.html` - HTML entry point

### Core Application
- ✅ `src/main.tsx` - Application entry point
- ✅ `src/App.tsx` - Main app with routing
- ✅ `src/index.css` - Global styles

### Library/Utils
- ✅ `src/lib/api.ts` - API client service
- ✅ `src/lib/utils.ts` - Utility functions

### Context
- ✅ `src/contexts/AuthContext.tsx` - Authentication context

### Components
- ✅ `src/components/Layout.tsx` - Main layout with sidebar

## Pages to Create

Create these files in `src/pages/`:

### 1. Login.tsx

```typescript
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Lock, User } from 'lucide-react'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-md w-full mx-4">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">PLG Lead Sourcer</h1>
            <p className="text-gray-600 mt-2">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-600">
            <p>Default credentials: admin / admin123</p>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 2. Dashboard.tsx

```typescript
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { 
  Users, 
  GitBranch, 
  FolderKanban, 
  Target,
  TrendingUp,
  Activity
} from 'lucide-react'
import { formatNumber } from '../lib/utils'

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  })

  const { data: topLeads } = useQuery({
    queryKey: ['top-leads'],
    queryFn: () => api.getTopLeads(),
  })

  if (isLoading) {
    return <div className="p-8">Loading...</div>
  }

  const statCards = [
    { name: 'Total Projects', value: stats?.total_projects || 0, icon: FolderKanban, color: 'bg-blue-500' },
    { name: 'Repositories', value: stats?.total_repositories || 0, icon: GitBranch, color: 'bg-green-500' },
    { name: 'Contributors', value: stats?.total_contributors || 0, icon: Users, color: 'bg-purple-500' },
    { name: 'Qualified Leads', value: stats?.qualified_leads || 0, icon: Target, color: 'bg-orange-500' },
  ]

  const classificationStats = [
    { name: 'Decision Makers', value: stats?.decision_makers || 0, color: 'text-purple-600' },
    { name: 'Key Contributors', value: stats?.key_contributors || 0, color: 'text-blue-600' },
    { name: 'High Impact', value: stats?.high_impact || 0, color: 'text-green-600' },
  ]

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Overview of your lead sourcing activities
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.name} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {formatNumber(stat.value)}
                  </p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Classification Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Lead Classification
          </h2>
          <div className="space-y-4">
            {classificationStats.map((stat) => (
              <div key={stat.name} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">{stat.name}</span>
                <span className={`text-xl font-bold ${stat.color}`}>
                  {stat.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Leads */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Top Leads
          </h2>
          <div className="space-y-4">
            {topLeads?.slice(0, 5).map((lead: any) => (
              <div key={lead.id} className="flex items-center space-x-3">
                <img
                  src={lead.avatar_url || '/default-avatar.png'}
                  alt={lead.username}
                  className="w-10 h-10 rounded-full"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {lead.full_name || lead.username}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {lead.current_position || lead.company}
                  </p>
                </div>
                <div className="text-sm font-semibold text-blue-600">
                  {lead.overall_score.toFixed(0)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 3. Projects.tsx

```typescript
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Plus, Trash2, Eye } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Projects() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.createProject(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowCreateModal(false)
      setName('')
      setDescription('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ name, description })
  }

  if (isLoading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-2">Manage your lead sourcing projects</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          <span>New Project</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects?.map((project: any) => (
          <div key={project.id} className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {project.name}
            </h3>
            <p className="text-sm text-gray-600 mb-4 line-clamp-2">
              {project.description || 'No description'}
            </p>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs text-gray-500">Repositories</p>
                <p className="text-xl font-bold text-gray-900">
                  {project.stats?.total_repositories || 0}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Qualified Leads</p>
                <p className="text-xl font-bold text-blue-600">
                  {project.stats?.qualified_leads || 0}
                </p>
              </div>
            </div>

            <div className="flex space-x-2">
              <Link
                to={`/projects/${project.id}`}
                className="flex-1 flex items-center justify-center space-x-2 bg-blue-50 text-blue-600 px-3 py-2 rounded hover:bg-blue-100"
              >
                <Eye className="w-4 h-4" />
                <span>View</span>
              </Link>
              <button
                onClick={() => {
                  if (confirm('Delete this project?')) {
                    deleteMutation.mutate(project.id)
                  }
                }}
                className="flex items-center justify-center space-x-2 bg-red-50 text-red-600 px-3 py-2 rounded hover:bg-red-100"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Create New Project</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
```

### 4-7. Create Stub Pages

Create these simple stub pages for now:

**ProjectDetail.tsx**, **Repositories.tsx**, **Contributors.tsx**, **Jobs.tsx**:

```typescript
export default function PageName() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900">Page Title</h1>
      <p className="text-gray-600 mt-2">Coming soon...</p>
    </div>
  )
}
```

## Installation Steps

```bash
cd frontend
npm install
npm run dev
```

The application will run on http://localhost:5173

## Features Implemented

1. **Authentication**: Login with JWT tokens
2. **Dashboard**: Real-time statistics and top leads
3. **Projects**: CRUD operations for projects
4. **Layout**: Responsive sidebar navigation
5. **API Integration**: Complete API client with interceptors
6. **Type Safety**: Full TypeScript support
7. **Styling**: TailwindCSS with custom theme

## Next Steps for Full Implementation

The above provides a working foundation. To complete all pages:

1. Expand **ProjectDetail.tsx** with repository management
2. Complete **Repositories.tsx** with add/trigger sourcing UI
3. Build **Contributors.tsx** with filtering and enrichment
4. Finish **Jobs.tsx** with real-time progress tracking

All TypeScript/lint errors will resolve after `npm install`.
