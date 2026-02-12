import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Users, GitBranch, FolderKanban, Target, ExternalLink, Building2, Factory, Mail, Info, Filter, X, Sparkles, GitCommitHorizontal } from 'lucide-react'
import ScoreTooltip from '../components/ScoreTooltip'
import StyledSelect from '../components/StyledSelect'
import { formatNumber } from '../lib/utils'

interface Lead {
  id: string
  username: string
  full_name: string
  company?: string
  bio?: string
  avatar_url: string
  email?: string
  overall_score: number
  activity_score: number
  influence_score: number
  position_score: number
  engagement_score: number
  priority?: string
  project_name?: string
  classification?: string
  classification_reasoning?: string
  current_position?: string
  current_company?: string
  industry?: string
  linkedin_url?: string
  linkedin_profile_photo_url?: string
  source?: string
}

export default function Dashboard() {
  const [filterClassification, setFilterClassification] = useState('')
  const [filterIndustry, setFilterIndustry] = useState('')
  const [filterCompany, setFilterCompany] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [filterProject, setFilterProject] = useState('')
  const [expandedReasoning, setExpandedReasoning] = useState<Set<string>>(new Set())

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
  })

  const { data: projects = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  })

  const { data: topLeads = [] } = useQuery<Lead[]>({
    queryKey: ['top-leads', filterSource, filterProject],
    queryFn: () => api.getTopLeads(filterProject || undefined, filterSource || undefined),
  })

  const toggleReasoning = (id: string) => {
    setExpandedReasoning(prev => {
      const s = new Set(prev)
      s.has(id) ? s.delete(id) : s.add(id)
      return s
    })
  }

  const industries = useMemo(() => [...new Set(topLeads.map(l => l.industry).filter(Boolean))].sort() as string[], [topLeads])
  const companies = useMemo(() => [...new Set(topLeads.map(l => l.current_company).filter(Boolean))].sort() as string[], [topLeads])

  const filteredLeads = useMemo(() => {
    return topLeads.filter(lead => {
      if (filterClassification && lead.classification !== filterClassification) return false
      if (filterIndustry && lead.industry !== filterIndustry) return false
      if (filterCompany && lead.current_company !== filterCompany) return false
      return true
    })
  }, [topLeads, filterClassification, filterIndustry, filterCompany])

  const hasActiveFilters = filterClassification || filterIndustry || filterCompany || filterSource || filterProject

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
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      DECISION_MAKER: { bg: 'bg-purple-100 dark:bg-purple-900/50', text: 'text-purple-700 dark:text-purple-300', label: 'Decision Maker' },
      KEY_CONTRIBUTOR: { bg: 'bg-blue-100 dark:bg-blue-900/50', text: 'text-blue-700 dark:text-blue-300', label: 'Key Contributor' },
      HIGH_IMPACT: { bg: 'bg-green-100 dark:bg-green-900/50', text: 'text-green-700 dark:text-green-300', label: 'High Impact' },
    }
    const badge = badges[classification?.toUpperCase() || ''] || { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-600 dark:text-gray-300', label: classification || 'Unclassified' }
    return <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${badge.bg} ${badge.text}`}>{badge.label}</span>
  }

  const getScoreColor = (score: number) => {
    if (score >= 50) return 'text-green-600 dark:text-green-400'
    if (score >= 25) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-gray-500 dark:text-gray-400'
  }

  // Distribute cards across columns for masonry layout
  const columnCount = 3
  const columns: Lead[][] = Array.from({ length: columnCount }, () => [])
  filteredLeads.forEach((lead, i) => {
    columns[i % columnCount].push(lead)
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

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">Overview of your lead sourcing activities</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.name} className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900/50 p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{stat.name}</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">
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

      {/* Filters */}
      {topLeads.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filter Leads</span>
            <span className="text-xs text-gray-400 ml-1">({filteredLeads.length} of {topLeads.length})</span>
            {hasActiveFilters && (
              <button
                onClick={() => { setFilterClassification(''); setFilterIndustry(''); setFilterCompany(''); setFilterSource(''); setFilterProject(''); }}
                className="ml-2 text-xs text-red-600 dark:text-red-400 hover:underline flex items-center"
              >
                <X className="w-3 h-3 mr-1" /> Clear all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            <StyledSelect
              value={filterProject}
              onChange={setFilterProject}
              placeholder="All Projects"
              options={[{ value: '', label: 'All Projects' }, ...projects.map(p => ({ value: p.id, label: p.name }))]}
            />
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

      {/* Pinterest / Masonry Lead Cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Top Leads Across All Projects
        </h2>

        {filteredLeads.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            {topLeads.length === 0 ? 'No leads yet — source a repository to get started.' : 'No leads match the current filters.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 items-start">
            {columns.map((col, colIdx) => (
              <div key={colIdx} className="space-y-4">
                {col.map((lead) => (
                  <div
                    key={lead.id}
                    className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow"
                  >
                    {/* Card Header */}
                    <div className="p-4 pb-3">
                      <div className="flex items-start space-x-3">
                        <img
                          src={lead.linkedin_profile_photo_url || lead.avatar_url || '/default-avatar.png'}
                          alt={lead.full_name || lead.username}
                          className="w-12 h-12 rounded-full object-cover flex-shrink-0"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                              {lead.full_name || lead.username}
                            </h3>
                            <div className="flex items-center ml-2 flex-shrink-0">
                              <ScoreTooltip
                                scores={{
                                  overall_score: lead.overall_score,
                                  activity_score: lead.activity_score,
                                  influence_score: lead.influence_score,
                                  position_score: lead.position_score,
                                  engagement_score: lead.engagement_score,
                                }}
                                colorClass={getScoreColor(lead.overall_score)}
                              />
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">@{lead.username}</p>
                        </div>
                      </div>
                    </div>

                    {/* Card Body */}
                    <div className="px-4 pb-3 space-y-2">
                      {/* Classification Badge + Project */}
                      <div className="flex items-center flex-wrap gap-1.5">
                        {getClassificationBadge(lead.classification)}
                        {getSourceBadge(lead.source)}
                        {lead.project_name && (
                          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                            {lead.project_name}
                          </span>
                        )}
                      </div>

                      {/* Org & Industry */}
                      {(lead.current_company || lead.company) && (
                        <div className="flex items-center text-xs text-gray-600 dark:text-gray-400">
                          <Building2 className="w-3.5 h-3.5 mr-1 flex-shrink-0" />
                          <span className="truncate">
                            {lead.current_position && `${lead.current_position} at `}
                            {lead.current_company || lead.company}
                          </span>
                        </div>
                      )}
                      {lead.industry && (
                        <div className="flex items-center text-xs text-gray-600 dark:text-gray-400">
                          <Factory className="w-3.5 h-3.5 mr-1 flex-shrink-0" />
                          <span>{lead.industry}</span>
                        </div>
                      )}
                      {lead.email && (
                        <div className="flex items-center text-xs text-gray-600 dark:text-gray-400">
                          <Mail className="w-3.5 h-3.5 mr-1 flex-shrink-0" />
                          <span className="truncate">{lead.email}</span>
                        </div>
                      )}

                      {/* Bio snippet */}
                      {lead.bio && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                          {lead.bio}
                        </p>
                      )}

                      {/* Classification reasoning */}
                      {lead.classification_reasoning && (
                        <div>
                          <button
                            onClick={() => toggleReasoning(lead.id)}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center"
                          >
                            <Info className="w-3 h-3 mr-1" />
                            {expandedReasoning.has(lead.id) ? 'Hide reasoning' : 'Why this classification?'}
                          </button>
                          {expandedReasoning.has(lead.id) && (
                            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 rounded p-2 leading-relaxed">
                              {lead.classification_reasoning}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Card Footer — Links */}
                    <div className="px-4 pb-3 flex gap-2">
                      <a
                        href={`https://github.com/${lead.username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      >
                        GitHub <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                      {lead.linkedin_url && (
                        <a
                          href={lead.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                        >
                          LinkedIn <ExternalLink className="w-3 h-3 ml-1" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
