import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { GitBranch, Plus, Star, GitFork, Code, Play, Trash2, X, ExternalLink, Clock, FolderKanban, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import Toast from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

interface Repository {
  id: string
  project_id: string
  github_url: string
  full_name: string
  owner: string
  repo_name: string
  sourcing_interval: string
  next_sourcing_at: string
  is_active: boolean
  last_sourced_at?: string
  created_at: string
}

interface Project {
  id: string
  name: string
}

export default function Repositories() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddDrawer, setShowAddDrawer] = useState(false)
  const [formData, setFormData] = useState({
    project_id: '',
    github_url: '',
    sourcing_interval: 'weekly' as 'daily' | 'weekly' | 'monthly'
  })
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const projectIdFilter = searchParams.get('project_id')

  useEffect(() => {
    fetchData()
  }, [projectIdFilter])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [reposData, projectsData] = await Promise.all([
        api.getRepositories(projectIdFilter || undefined),
        api.getProjects()
      ])
      setRepositories(reposData)
      setProjects(projectsData)
      
      // Pre-select project if filtering
      if (projectIdFilter && !formData.project_id) {
        setFormData(prev => ({ ...prev, project_id: projectIdFilter }))
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSubmitting(true)
      await api.createRepository(formData)
      setShowAddDrawer(false)
      setFormData({ project_id: '', github_url: '', sourcing_interval: 'weekly' })
      fetchData()
      setToast({ message: 'Repository added successfully!', type: 'success' })
    } catch (error: any) {
      console.error('Error creating repository:', error)
      setToast({ message: error.response?.data?.detail || 'Failed to create repository', type: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleTriggerSourcing = async (repoId: string) => {
    try {
      await api.triggerSourcing(repoId)
      setToast({ message: 'Sourcing job started! Check the Jobs page for progress.', type: 'success' })
      fetchData() // Refresh to update active jobs count
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to trigger sourcing', type: 'error' })
    }
  }

  const handleAnalyzeStargazers = async (repoId: string) => {
    try {
      await api.analyzeStargazers(repoId)
      setToast({ message: 'Stargazer analysis started! Check the Jobs page for progress.', type: 'success' })
      fetchData()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to start stargazer analysis', type: 'error' })
    }
  }

  const hasActiveJob = (_repoId: string): boolean => {
    // This would need actual job data, for now we rely on the backend check
    // The button will show error if job already exists
    return false
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteRepository(id)
      setDeleteConfirmId(null)
      fetchData()
      setToast({ message: 'Repository deleted successfully', type: 'success' })
    } catch (error) {
      console.error('Error deleting repository:', error)
      setToast({ message: 'Failed to delete repository', type: 'error' })
    }
  }

  const getProjectName = (projectId: string) => {
    return projects.find(p => p.id === projectId)?.name || 'Unknown Project'
  }

  const filteredProject = projectIdFilter ? projects.find(p => p.id === projectIdFilter) : null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading repositories...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Repositories</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {filteredProject ? `Repositories in ${filteredProject.name}` : 'Add GitHub repositories to discover contributors and stargazers as potential leads'}
          </p>
        </div>
        <div className="flex space-x-3">
          {filteredProject && (
            <button
              onClick={() => navigate('/app/repositories')}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Clear Filter
            </button>
          )}
          <button
            onClick={() => setShowAddDrawer(true)}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Repository
          </button>
        </div>
      </div>

      {repositories.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 p-8 mb-6">
            <GitBranch className="w-16 h-16 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            Connect Your First Repository
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-2xl mb-8 leading-relaxed">
            Connect GitHub repositories to discover and source contributors. Our system analyzes commit history,
            pull requests, and contributor activity to identify potential leads for your business.
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mb-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Code className="w-10 h-10 text-blue-600 dark:text-blue-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Auto-Discovery</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Automatically find and analyze contributors from any public GitHub repository
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Star className="w-10 h-10 text-yellow-600 dark:text-yellow-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Activity Tracking</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Monitor commits, PRs, and contributor engagement over time
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <GitFork className="w-10 h-10 text-purple-600 dark:text-purple-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Smart Sourcing</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Schedule automatic sourcing runs daily, weekly, or monthly
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAddDrawer(true)}
            className="px-6 py-3 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Your First Repository
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {repositories.map((repo) => (
            <div
              key={repo.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg dark:hover:shadow-gray-900/50 transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-lg flex-shrink-0">
                    <GitBranch className="w-6 h-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">{repo.repo_name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{repo.owner}</p>
                  </div>
                </div>
                <button
                  onClick={() => setDeleteConfirmId(repo.id)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex-shrink-0"
                  title="Delete repository"
                >
                  <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                </button>
              </div>

              {/* Delete Confirmation */}
              {deleteConfirmId === repo.id && (
                <ConfirmDialog
                  title="Delete Repository"
                  message="Are you sure you want to delete this repository?"
                  onConfirm={() => handleDelete(repo.id)}
                  onCancel={() => setDeleteConfirmId(null)}
                  confirmText="Yes, Delete Repository"
                />
              )}

              <div className="space-y-3 mb-4">
                <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                  <FolderKanban className="w-4 h-4 mr-2" />
                  {getProjectName(repo.project_id)}
                </div>
                <a
                  href={repo.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-sm text-primary hover:underline"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View on GitHub
                </a>
                <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                  <Clock className="w-4 h-4 mr-2" />
                  Sourcing: {repo.sourcing_interval}
                </div>
              </div>

              {repo.last_sourced_at && (
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  Last sourced: {new Date(repo.last_sourced_at).toLocaleDateString()}
                </p>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => handleTriggerSourcing(repo.id)}
                  disabled={hasActiveJob(repo.id)}
                  className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg inline-flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  title={hasActiveJob(repo.id) ? 'Sourcing already in progress' : 'Source contributors now'}
                >
                  <Play className="w-4 h-4 mr-1.5" />
                  Source
                </button>
                <button
                  onClick={() => handleAnalyzeStargazers(repo.id)}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-white rounded-lg inline-flex items-center justify-center text-sm"
                  title="Analyze who starred this repo to find leads"
                >
                  <Sparkles className="w-4 h-4 mr-1.5" />
                  Stargazers
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Repository Drawer */}
      {showAddDrawer && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowAddDrawer(false)} />
          <div className="absolute inset-y-0 right-0 max-w-md w-full bg-white dark:bg-gray-800 shadow-xl overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Add Repository</h2>
                <button
                  onClick={() => setShowAddDrawer(false)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Project *
                  </label>
                  <select
                    required
                    value={formData.project_id}
                    onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">Select a project</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>{project.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    GitHub URL *
                  </label>
                  <input
                    type="url"
                    required
                    value={formData.github_url}
                    onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    placeholder="https://github.com/facebook/react"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Enter the full GitHub repository URL
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Sourcing Interval *
                  </label>
                  <select
                    value={formData.sourcing_interval}
                    onChange={(e) => setFormData({ ...formData, sourcing_interval: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    How often should we check for new contributors?
                  </p>
                </div>

                <div className="flex space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowAddDrawer(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg disabled:opacity-50"
                  >
                    {submitting ? 'Adding...' : 'Add Repository'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  )
}
