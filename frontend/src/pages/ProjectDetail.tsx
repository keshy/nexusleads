import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { ExternalLink, GitBranch, Play, Tag, Trash2, Users } from 'lucide-react'
import Toast from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

interface Project {
  id: string
  name: string
  description?: string
  tags?: string[]
  external_urls?: string[]
  sourcing_context?: string
  stats: {
    total_repositories: number
    total_contributors: number
    qualified_leads: number
    active_jobs: number
  }
}

interface Repository {
  id: string
  github_url: string
  full_name: string
  repo_name: string
  owner: string
  sourcing_interval: string
  last_sourced_at?: string
}

interface Lead {
  id: string
  username: string
  full_name?: string
  avatar_url?: string
  overall_score?: number
  classification?: string
  current_position?: string
  current_company?: string
}

export default function ProjectDetail() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [topLeads, setTopLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)

  useEffect(() => {
    if (!projectId) return
    fetchData()
  }, [projectId])

  const fetchData = async () => {
    if (!projectId) return
    try {
      setLoading(true)
      const [projectData, reposData, leadsData] = await Promise.all([
        api.getProject(projectId),
        api.getRepositories(projectId),
        api.getTopLeads(projectId)
      ])
      setProject(projectData)
      setRepositories(reposData)
      setTopLeads(leadsData || [])
    } catch (error) {
      console.error('Error fetching project data:', error)
      setToast({ message: 'Failed to load project details', type: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const handleSourceProject = async () => {
    if (!projectId) return
    try {
      const result = await api.triggerProjectSourcing(projectId)
      if (result.jobs_created === 0) {
        setToast({ message: `All ${result.total_repositories} repositories are already being sourced.`, type: 'info' })
      } else if (result.jobs_created === result.total_repositories) {
        setToast({ message: `Started sourcing ${result.jobs_created} repositories!`, type: 'success' })
      } else {
        setToast({ message: `Started sourcing ${result.jobs_created} of ${result.total_repositories} repositories.`, type: 'info' })
      }
      fetchData()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to trigger sourcing', type: 'error' })
    }
  }

  const handleDeleteProject = async () => {
    if (!projectId) return
    try {
      await api.deleteProject(projectId)
      navigate('/app/projects')
    } catch (error) {
      setToast({ message: 'Failed to delete project', type: 'error' })
    }
  }

  const handleTriggerSourcing = async (repoId: string) => {
    try {
      await api.triggerSourcing(repoId)
      setToast({ message: 'Sourcing job started! Check Jobs for progress.', type: 'success' })
      fetchData()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to start sourcing', type: 'error' })
    }
  }

  const handleDeleteRepo = async (repoId: string) => {
    try {
      await api.deleteRepository(repoId)
      setToast({ message: 'Repository deleted successfully', type: 'success' })
      fetchData()
    } catch (error) {
      setToast({ message: 'Failed to delete repository', type: 'error' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading project...</div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Project not found</h1>
        <button
          onClick={() => navigate('/app/projects')}
          className="mt-4 px-4 py-2 bg-primary text-white rounded-lg"
        >
          Back to Projects
        </button>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{project.name}</h1>
          {project.description && (
            <p className="text-gray-600 dark:text-gray-400 mt-2">{project.description}</p>
          )}
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleSourceProject}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg inline-flex items-center"
          >
            <Play className="w-4 h-4 mr-2" />
            Source All
          </button>
          {!showDeleteConfirm && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {showDeleteConfirm && (
        <ConfirmDialog
          title="Delete Project"
          message="Are you sure you want to delete this project? This will also delete all associated repositories and data."
          onConfirm={handleDeleteProject}
          onCancel={() => setShowDeleteConfirm(false)}
          confirmText="Yes, Delete Project"
        />
      )}

      {project.tags && project.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {project.tags.map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
            >
              <Tag className="w-3 h-3 mr-1" />
              {tag}
            </span>
          ))}
        </div>
      )}

      {project.external_urls && project.external_urls.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">External URLs</h3>
          {project.external_urls.map((url, idx) => (
            <a
              key={idx}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-sm text-primary hover:underline"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              {url}
            </a>
          ))}
        </div>
      )}

      {project.sourcing_context && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Sourcing Context</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{project.sourcing_context}</p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.total_repositories}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Repositories</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.total_contributors}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Contributors</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.qualified_leads}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Qualified Leads</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.active_jobs}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Active Jobs</div>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Repositories</h2>
        {repositories.length === 0 ? (
          <div className="text-gray-600 dark:text-gray-400">No repositories added yet.</div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repositories.map((repo) => (
              <div key={repo.id} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">{repo.repo_name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{repo.owner}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteRepo(repo.id)}
                    className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    title="Delete repository"
                  >
                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </button>
                </div>
                <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center">
                    <GitBranch className="w-4 h-4 mr-2" />
                    {repo.full_name}
                  </div>
                  {repo.last_sourced_at && (
                    <div>Last sourced: {new Date(repo.last_sourced_at).toLocaleDateString()}</div>
                  )}
                  <div>Sourcing: {repo.sourcing_interval}</div>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <a
                    href={repo.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center"
                  >
                    View GitHub <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                  <button
                    onClick={() => handleTriggerSourcing(repo.id)}
                    className="px-3 py-1 bg-primary hover:bg-primary/90 text-white rounded-lg inline-flex items-center text-sm"
                  >
                    <Play className="w-3 h-3 mr-1" />
                    Source
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center">
          <Users className="w-5 h-5 mr-2" />
          Top Leads
        </h2>
        {topLeads.length === 0 ? (
          <div className="text-gray-600 dark:text-gray-400">No leads yet. Run sourcing to discover contributors.</div>
        ) : (
          <div className="space-y-3">
            {topLeads.slice(0, 10).map((lead) => (
              <div key={lead.id} className="flex items-center space-x-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <img
                  src={lead.avatar_url || '/default-avatar.png'}
                  alt={lead.username}
                  className="w-10 h-10 rounded-full"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {lead.full_name || lead.username}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                    {lead.current_position || lead.current_company || 'Contributor'}
                  </p>
                </div>
                {lead.overall_score !== undefined && (
                  <div className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    {lead.overall_score.toFixed(0)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

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
