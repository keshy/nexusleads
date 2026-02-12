import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiClient {
  private client: AxiosInstance
  private isRefreshing = false
  private failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add auth token and org header to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      const orgId = localStorage.getItem('activeOrgId')
      if (orgId) {
        config.headers['X-Org-Id'] = orgId
      }
      return config
    })

    // Handle auth errors with automatic token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

        if (error.response?.status === 401 && !originalRequest._retry) {
          const refreshToken = localStorage.getItem('refresh_token')

          if (!refreshToken) {
            this.clearTokens()
            window.location.href = '/login'
            return Promise.reject(error)
          }

          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject })
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`
              return this.client(originalRequest)
            })
          }

          originalRequest._retry = true
          this.isRefreshing = true

          try {
            const response = await axios.post(`${API_URL}/api/auth/refresh`, {
              refresh_token: refreshToken,
            })
            const { access_token, refresh_token: newRefresh } = response.data
            localStorage.setItem('token', access_token)
            localStorage.setItem('refresh_token', newRefresh)

            this.failedQueue.forEach(({ resolve }) => resolve(access_token))
            this.failedQueue = []

            originalRequest.headers.Authorization = `Bearer ${access_token}`
            return this.client(originalRequest)
          } catch (refreshError) {
            this.failedQueue.forEach(({ reject }) => reject(refreshError))
            this.failedQueue = []
            this.clearTokens()
            window.location.href = '/login'
            return Promise.reject(refreshError)
          } finally {
            this.isRefreshing = false
          }
        }

        return Promise.reject(error)
      }
    )
  }

  private clearTokens() {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }

  // Auth
  async login(username: string, password: string) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    
    const response = await this.client.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  async register(data: { username: string; email: string; password: string; full_name?: string }) {
    const response = await this.client.post('/api/auth/register', data)
    return response.data
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/auth/me')
    return response.data
  }

  // Projects
  async getProjects() {
    const response = await this.client.get('/api/projects')
    return response.data
  }

  async getProject(id: string) {
    const response = await this.client.get(`/api/projects/${id}`)
    return response.data
  }

  async createProject(data: { 
    name: string; 
    description?: string;
    tags?: string[];
    external_urls?: string[];
    sourcing_context?: string;
  }) {
    const response = await this.client.post('/api/projects', data)
    return response.data
  }

  async updateProject(id: string, data: any) {
    const response = await this.client.put(`/api/projects/${id}`, data)
    return response.data
  }

  async deleteProject(id: string) {
    await this.client.delete(`/api/projects/${id}`)
  }

  async triggerProjectSourcing(id: string) {
    const response = await this.client.post(`/api/projects/${id}/source-all`)
    return response.data
  }

  // Repositories
  async getRepositories(projectId?: string) {
    const params = projectId ? { project_id: projectId } : {}
    const response = await this.client.get('/api/repositories', { params })
    return response.data
  }

  async createRepository(data: { project_id: string; github_url: string; sourcing_interval: string }) {
    const response = await this.client.post('/api/repositories', data)
    return response.data
  }

  async triggerSourcing(repositoryId: string) {
    const response = await this.client.post(`/api/repositories/${repositoryId}/source-now`)
    return response.data
  }

  async analyzeStargazers(repositoryId: string) {
    const response = await this.client.post(`/api/repositories/${repositoryId}/analyze-stargazers`)
    return response.data
  }

  async deleteRepository(id: string) {
    await this.client.delete(`/api/repositories/${id}`)
  }

  // Contributors
  async getContributors(params?: {
    project_id?: string
    repository_id?: string
    classification?: string
    qualified_only?: boolean
  }) {
    const response = await this.client.get('/api/contributors', { params })
    return response.data
  }

  async getContributor(id: string, projectId?: string) {
    const params = projectId ? { project_id: projectId } : {}
    const response = await this.client.get(`/api/contributors/${id}`, { params })
    return response.data
  }

  async enrichContributor(id: string) {
    const response = await this.client.post(`/api/contributors/${id}/enrich`)
    return response.data
  }

  // Jobs
  async getJobs(projectId?: string, repositoryId?: string, statusFilter?: string) {
    const params: any = {}
    if (projectId) params.project_id = projectId
    if (repositoryId) params.repository_id = repositoryId
    if (statusFilter) params.status_filter = statusFilter
    const response = await this.client.get('/api/jobs', { params })
    return response.data
  }

  async getJob(id: string) {
    const response = await this.client.get(`/api/jobs/${id}`)
    return response.data
  }

  async cancelJob(id: string) {
    const response = await this.client.post(`/api/jobs/${id}/cancel`)
    return response.data
  }

  async getJobStats() {
    const response = await this.client.get('/api/jobs/stats/summary')
    return response.data
  }

  // Dashboard
  async getDashboardStats() {
    const response = await this.client.get('/api/dashboard/stats')
    return response.data
  }

  async getRepositoryStats(projectId?: string) {
    const params = projectId ? { project_id: projectId } : {}
    const response = await this.client.get('/api/dashboard/repositories/stats', { params })
    return response.data
  }

  async getRecentActivity() {
    const response = await this.client.get('/api/dashboard/recent-activity')
    return response.data
  }

  async getTopLeads(projectId?: string, source?: string) {
    const params: Record<string, string> = {}
    if (projectId) params.project_id = projectId
    if (source) params.source = source
    const response = await this.client.get('/api/dashboard/top-leads', { params })
    return response.data
  }

  // Users
  async getUsers() {
    const response = await this.client.get('/api/users')
    return response.data
  }

  async createUser(data: { username: string; email: string; password: string; full_name?: string }) {
    const response = await this.client.post('/api/users', data)
    return response.data
  }

  async updateUserProfile(data: { email?: string; full_name?: string; password?: string }) {
    const response = await this.client.put('/api/users/me', data)
    return response.data
  }

  async deleteUser(id: string) {
    await this.client.delete(`/api/users/${id}`)
  }

  // Leads
  async getLeadsByProject(source?: string) {
    const params: Record<string, string> = {}
    if (source) params.source = source
    const response = await this.client.get('/api/leads/by-project', { params })
    return response.data
  }

  // Settings
  async getSettings() {
    const response = await this.client.get('/api/settings')
    return response.data
  }

  async updateSetting(key: string, value: string) {
    const response = await this.client.put('/api/settings', { key, value })
    return response.data
  }

  async deleteSetting(key: string) {
    const response = await this.client.delete(`/api/settings/${key}`)
    return response.data
  }

  // Similar repos
  async searchSimilarRepos(query: string, limit: number = 10) {
    const response = await this.client.post('/api/repositories/similar', { query, limit })
    return response.data
  }

  // Organizations
  async getOrganizations() {
    const response = await this.client.get('/api/organizations')
    return response.data
  }

  async createOrganization(name: string) {
    const response = await this.client.post('/api/organizations', { name })
    return response.data
  }

  async getOrgMembers(orgId: string) {
    const response = await this.client.get(`/api/organizations/${orgId}/members`)
    return response.data
  }

  async addOrgMember(orgId: string, email: string, role?: string) {
    const response = await this.client.post(`/api/organizations/${orgId}/members`, { email, role })
    return response.data
  }

  async removeOrgMember(orgId: string, memberId: string) {
    await this.client.delete(`/api/organizations/${orgId}/members/${memberId}`)
  }

  // Integrations – Clay
  async getClayConfig() {
    const response = await this.client.get('/api/integrations/clay/config')
    return response.data
  }

  async updateClayConfig(webhookUrl: string) {
    const response = await this.client.put('/api/integrations/clay/config', { webhook_url: webhookUrl })
    return response.data
  }

  async testClayWebhook() {
    const response = await this.client.post('/api/integrations/clay/test')
    return response.data
  }

  async getClayActivity(limit: number = 50) {
    const response = await this.client.get('/api/integrations/clay/activity', { params: { limit } })
    return response.data
  }

  async getClayStats() {
    const response = await this.client.get('/api/integrations/clay/stats')
    return response.data
  }

  async pushLeadsToClay(contributorIds: string[], projectId?: string) {
    const response = await this.client.post('/api/integrations/clay/push', {
      contributor_ids: contributorIds,
      project_id: projectId,
    })
    return response.data
  }

  // Billing
  async getBillingBalance() {
    const response = await this.client.get('/api/billing/balance')
    return response.data
  }

  async getBillingTransactions(limit?: number, offset?: number) {
    const response = await this.client.get('/api/billing/transactions', { params: { limit, offset } })
    return response.data
  }

  async getBillingUsage() {
    const response = await this.client.get('/api/billing/usage')
    return response.data
  }

  async updateAutoReload(data: { enabled?: boolean; threshold?: number; amount?: number }) {
    const response = await this.client.put('/api/billing/auto-reload', data)
    return response.data
  }

  // Chat conversations
  async getChatConversations() {
    const response = await this.client.get('/api/chat/conversations')
    return response.data
  }

  async getChatConversation(id: string, _orgId?: string) {
    const response = await this.client.get(`/api/chat/conversations/${id}`)
    return response.data
  }

  async createChatConversation(data: { title?: string; messages?: any[] }, _orgId?: string) {
    const response = await this.client.post('/api/chat/conversations', data)
    return response.data
  }

  async updateChatConversation(id: string, data: { title?: string; messages?: any[] }, _orgId?: string) {
    const response = await this.client.put(`/api/chat/conversations/${id}`, data)
    return response.data
  }

  async deleteChatConversation(id: string, _orgId?: string) {
    await this.client.delete(`/api/chat/conversations/${id}`)
  }

  // Aliases used by ChatSidecar (orgId sent via header, param kept for compat)
  async listChatConversations(_orgId?: string) {
    return this.getChatConversations()
  }
}

export const api = new ApiClient()
