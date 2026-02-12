import { useState, useEffect } from 'react'
import { RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Pause, Play, GitBranch, Filter, X, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import Toast from '../components/Toast'
import ConfirmDialog from '../components/ConfirmDialog'

interface Job {
  id: string
  project_id?: string
  repository_id?: string
  job_type: string
  status: string
  total_steps: number
  current_step: number
  progress_percentage: number
  started_at?: string
  completed_at?: string
  error_message?: string
  created_at: string
  project_name?: string
  repository_name?: string
}

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [projects, setProjects] = useState<any[]>([])
  const [repositories, setRepositories] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [repositoryFilter, setRepositoryFilter] = useState<string>('all')
  const [selectedJob, setSelectedJob] = useState<any>(null)
  const [showDetailDrawer, setShowDetailDrawer] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [statusFilter, projectFilter, repositoryFilter])

  useEffect(() => {
    if (!autoRefresh) return
    
    const interval = setInterval(() => {
      fetchJobs()
    }, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [autoRefresh, statusFilter, projectFilter, repositoryFilter])

  const fetchData = async () => {
    try {
      const [projectsData, reposData] = await Promise.all([
        api.getProjects(),
        api.getRepositories()
      ])
      setProjects(projectsData)
      setRepositories(reposData)
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  const fetchJobs = async () => {
    try {
      const projFilter = projectFilter === 'all' ? undefined : projectFilter
      const repoFilter = repositoryFilter === 'all' ? undefined : repositoryFilter
      const statusFilt = statusFilter === 'all' ? undefined : statusFilter
      const data = await api.getJobs(projFilter, repoFilter, statusFilt)
      setJobs(data)
    } catch (error) {
      console.error('Error fetching jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
      case 'running':
        return <RefreshCw className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />
      case 'cancelled':
        return <AlertCircle className="w-5 h-5 text-gray-600 dark:text-gray-400" />
      default:
        return <Clock className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
      case 'failed':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
      case 'running':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200'
      case 'cancelled':
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
      default:
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200'
    }
  }

  const formatJobType = (type: string) => {
    return type.split('_').map((word: string) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
  }

  const getJobTitle = (job: Job) => {
    if (job.repository_name) {
      return job.repository_name
    }
    if (job.project_name) {
      return job.project_name
    }
    return formatJobType(job.job_type)
  }

  const formatDate = (date?: string) => {
    if (!date) return 'N/A'
    return new Date(date).toLocaleString()
  }

  const getDuration = (startedAt?: string, completedAt?: string) => {
    if (!startedAt) return null
    const end = completedAt ? new Date(completedAt) : new Date()
    const start = new Date(startedAt)
    const diffMs = end.getTime() - start.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    
    if (diffMin > 0) {
      return `${diffMin}m ${diffSec % 60}s`
    }
    return `${diffSec}s`
  }

  const openJobDetail = async (jobId: string) => {
    try {
      const data = await api.getJob(jobId)
      setSelectedJob(data)
      setShowDetailDrawer(true)
    } catch (error) {
      console.error('Error fetching job details:', error)
    }
  }

  const handleCancelJob = async (jobId: string, closeDrawer: boolean = true) => {
    try {
      await api.cancelJob(jobId)
      if (closeDrawer) {
        setShowDetailDrawer(false)
      }
      setShowDeleteConfirm(false)
      setDeleteConfirmId(null)
      setToast({ message: 'Job cancelled successfully', type: 'success' })
      fetchJobs()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to cancel job', type: 'error' })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading jobs...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Jobs</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">Track background sourcing, enrichment, and classification jobs in real time</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-4 py-2 rounded-lg inline-flex items-center ${
              autoRefresh
                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
            }`}
            title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
          >
            {autoRefresh ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
            Auto-refresh
          </button>
          <button
            onClick={fetchJobs}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg inline-flex items-center"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <Filter className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        
        <select
          value={projectFilter}
          onChange={(e: any) => setProjectFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
        >
          <option value="all">All Projects</option>
          {projects.map((p: any) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        
        <select
          value={repositoryFilter}
          onChange={(e: any) => setRepositoryFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
        >
          <option value="all">All Repositories</option>
          {repositories.map((r: any) => (
            <option key={r.id} value={r.id}>{r.full_name}</option>
          ))}
        </select>
        
        <select
          value={statusFilter}
          onChange={(e: any) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
        >
          <option value="all">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {jobs.length} {jobs.length === 1 ? 'job' : 'jobs'}
        </span>
      </div>

      {jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-purple-100 to-indigo-100 dark:from-purple-900/30 dark:to-indigo-900/30 p-8 mb-6">
            <Clock className="w-16 h-16 text-purple-600 dark:text-purple-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            No Jobs Found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-md">
            {statusFilter === 'all'
              ? 'No jobs have been created yet. Create a project and add repositories to start sourcing!'
              : `No ${statusFilter} jobs found.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <div 
                  className="flex items-start space-x-4 flex-1 cursor-pointer"
                  onClick={() => openJobDetail(job.id)}
                >
                  {getStatusIcon(job.status)}
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {getJobTitle(job)}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(job.status)}`}>
                        {job.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                      {formatJobType(job.job_type)}
                    </p>
                    <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                      {job.repository_id && (
                        <div className="inline-flex items-center">
                          <GitBranch className="w-4 h-4 mr-1" />
                          Repository Job
                        </div>
                      )}
                      <div>Created: {formatDate(job.created_at)}</div>
                      {job.started_at && (
                        <div>Duration: {getDuration(job.started_at, job.completed_at)}</div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Delete Button */}
                {(job.status === 'pending' || job.status === 'running') && deleteConfirmId !== job.id && (
                  <button
                    onClick={(e: any) => {
                      e.stopPropagation()
                      setDeleteConfirmId(job.id)
                    }}
                    className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors group"
                    title="Cancel job"
                  >
                    <Trash2 className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-red-600 dark:group-hover:text-red-400" />
                  </button>
                )}
              </div>

              {/* Delete Confirmation */}
              {deleteConfirmId === job.id && (
                <div onClick={(e: any) => e.stopPropagation()}>
                  <ConfirmDialog
                    title="Cancel Job"
                    message="Are you sure you want to cancel this job?"
                    onConfirm={() => handleCancelJob(job.id, false)}
                    onCancel={() => setDeleteConfirmId(null)}
                    confirmText="Yes, Cancel Job"
                  />
                </div>
              )}

              {/* Progress Bar */}
              {job.status === 'running' && (
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>Progress: {job.current_step} / {job.total_steps} steps</span>
                    <span>{Number(job.progress_percentage || 0).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${job.progress_percentage}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Message */}
              {job.error_message && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start space-x-2">
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">Error</p>
                      <p className="text-sm text-red-700 dark:text-red-300">{job.error_message}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Completion Info */}
              {job.completed_at && job.status === 'completed' && (
                <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                  ✓ Completed at {formatDate(job.completed_at)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Job Detail Drawer */}
      {showDetailDrawer && selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={() => setShowDetailDrawer(false)}>
          <div 
            className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white dark:bg-gray-900 shadow-xl overflow-y-auto"
            onClick={(e: any) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Job Details</h2>
                <div className="flex items-center space-x-2">
                  {(selectedJob.status === 'pending' || selectedJob.status === 'running') && !showDeleteConfirm && (
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
                    >
                      Cancel Job
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setShowDetailDrawer(false)
                      setShowDeleteConfirm(false)
                    }}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                  >
                    <X className="w-6 h-6 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>
              </div>

              {/* Delete Confirmation */}
              {showDeleteConfirm && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start space-x-3 mb-4">
                    <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                    <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">Cancel Job</p>
                    <p className="text-sm text-red-700 dark:text-red-300">
                        Are you sure you want to cancel this job?
                    </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleCancelJob(selectedJob.id)}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
                    >
                      Yes, Cancel Job
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-medium"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Job Header */}
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center space-x-3 mb-3">
                  {getStatusIcon(selectedJob.status)}
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {getJobTitle(selectedJob)}
                  </h3>
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(selectedJob.status)}`}>
                    {selectedJob.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  {formatJobType(selectedJob.job_type)}
                </p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Created:</span>
                    <span className="ml-2 text-gray-900 dark:text-gray-100">{formatDate(selectedJob.created_at)}</span>
                  </div>
                  {selectedJob.started_at && (
                    <div>
                      <span className="text-gray-500 dark:text-gray-400">Duration:</span>
                      <span className="ml-2 text-gray-900 dark:text-gray-100">{getDuration(selectedJob.started_at, selectedJob.completed_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {selectedJob.status === 'running' && (
                <div className="mb-6">
                  <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
                    <span>Overall Progress</span>
                    <span>{Number(selectedJob.progress_percentage || 0).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div
                      className="bg-blue-600 dark:bg-blue-500 h-3 rounded-full transition-all duration-300"
                      style={{ width: `${selectedJob.progress_percentage}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Message */}
              {selectedJob.error_message && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <XCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">Latest Error</p>
                      <p className="text-sm text-red-700 dark:text-red-300">{selectedJob.error_message}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Progress Steps */}
              {selectedJob.progress_steps && selectedJob.progress_steps.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Progress Steps</h3>
                  <div className="space-y-3">
                    {selectedJob.progress_steps.map((step: any, _index: number) => (
                      <div
                        key={step.id}
                        className="flex items-start space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex-shrink-0 mt-1">
                          {step.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />}
                          {step.status === 'running' && <RefreshCw className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />}
                          {step.status === 'failed' && <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />}
                          {step.status === 'pending' && <Clock className="w-5 h-5 text-gray-400 dark:text-gray-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              Step {step.step_number}: {step.step_name}
                            </span>
                            <span className={`px-2 py-0.5 text-xs rounded-full ${
                              step.status === 'completed' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' :
                              step.status === 'running' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200' :
                              step.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200' :
                              'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                            }`}>
                              {step.status}
                            </span>
                          </div>
                          {step.message && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{step.message}</p>
                          )}
                          {step.error_message && (
                            <p className="text-sm text-red-600 dark:text-red-400">{step.error_message}</p>
                          )}
                          <div className="flex items-center space-x-3 text-xs text-gray-500 dark:text-gray-500 mt-1">
                            {step.started_at && (
                              <span>Started: {new Date(step.started_at).toLocaleTimeString()}</span>
                            )}
                            {step.completed_at && (
                              <span>Completed: {new Date(step.completed_at).toLocaleTimeString()}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedJob.completed_at && selectedJob.status === 'completed' && (
                <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <span className="text-sm text-green-800 dark:text-green-200">
                      Job completed successfully at {formatDate(selectedJob.completed_at)}
                    </span>
                  </div>
                </div>
              )}
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
