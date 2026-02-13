import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight, ExternalLink, Mail, Building2, UserCheck, FolderKanban, Info, Filter, Factory, X, Sparkles, GitCommitHorizontal, Send, Download, Loader2, Cloud, Blocks } from 'lucide-react'
import Toast from '../components/Toast'
import ScoreTooltip from '../components/ScoreTooltip'
import StyledSelect from '../components/StyledSelect'
import { api } from '../lib/api'

interface Lead {
  id: string
  full_name: string
  username: string
  email?: string
  avatar_url: string
  company?: string
  bio?: string
  current_company?: string
  current_position?: string
  industry?: string
  linkedin_url?: string
  linkedin_profile_photo_url?: string
  classification?: string
  classification_reasoning?: string
  overall_score?: number
  activity_score: number
  influence_score: number
  position_score: number
  engagement_score: number
  source?: string
  clay_pushed_at?: string
}

interface Project {
  id: string
  name: string
  description?: string
  leads: Lead[]
  contributors: Lead[]
}

export default function Leads() {
  const [projects, setProjects] = useState<Project[]>([])
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [expandedReasoning, setExpandedReasoning] = useState<Set<string>>(new Set())
  const [expandedContributors, setExpandedContributors] = useState<Set<string>>(new Set())
  const [filterClassification, setFilterClassification] = useState<string>('')
  const [filterIndustry, setFilterIndustry] = useState<string>('')
  const [filterCompany, setFilterCompany] = useState<string>('')
  const [filterSource, setFilterSource] = useState<string>('')
  const [selectedLeads, setSelectedLeads] = useState<Set<string>>(new Set())
  const [pushing, setPushing] = useState(false)
  const [pushingLeadId, setPushingLeadId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)
  const [clayConfigured, setClayConfigured] = useState<boolean | null>(null)
  const [showPushConfirm, setShowPushConfirm] = useState(false)

  useEffect(() => {
    fetchLeadsByProject()
    api.getClayConfig().then((c: any) => setClayConfigured(c?.connected || false)).catch(() => setClayConfigured(false))
  }, [filterSource])

  const fetchLeadsByProject = async () => {
    try {
      setLoading(true)
      const data = await api.getLeadsByProject(filterSource || undefined)
      setProjects(data)
      // Expand first project by default
      if (data.length > 0) {
        setExpandedProjects(new Set([data[0].id]))
      }
    } catch (error) {
      console.error('Error fetching leads:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleProject = (projectId: string) => {
    setExpandedProjects(prev => {
      const newSet = new Set(prev)
      if (newSet.has(projectId)) {
        newSet.delete(projectId)
      } else {
        newSet.add(projectId)
      }
      return newSet
    })
  }

  const toggleSelectLead = (leadId: string) => {
    setSelectedLeads(prev => {
      const s = new Set(prev)
      s.has(leadId) ? s.delete(leadId) : s.add(leadId)
      return s
    })
  }

  const toggleSelectAllInProject = (projectId: string) => {
    const proj = projects.find(p => p.id === projectId)
    if (!proj) return
    const filtered = filterLeads(proj.leads)
    const allSelected = filtered.every(l => selectedLeads.has(l.id))
    setSelectedLeads(prev => {
      const s = new Set(prev)
      filtered.forEach(l => allSelected ? s.delete(l.id) : s.add(l.id))
      return s
    })
  }

  const handleBulkPushClay = async () => {
    if (selectedLeads.size === 0) return
    setShowPushConfirm(true)
  }

  const confirmBulkPush = async () => {
    setShowPushConfirm(false)
    setPushing(true)
    try {
      const ids = Array.from(selectedLeads)
      await api.pushLeadsToClay(ids)
      setToast({ message: `Pushed ${ids.length} leads to Clay`, type: 'success' })
      setSelectedLeads(new Set())
      fetchLeadsByProject()
    } catch (err: any) {
      setToast({ message: err?.response?.data?.detail || 'Failed to push to Clay', type: 'error' })
    } finally {
      setPushing(false)
    }
  }

  const handleSinglePushClay = async (leadId: string) => {
    setPushingLeadId(leadId)
    try {
      await api.pushLeadsToClay([leadId])
      setToast({ message: 'Lead pushed to Clay', type: 'success' })
      fetchLeadsByProject()
    } catch (err: any) {
      setToast({ message: err?.response?.data?.detail || 'Failed to push to Clay', type: 'error' })
    } finally {
      setPushingLeadId(null)
    }
  }

  const handleExportCSV = () => {
    const selected = allLeads.filter(l => selectedLeads.has(l.id))
    if (selected.length === 0) return
    const headers = ['Name', 'Username', 'Email', 'Company', 'Position', 'Industry', 'Classification', 'Score', 'LinkedIn', 'GitHub']
    const rows = selected.map(l => [
      l.full_name || '', l.username, l.email || '', l.current_company || l.company || '',
      l.current_position || '', l.industry || '', l.classification || '',
      l.overall_score?.toFixed(0) || '', l.linkedin_url || '', `https://github.com/${l.username}`
    ])
    const csv = [headers, ...rows].map(r => r.map(c => `"${(c || '').replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nexusleads-export-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    setToast({ message: `Exported ${selected.length} leads to CSV`, type: 'success' })
  }

  const toggleReasoning = (leadId: string) => {
    setExpandedReasoning(prev => {
      const newSet = new Set(prev)
      if (newSet.has(leadId)) {
        newSet.delete(leadId)
      } else {
        newSet.add(leadId)
      }
      return newSet
    })
  }

  // Collect unique filter values
  const allLeads = useMemo(() => projects.flatMap(p => p.leads), [projects])
  const industries = useMemo(() => [...new Set(allLeads.map(l => l.industry).filter(Boolean))].sort() as string[], [allLeads])
  const companies = useMemo(() => [...new Set(allLeads.map(l => l.current_company).filter(Boolean))].sort() as string[], [allLeads])

  // Filter leads per project
  const filterLeads = (leads: Lead[]) => {
    return leads.filter(lead => {
      if (filterClassification && lead.classification !== filterClassification) return false
      if (filterIndustry && lead.industry !== filterIndustry) return false
      if (filterCompany && lead.current_company !== filterCompany) return false
      return true
    })
  }

  const hasActiveFilters = filterClassification || filterIndustry || filterCompany || filterSource

  const getScoreColor = (score?: number) => {
    if (!score) return 'text-gray-400'
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getSourceBadge = (source?: string) => {
    if (source === 'stargazer') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
          <Sparkles className="w-3 h-3" /> Stargazer
        </span>
      )
    }
    if (source === 'commit') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full bg-sky-100 dark:bg-sky-900/40 text-sky-700 dark:text-sky-300">
          <GitCommitHorizontal className="w-3 h-3" /> Contributor
        </span>
      )
    }
    return null
  }

  const getClassificationBadge = (classification?: string) => {
    const normalized = classification?.toUpperCase()
    const badges: Record<string, { bg: string, text: string, label: string }> = {
      DECISION_MAKER: { bg: 'bg-purple-100 dark:bg-purple-900', text: 'text-purple-800 dark:text-purple-200', label: 'Decision Maker' },
      KEY_CONTRIBUTOR: { bg: 'bg-blue-100 dark:bg-blue-900', text: 'text-blue-800 dark:text-blue-200', label: 'Key Contributor' },
      HIGH_IMPACT: { bg: 'bg-green-100 dark:bg-green-900', text: 'text-green-800 dark:text-green-200', label: 'High Impact' },
      CONTRIBUTOR: { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-800 dark:text-gray-200', label: 'Contributor' },
    }
    const badge = badges[normalized || ''] || badges.CONTRIBUTOR
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading leads...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Leads</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            AI-classified leads from contributors and stargazers, organized by project
          </p>
        </div>
      </div>

      {/* Bulk Actions Bar */}
      {selectedLeads.size > 0 && (
        <div className="sticky top-0 z-20 bg-gradient-to-r from-cyan-600 to-violet-600 text-white rounded-lg px-5 py-3 flex items-center justify-between shadow-lg">
          <span className="text-sm font-medium">{selectedLeads.size} lead{selectedLeads.size !== 1 ? 's' : ''} selected</span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkPushClay}
              disabled={pushing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {pushing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Push to Clay
            </button>
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
            <button
              onClick={() => setSelectedLeads(new Set())}
              className="ml-2 p-1.5 hover:bg-white/20 rounded-lg"
              title="Clear selection"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* No integrations banner */}
      {clayConfigured === false && projects.length > 0 && (
        <div className="bg-gradient-to-r from-cyan-900/20 to-violet-900/20 border border-cyan-500/20 rounded-lg px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <Blocks className="w-4 h-4 text-cyan-400" />
            Connect an integration to push leads directly to your sales tools
          </div>
          <Link to="/app/integrations" className="text-xs text-cyan-400 hover:text-cyan-300 font-medium">
            Set up Integrations
          </Link>
        </div>
      )}

      {/* Filters */}
      {projects.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
            {hasActiveFilters && (
              <button
                onClick={() => { setFilterClassification(''); setFilterIndustry(''); setFilterCompany(''); setFilterSource(''); }}
                className="ml-2 text-xs text-red-600 dark:text-red-400 hover:underline flex items-center"
              >
                <X className="w-3 h-3 mr-1" /> Clear all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            <StyledSelect
              value={filterClassification}
              onChange={setFilterClassification}
              placeholder="All Classifications"
              options={[
                { value: '', label: 'All Classifications' },
                { value: 'DECISION_MAKER', label: 'Decision Maker' },
                { value: 'HIGH_IMPACT', label: 'High Impact' },
              ]}
            />
            <StyledSelect
              value={filterIndustry}
              onChange={setFilterIndustry}
              placeholder="All Industries"
              options={[{ value: '', label: 'All Industries' }, ...industries.map(ind => ({ value: ind, label: ind }))]}
            />
            <StyledSelect
              value={filterCompany}
              onChange={setFilterCompany}
              placeholder="All Organizations"
              options={[{ value: '', label: 'All Organizations' }, ...companies.map(comp => ({ value: comp, label: comp }))]}
            />
            <StyledSelect
              value={filterSource}
              onChange={setFilterSource}
              placeholder="All Sources"
              options={[
                { value: '', label: 'All Sources' },
                { value: 'commit', label: 'Contributors' },
                { value: 'stargazer', label: 'Stargazers' },
              ]}
            />
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 p-8 mb-6">
            <UserCheck className="w-16 h-16 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            No Leads Yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-2xl mb-8 leading-relaxed">
            Leads are qualified contributors from your tracked projects. They're automatically scored and classified 
            based on their activity, influence, and role. Get started by:
          </p>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mb-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="bg-blue-100 dark:bg-blue-900/30 w-10 h-10 rounded-lg flex items-center justify-center mb-3">
                <span className="text-blue-600 dark:text-blue-400 font-bold">1</span>
              </div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Create a Project</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">Define your target audience and sourcing criteria</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="bg-purple-100 dark:bg-purple-900/30 w-10 h-10 rounded-lg flex items-center justify-center mb-3">
                <span className="text-purple-600 dark:text-purple-400 font-bold">2</span>
              </div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Add Repositories</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">Connect GitHub repos to source contributors from</p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="bg-green-100 dark:bg-green-900/30 w-10 h-10 rounded-lg flex items-center justify-center mb-3">
                <span className="text-green-600 dark:text-green-400 font-bold">3</span>
              </div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Start Sourcing</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">Run jobs to discover and enrich leads automatically</p>
            </div>
          </div>
          <Link
            to="/app/projects"
            className="px-6 py-3 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
          >
            <FolderKanban className="w-5 h-5 mr-2" />
            Go to Projects
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {projects.map((project) => {
            const isExpanded = expandedProjects.has(project.id)
            return (
              <div
                key={project.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                {/* Project Header */}
                <div className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                  <div className="flex items-center space-x-3">
                    {isExpanded && filterLeads(project.leads).length > 0 && (
                      <input
                        type="checkbox"
                        checked={filterLeads(project.leads).every(l => selectedLeads.has(l.id))}
                        onChange={() => toggleSelectAllInProject(project.id)}
                        className="w-4 h-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500"
                        onClick={(e) => e.stopPropagation()}
                      />
                    )}
                    <button onClick={() => toggleProject(project.id)} className="flex items-center space-x-3">
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                      )}
                      <div className="text-left">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400">{project.description}</p>
                        )}
                      </div>
                    </button>
                  </div>
                  <span className="px-3 py-1 bg-primary text-white text-sm font-medium rounded-full">
                    {filterLeads(project.leads).length} {filterLeads(project.leads).length === 1 ? 'Lead' : 'Leads'}
                  </span>
                </div>

                {/* Leads List */}
                {isExpanded && (
                  <div className="border-t border-gray-200 dark:border-gray-700">
                    {filterLeads(project.leads).length === 0 && (
                      <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                        No leads match the current filters
                      </div>
                    )}
                    {filterLeads(project.leads).map((lead) => (
                      <div
                        key={lead.id}
                        className={`px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700 last:border-b-0 ${selectedLeads.has(lead.id) ? 'bg-cyan-50/50 dark:bg-cyan-900/10' : ''}`}
                      >
                        <div className="flex items-start space-x-4">
                          {/* Checkbox */}
                          <input
                            type="checkbox"
                            checked={selectedLeads.has(lead.id)}
                            onChange={() => toggleSelectLead(lead.id)}
                            className="mt-3 w-4 h-4 rounded border-gray-300 text-cyan-600 focus:ring-cyan-500 flex-shrink-0"
                          />
                          {/* Avatar */}
                          <img
                            src={lead.linkedin_profile_photo_url || lead.avatar_url}
                            alt={lead.full_name}
                            className="w-12 h-12 rounded-full object-cover"
                          />

                          {/* Lead Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                                {lead.full_name}
                              </h4>
                              {getClassificationBadge(lead.classification)}
                              {getSourceBadge(lead.source)}
                              {lead.overall_score != null && (
                                <ScoreTooltip
                                  scores={{
                                    overall_score: lead.overall_score || 0,
                                    activity_score: lead.activity_score,
                                    influence_score: lead.influence_score,
                                    position_score: lead.position_score,
                                    engagement_score: lead.engagement_score,
                                  }}
                                  colorClass={getScoreColor(lead.overall_score)}
                                  size="md"
                                />
                              )}
                            </div>

                            <div className="flex flex-wrap gap-3 text-sm text-gray-600 dark:text-gray-400">
                              {(lead.current_company || lead.company) && (
                                <div className="flex items-center">
                                  <Building2 className="w-4 h-4 mr-1" />
                                  {lead.current_position && `${lead.current_position} at `}
                                  {lead.current_company || lead.company}
                                </div>
                              )}
                              {lead.industry && (
                                <div className="flex items-center">
                                  <Factory className="w-4 h-4 mr-1" />
                                  {lead.industry}
                                </div>
                              )}
                              {lead.email && (
                                <div className="flex items-center">
                                  <Mail className="w-4 h-4 mr-1" />
                                  {lead.email}
                                </div>
                              )}
                            </div>

                            {/* Classification reasoning */}
                            {lead.classification_reasoning && (
                              <div className="mt-1">
                                <button
                                  onClick={() => toggleReasoning(lead.id)}
                                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center"
                                >
                                  <Info className="w-3 h-3 mr-1" />
                                  {expandedReasoning.has(lead.id) ? 'Hide' : 'Why this classification?'}
                                </button>
                                {expandedReasoning.has(lead.id) && (
                                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded p-2 leading-relaxed">
                                    {lead.classification_reasoning}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Links + Push to Clay */}
                            <div className="flex items-center gap-2 mt-2">
                              {lead.linkedin_url && (
                                <a
                                  href={lead.linkedin_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                                >
                                  LinkedIn <ExternalLink className="w-3 h-3 ml-1" />
                                </a>
                              )}
                              <a
                                href={`https://github.com/${lead.username}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                              >
                                GitHub <ExternalLink className="w-3 h-3 ml-1" />
                              </a>
                              {clayConfigured && !lead.clay_pushed_at && (
                                <button
                                  onClick={() => handleSinglePushClay(lead.id)}
                                  disabled={pushingLeadId === lead.id}
                                  className="inline-flex items-center gap-1 px-3 py-1 text-sm text-cyan-600 dark:text-cyan-400 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 rounded-lg disabled:opacity-50"
                                >
                                  {pushingLeadId === lead.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                                  Push to Clay
                                </button>
                              )}
                              {lead.clay_pushed_at && (
                                <span className="inline-flex items-center gap-1 px-2 py-1 text-[11px] text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 rounded-full">
                                  <Cloud className="w-3 h-3" />
                                  Pushed to Clay {new Date(lead.clay_pushed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Other Contributors - collapsible */}
                    {project.contributors && project.contributors.length > 0 && (
                      <div className="border-t border-gray-200 dark:border-gray-700">
                        <button
                          onClick={() => setExpandedContributors(prev => {
                            const s = new Set(prev)
                            s.has(project.id) ? s.delete(project.id) : s.add(project.id)
                            return s
                          })}
                          className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                        >
                          <div className="flex items-center space-x-2">
                            {expandedContributors.has(project.id) ? (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-gray-400" />
                            )}
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              Other Contributors
                            </span>
                          </div>
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                            {project.contributors.length}
                          </span>
                        </button>

                        {expandedContributors.has(project.id) && (
                          <div className="bg-gray-50/30 dark:bg-gray-900/20">
                            {project.contributors.map((lead) => (
                              <div
                                key={lead.id}
                                className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                              >
                                <div className="flex items-start space-x-4">
                                  <img
                                    src={lead.linkedin_profile_photo_url || lead.avatar_url}
                                    alt={lead.full_name || lead.username}
                                    className="w-12 h-12 rounded-full object-cover"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                                        {lead.full_name || lead.username}
                                      </h4>
                                      {getClassificationBadge(lead.classification)}
                                      {getSourceBadge(lead.source)}
                                      {lead.overall_score != null && (
                                        <ScoreTooltip
                                          scores={{
                                            overall_score: lead.overall_score || 0,
                                            activity_score: lead.activity_score,
                                            influence_score: lead.influence_score,
                                            position_score: lead.position_score,
                                            engagement_score: lead.engagement_score,
                                          }}
                                          colorClass={getScoreColor(lead.overall_score)}
                                          size="md"
                                        />
                                      )}
                                    </div>

                                    <div className="flex flex-wrap gap-3 text-sm text-gray-600 dark:text-gray-400">
                                      {(lead.current_company || lead.company) && (
                                        <div className="flex items-center">
                                          <Building2 className="w-4 h-4 mr-1" />
                                          {lead.current_position && `${lead.current_position} at `}
                                          {lead.current_company || lead.company}
                                        </div>
                                      )}
                                      {lead.industry && (
                                        <div className="flex items-center">
                                          <Factory className="w-4 h-4 mr-1" />
                                          {lead.industry}
                                        </div>
                                      )}
                                      {lead.email && (
                                        <div className="flex items-center">
                                          <Mail className="w-4 h-4 mr-1" />
                                          {lead.email}
                                        </div>
                                      )}
                                    </div>

                                    {lead.classification_reasoning && (
                                      <div className="mt-1">
                                        <button
                                          onClick={() => toggleReasoning(lead.id)}
                                          className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center"
                                        >
                                          <Info className="w-3 h-3 mr-1" />
                                          {expandedReasoning.has(lead.id) ? 'Hide' : 'Why this classification?'}
                                        </button>
                                        {expandedReasoning.has(lead.id) && (
                                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded p-2 leading-relaxed">
                                            {lead.classification_reasoning}
                                          </p>
                                        )}
                                      </div>
                                    )}

                                    <div className="flex gap-2 mt-2">
                                      {lead.linkedin_url && (
                                        <a
                                          href={lead.linkedin_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                                        >
                                          LinkedIn <ExternalLink className="w-3 h-3 ml-1" />
                                        </a>
                                      )}
                                      <a
                                        href={`https://github.com/${lead.username}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center px-3 py-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                                      >
                                        GitHub <ExternalLink className="w-3 h-3 ml-1" />
                                      </a>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      {/* Push Confirmation Modal */}
      {showPushConfirm && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Push to Clay</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Push {selectedLeads.size} lead{selectedLeads.size !== 1 ? 's' : ''} to your Clay table? Already-pushed leads will be updated with latest data.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={() => setShowPushConfirm(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                onClick={confirmBulkPush}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm inline-flex items-center gap-2"
              >
                <Send className="w-4 h-4" /> Push to Clay
              </button>
            </div>
          </div>
        </div>
      )}

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
