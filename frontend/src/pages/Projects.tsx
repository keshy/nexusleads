import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderKanban, Plus, GitBranch, Target, X, Trash2, ExternalLink, Tag, Play } from 'lucide-react'
import { api } from '../lib/api'
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

interface RepoForm {
  github_url: string
  sourcing_interval: 'daily' | 'weekly' | 'monthly'
}

export default function Projects() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [showDetailDrawer, setShowDetailDrawer] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tags: '',
    external_urls: '',
    sourcing_context: ''
  })
  const [repositories, setRepositories] = useState<RepoForm[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [showDrawerDeleteConfirm, setShowDrawerDeleteConfirm] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const data = await api.getProjects()
      setProjects(data)
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSubmitting(true)
      const projectData = {
        name: formData.name,
        description: formData.description || undefined,
        tags: formData.tags ? formData.tags.split(',').map(t => t.trim()).filter(t => t) : undefined,
        external_urls: formData.external_urls ? formData.external_urls.split('\n').map(u => u.trim()).filter(u => u) : undefined,
        sourcing_context: formData.sourcing_context || undefined
      }
      
      const newProject = await api.createProject(projectData)
      
      // Create repositories if any were added
      if (repositories.length > 0) {
        for (const repo of repositories) {
          try {
            await api.createRepository({
              project_id: newProject.id,
              github_url: repo.github_url,
              sourcing_interval: repo.sourcing_interval
            })
          } catch (repoError) {
            console.error('Error creating repository:', repoError)
          }
        }
      }
      
      setShowCreateModal(false)
      setFormData({ name: '', description: '', tags: '', external_urls: '', sourcing_context: '' })
      setRepositories([])
      fetchProjects()
      setToast({ message: 'Project created successfully!', type: 'success' })
    } catch (error: any) {
      console.error('Error creating project:', error)
      setToast({ message: error.response?.data?.detail || 'Failed to create project', type: 'error' })
    } finally {
      setSubmitting(false)
    }
  }

  const addRepository = () => {
    setRepositories([...repositories, { github_url: '', sourcing_interval: 'weekly' }])
  }

  const removeRepository = (index: number) => {
    setRepositories(repositories.filter((_, i) => i !== index))
  }

  const updateRepository = (index: number, field: keyof RepoForm, value: string) => {
    const updated = [...repositories]
    updated[index] = { ...updated[index], [field]: value }
    setRepositories(updated)
  }

  const openProjectDetail = async (project: Project) => {
    setSelectedProject(project)
    setShowDetailDrawer(true)
  }

  const handleSourceProject = async (id: string) => {
    try {
      const result = await api.triggerProjectSourcing(id)
      
      if (result.jobs_created === 0) {
        setToast({ message: `All ${result.total_repositories} repositories are already being sourced. Check the Jobs page for progress.`, type: 'info' })
      } else if (result.jobs_created === result.total_repositories) {
        setToast({ message: `Started sourcing ${result.jobs_created} repositories! Check the Jobs page for progress.`, type: 'success' })
      } else {
        setToast({ message: `Started sourcing ${result.jobs_created} of ${result.total_repositories} repositories. ${result.total_repositories - result.jobs_created} already in progress.`, type: 'info' })
      }
      
      setShowDetailDrawer(false)
      fetchProjects() // Refresh to update stats
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to trigger sourcing', type: 'error' })
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await api.deleteProject(id)
      setDeleteConfirmId(null)
      setShowDrawerDeleteConfirm(false)
      setShowDetailDrawer(false)
      fetchProjects()
      setToast({ message: 'Project deleted successfully', type: 'success' })
    } catch (error) {
      console.error('Error deleting project:', error)
      setToast({ message: 'Failed to delete project', type: 'error' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading projects...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Projects</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Organize repositories into projects to track and source leads by campaign or product area</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
        >
          <Plus className="w-5 h-5 mr-2" />
          New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/30 dark:to-indigo-900/30 p-8 mb-6">
            <FolderKanban className="w-16 h-16 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            Create Your First Project
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-2xl mb-8 leading-relaxed">
            Projects help you organize your lead sourcing efforts. Each project can contain multiple GitHub repositories,
            custom URLs, tags, and specific sourcing criteria to find the right leads for your business.
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mb-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <FolderKanban className="w-10 h-10 text-blue-600 dark:text-blue-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Organize Sources</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Group related repositories and sources together by project or campaign
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <GitBranch className="w-10 h-10 text-green-600 dark:text-green-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Track Repositories</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Add GitHub repos, external URLs, and custom tags to each project
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Target className="w-10 h-10 text-purple-600 dark:text-purple-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Define Criteria</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Set sourcing context to guide AI in finding your ideal leads
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
          >
            <Plus className="w-5 h-5 mr-2" />
            Create Your First Project
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg dark:hover:shadow-gray-900/50 transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div 
                  className="flex items-center space-x-3 flex-1 cursor-pointer"
                  onClick={() => openProjectDetail(project)}
                >
                  <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded-lg">
                    <FolderKanban className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{project.name}</h3>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleSourceProject(project.id)
                    }}
                    className="p-1 hover:bg-green-100 dark:hover:bg-green-900/30 rounded"
                    title="Source all repositories"
                  >
                    <Play className="w-4 h-4 text-green-600 dark:text-green-400" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteConfirmId(project.id)
                    }}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    title="Delete project"
                  >
                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </button>
                </div>
              </div>

              {/* Delete Confirmation */}
              {deleteConfirmId === project.id && (
                <div onClick={(e) => e.stopPropagation()}>
                  <ConfirmDialog
                    title="Delete Project"
                    message="Are you sure you want to delete this project? This will also delete all associated repositories and data."
                    onConfirm={() => handleDelete(project.id)}
                    onCancel={() => setDeleteConfirmId(null)}
                    confirmText="Yes, Delete Project"
                  />
                </div>
              )}

              <div onClick={() => openProjectDetail(project)} className="cursor-pointer">
                {project.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">{project.description}</p>
                )}
              </div>

              <div onClick={() => openProjectDetail(project)} className="cursor-pointer">
                {project.tags && project.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {project.tags.slice(0, 3).map((tag, idx) => (
                      <span key={idx} className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                        <Tag className="w-3 h-3 mr-1" />
                        {tag}
                      </span>
                    ))}
                    {project.tags.length > 3 && (
                      <span className="text-xs text-gray-500">+{project.tags.length - 3} more</span>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div>
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.total_repositories}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Repositories</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{project.stats.qualified_leads}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Qualified Leads</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Create New Project</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder="My Lead Sourcing Project"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder="What is this project about?"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder="enterprise, SaaS, developers"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  External URLs (one per line)
                </label>
                <textarea
                  value={formData.external_urls}
                  onChange={(e) => setFormData({ ...formData, external_urls: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder="https://example.com\nhttps://docs.example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Sourcing Context
                </label>
                <textarea
                  value={formData.sourcing_context}
                  onChange={(e) => setFormData({ ...formData, sourcing_context: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  placeholder="What should we look for? E.g., Senior developers with 5+ years experience, CTOs at B2B SaaS companies..."
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  This context helps AI classify and score leads more accurately
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Repositories
                  </label>
                  <button
                    type="button"
                    onClick={addRepository}
                    className="text-sm text-primary hover:text-primary/80 inline-flex items-center"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add Repository
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                  Add GitHub repositories to this project for lead sourcing
                </p>
                {repositories.map((repo, index) => (
                  <div key={index} className="flex gap-2 mb-2 items-start">
                    <input
                      type="url"
                      value={repo.github_url}
                      onChange={(e) => updateRepository(index, 'github_url', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
                      placeholder="https://github.com/owner/repo"
                    />
                    <select
                      value={repo.sourcing_interval}
                      onChange={(e) => updateRepository(index, 'sourcing_interval', e.target.value)}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => removeRepository(index)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setRepositories([])
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Project Detail Drawer */}
      {showDetailDrawer && selectedProject && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowDetailDrawer(false)} />
          <div className="absolute inset-y-0 right-0 max-w-2xl w-full bg-white dark:bg-gray-800 shadow-xl overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">{selectedProject.name}</h2>
                <button
                  onClick={() => setShowDetailDrawer(false)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {selectedProject.description && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Description</h3>
                  <p className="text-gray-600 dark:text-gray-400">{selectedProject.description}</p>
                </div>
              )}

              {selectedProject.tags && selectedProject.tags.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedProject.tags.map((tag, idx) => (
                      <span key={idx} className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                        <Tag className="w-3 h-3 mr-1" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedProject.external_urls && selectedProject.external_urls.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">External URLs</h3>
                  <div className="space-y-2">
                    {selectedProject.external_urls.map((url, idx) => (
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
                </div>
              )}

              {selectedProject.sourcing_context && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Sourcing Context</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{selectedProject.sourcing_context}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{selectedProject.stats.total_repositories}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Repositories</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{selectedProject.stats.qualified_leads}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Qualified Leads</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{selectedProject.stats.total_contributors}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Contributors</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{selectedProject.stats.active_jobs}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Active Jobs</div>
                </div>
              </div>

              {/* Delete Confirmation in Drawer */}
              {showDrawerDeleteConfirm && (
                <ConfirmDialog
                  title="Delete Project"
                  message="Are you sure you want to delete this project? This will also delete all associated repositories and data."
                  onConfirm={() => handleDelete(selectedProject.id)}
                  onCancel={() => setShowDrawerDeleteConfirm(false)}
                  confirmText="Yes, Delete Project"
                />
              )}

              <div className="space-y-3">
                <button
                  onClick={() => handleSourceProject(selectedProject.id)}
                  className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg inline-flex items-center justify-center"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Source All Repositories Now
                </button>
                
                <div className="flex space-x-3">
                  <button
                    onClick={() => {
                      setShowDetailDrawer(false)
                      navigate(`/app/repositories?project_id=${selectedProject.id}`)
                    }}
                    className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg inline-flex items-center justify-center"
                  >
                    <GitBranch className="w-5 h-5 mr-2" />
                    View Repositories
                  </button>
                  {!showDrawerDeleteConfirm && (
                    <button
                      onClick={() => setShowDrawerDeleteConfirm(true)}
                      className="px-4 py-2 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
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
