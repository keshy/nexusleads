import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Plus, Star, Users, Code, Play, Trash2, X, ExternalLink, Clock, FolderKanban, Sparkles, Globe } from 'lucide-react'
import { api } from '../lib/api'
import Toast from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

interface Source {
  id: string
  project_id: string
  source_type: string
  external_url: string
  github_url?: string
  full_name: string
  owner?: string
  repo_name?: string
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

const SOURCE_TYPE_LABELS: Record<string, string> = {
  github_repo: 'GitHub Repository',
  discord_server: 'Discord Server',
  reddit_subreddit: 'Reddit Subreddit',
  x_account: 'X / Twitter',
  stock_forum: 'Stock Forum',
  custom: 'Custom',
}

const SOURCE_TYPE_ICONS: Record<string, string> = {
  github_repo: '🐙',
  discord_server: '💬',
  reddit_subreddit: '📡',
  x_account: '𝕏',
  stock_forum: '📈',
  custom: '🔗',
}

const SOURCE_TYPE_PLACEHOLDERS: Record<string, string> = {
  github_repo: 'https://github.com/facebook/react',
  discord_server: 'https://discord.gg/invite-code',
  reddit_subreddit: 'https://reddit.com/r/programming',
  x_account: 'https://x.com/openai',
  stock_forum: 'https://stocktwits.com/symbol/AAPL',
  custom: 'https://community.example.com',
}

const SOURCE_TYPE_HINTS: Record<string, string> = {
  github_repo: 'Source type auto-detected from URL. Requires GITHUB_TOKEN in Settings.',
  discord_server: 'Connector coming soon. The source will be tracked; ingestion will start when the connector is available.',
  reddit_subreddit: 'Connector coming soon. The source will be tracked; ingestion will start when the connector is available.',
  x_account: 'Connector coming soon. The source will be tracked; ingestion will start when the connector is available.',
  stock_forum: 'Connector coming soon. The source will be tracked; ingestion will start when the connector is available.',
  custom: 'Custom source type. Connector support varies.',
}

function detectSourceType(url: string): string | null {
  const lower = url.toLowerCase()
  if (lower.includes('github.com')) return 'github_repo'
  if (lower.includes('discord.gg') || lower.includes('discord.com')) return 'discord_server'
  if (lower.includes('reddit.com/r/')) return 'reddit_subreddit'
  if (lower.includes('twitter.com') || lower.includes('x.com')) return 'x_account'
  if (lower.includes('stocktwits.com')) return 'stock_forum'
  return null
}

export default function Sources() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [sources, setSources] = useState<Source[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddDrawer, setShowAddDrawer] = useState(false)
  const [formData, setFormData] = useState({
    project_id: '',
    external_url: '',
    source_type: 'github_repo',
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
      const [sourcesData, projectsData] = await Promise.all([
        api.getSources(projectIdFilter || undefined),
        api.getProjects()
      ])
      setSources(sourcesData)
      setProjects(projectsData)
      
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
      await api.createSource(formData)
      setShowAddDrawer(false)
      setFormData({ project_id: '', external_url: '', source_type: 'github_repo', sourcing_interval: 'weekly' })
      fetchData()
      setToast({ message: 'Community source added successfully!', type: 'success' })
    } catch (error: any) {
      console.error('Error creating source:', error)
      setToast({ message: error.response?.data?.detail || 'Failed to create source', type: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const handleTriggerSourcing = async (sourceId: string) => {
    try {
      await api.triggerSourcing(sourceId)
      setToast({ message: 'Scan started! Check the Jobs page for progress.', type: 'success' })
      fetchData()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to start scan', type: 'error' })
    }
  }

  const handleAnalyzeStargazers = async (sourceId: string) => {
    try {
      await api.analyzeStargazers(sourceId)
      setToast({ message: 'Stargazer analysis started! Check the Jobs page for progress.', type: 'success' })
      fetchData()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to start stargazer analysis', type: 'error' })
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteSource(id)
      setDeleteConfirmId(null)
      fetchData()
      setToast({ message: 'Source deleted successfully', type: 'success' })
    } catch (error) {
      console.error('Error deleting source:', error)
      setToast({ message: 'Failed to delete source', type: 'error' })
    }
  }

  const getProjectName = (projectId: string) => {
    return projects.find(p => p.id === projectId)?.name || 'Unknown Project'
  }

  const filteredProject = projectIdFilter ? projects.find(p => p.id === projectIdFilter) : null

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading sources...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Community Sources</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {filteredProject ? `Sources in ${filteredProject.name}` : 'Connect community sources to discover members and potential leads'}
          </p>
        </div>
        <div className="flex space-x-3">
          {filteredProject && (
            <button
              onClick={() => navigate('/app/sources')}
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
            Add Source
          </button>
        </div>
      </div>

      {sources.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 p-8 mb-6">
            <Globe className="w-16 h-16 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            Connect Your First Community Source
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-2xl mb-8 leading-relaxed">
            Connect community sources like GitHub repositories, Discord servers, Reddit communities, and more to discover and source members as potential leads.
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mb-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Code className="w-10 h-10 text-blue-600 dark:text-blue-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Auto-Discovery</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Automatically find and analyze community members from any connected source
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Star className="w-10 h-10 text-yellow-600 dark:text-yellow-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Activity Tracking</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Monitor activity and member engagement across all connected sources
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Users className="w-10 h-10 text-purple-600 dark:text-purple-400 mb-3" />
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
            Add Your First Source
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sources.map((src) => (
            <div
              key={src.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg dark:hover:shadow-gray-900/50 transition-shadow flex flex-col"
            >
              {/* Header — fixed */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded-lg flex-shrink-0 text-xl">
                    {SOURCE_TYPE_ICONS[src.source_type] || '🔗'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">{src.full_name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{SOURCE_TYPE_LABELS[src.source_type] || src.source_type}</p>
                  </div>
                </div>
                <button
                  onClick={() => setDeleteConfirmId(src.id)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex-shrink-0 ml-2"
                  title="Delete source"
                >
                  <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                </button>
              </div>

              {deleteConfirmId === src.id && (
                <ConfirmDialog
                  title="Delete Source"
                  message="Are you sure you want to delete this source?"
                  onConfirm={() => handleDelete(src.id)}
                  onCancel={() => setDeleteConfirmId(null)}
                  confirmText="Yes, Delete Source"
                />
              )}

              {/* Body — flex-grow to push actions to bottom */}
              <div className="flex-1 flex flex-col">
                {/* Meta rows — fixed 3-row slot */}
                <div className="space-y-2 mb-3">
                  <div className="flex items-center text-sm text-gray-600 dark:text-gray-400 truncate">
                    <FolderKanban className="w-4 h-4 mr-2 flex-shrink-0" />
                    <span className="truncate">{getProjectName(src.project_id)}</span>
                  </div>
                  {src.external_url ? (
                    <a
                      href={src.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center text-sm text-primary hover:underline truncate"
                    >
                      <ExternalLink className="w-4 h-4 mr-2 flex-shrink-0" />
                      <span className="truncate">{src.external_url.replace(/^https?:\/\//, '')}</span>
                    </a>
                  ) : (
                    <div className="h-5" />
                  )}
                  <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                    <Clock className="w-4 h-4 mr-2 flex-shrink-0" />
                    Scan: {src.sourcing_interval}
                  </div>
                </div>

                {/* Last scanned — fixed slot */}
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4 min-h-[1rem]">
                  {src.last_sourced_at ? `Last scanned: ${new Date(src.last_sourced_at).toLocaleDateString()}` : 'Not yet scanned'}
                </p>

                {/* Actions — pinned to bottom */}
                <div className="flex gap-2 mt-auto">
                  <button
                    onClick={() => handleTriggerSourcing(src.id)}
                    className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg inline-flex items-center justify-center text-sm"
                    title="Run scan now"
                  >
                    <Play className="w-4 h-4 mr-1.5" />
                    Run Scan
                  </button>
                  {src.source_type === 'github_repo' && (
                    <button
                      onClick={() => handleAnalyzeStargazers(src.id)}
                      className="flex-1 px-4 py-2 border border-amber-400/60 dark:border-amber-500/40 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg inline-flex items-center justify-center text-sm"
                      title="Analyze who starred this repo to find leads"
                    >
                      <Sparkles className="w-4 h-4 mr-1.5" />
                      Stargazers
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Source Drawer */}
      {showAddDrawer && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowAddDrawer(false)} />
          <div className="absolute inset-y-0 right-0 max-w-md w-full bg-white dark:bg-gray-800 shadow-xl overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Add Community Source</h2>
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
                    Source Type
                  </label>
                  <select
                    value={formData.source_type}
                    onChange={(e) => setFormData({ ...formData, source_type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    {Object.entries(SOURCE_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    URL *
                  </label>
                  <input
                    type="url"
                    required
                    value={formData.external_url}
                    onChange={(e) => setFormData({ ...formData, external_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    placeholder={SOURCE_TYPE_PLACEHOLDERS[formData.source_type] || 'https://...'}
                    onBlur={(e) => {
                      const detected = detectSourceType(e.target.value)
                      if (detected && detected !== formData.source_type) {
                        setFormData(prev => ({ ...prev, source_type: detected }))
                      }
                    }}
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {SOURCE_TYPE_HINTS[formData.source_type] || 'Enter the full URL of the community source'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Scan Interval *
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
                    How often should we scan for new members?
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
                    {submitting ? 'Adding...' : 'Add Source'}
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
