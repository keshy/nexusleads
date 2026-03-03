import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import Toast from '../components/Toast'
import {
  ExternalLink, CheckCircle2, XCircle, AlertCircle, CheckCircle,
  Send, Activity, BarChart3, Clock, ChevronRight, Loader2, Lock,
  Eye, EyeOff, Trash2, Info, HelpCircle, AlertTriangle,
  Globe,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface ClayConfig { webhook_url: string; connected: boolean }
interface ClayStats { total: number; success: number; failed: number }
interface ActivityLog {
  id: string; contributor_id: string; project_id: string | null
  status: string; pushed_at: string | null; error_message: string | null
}
interface AppSetting {
  key: string; value: string | null; is_set: boolean; is_secret: boolean
  required: boolean; description: string; source: string
  hint?: string; help_url?: string; placeholder?: string
}

/* ------------------------------------------------------------------ */
/*  Source connector definitions                                       */
/* ------------------------------------------------------------------ */
const SOURCE_CONNECTOR_GROUPS: { label: string; icon: string; desc: string; keys: string[]; status: 'active' | 'tracking' }[] = [
  { label: 'GitHub', icon: '🐙', desc: 'Scan repository contributors, stargazers, and activity.', keys: ['GITHUB_TOKEN'], status: 'active' },
  { label: 'Discord', icon: '💬', desc: 'Scan Discord server members. Requires a bot with Server Members Intent.', keys: ['DISCORD_BOT_TOKEN'], status: 'active' },
  { label: 'Reddit', icon: '📡', desc: 'Scan subreddit participants — post and comment authors.', keys: ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'], status: 'active' },
  { label: 'X / Twitter', icon: '𝕏', desc: 'Scan followers and engagers of an X account.', keys: ['X_BEARER_TOKEN'], status: 'active' },
  { label: 'StockTwits', icon: '📈', desc: 'Scan ticker stream participants on StockTwits.', keys: ['STOCKTWITS_TOKEN'], status: 'active' },
]

/* ------------------------------------------------------------------ */
/*  Destination tiles                                                  */
/* ------------------------------------------------------------------ */
const DESTINATION_TILES = [
  { name: 'Apollo', desc: 'Enrich leads with Apollo.io contact data', status: 'coming_soon' as const, features: ['Contact data enrichment', 'Verified email addresses', 'Company intelligence'] },
  { name: 'Salesforce', desc: 'Sync leads to Salesforce CRM', status: 'enterprise' as const, features: ['Auto-create contacts from qualified leads', 'Map NexusLeads scores to Salesforce fields', 'Bi-directional sync for lead status', 'Custom field mapping'] },
  { name: 'HubSpot', desc: 'Push leads into HubSpot contacts', status: 'enterprise' as const, features: ['Create contacts and deals automatically', 'Sync lead scores and classifications', 'Trigger workflows on new leads', 'Custom property mapping'] },
  { name: 'Outreach', desc: 'Add leads to Outreach sequences', status: 'enterprise' as const, features: ['Add leads to sequences automatically', 'Personalize with NexusLeads enrichment data', 'Track engagement back to source repo', 'A/B test messaging by lead classification'] },
  { name: 'Slack', desc: 'Get notified about new qualified leads', status: 'enterprise' as const, features: ['Real-time alerts for high-score leads', 'Configurable notification rules', 'Channel-per-project routing', 'Rich lead preview cards'] },
  { name: 'Webhooks', desc: 'Send lead data to any endpoint', status: 'enterprise' as const, features: ['Push to any HTTP endpoint', 'Configurable payload format', 'Retry on failure', 'Event filtering by score/classification'] },
]

/* ================================================================== */
export default function Integrations() {
  const [activeTab, setActiveTab] = useState<'connectors' | 'destinations'>('connectors')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)

  // Source-connector settings state
  const [appSettings, setAppSettings] = useState<AppSetting[]>([])
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})

  // Destinations / Clay state
  const [clayConfig, setClayConfig] = useState<ClayConfig | null>(null)
  const [clayStats, setClayStats] = useState<ClayStats | null>(null)
  const [activity, setActivity] = useState<ActivityLog[]>([])
  const [webhookUrl, setWebhookUrl] = useState('')
  const [showClayDetail, setShowClayDetail] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message?: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [gatedModal, setGatedModal] = useState<typeof DESTINATION_TILES[0] | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (activeTab === 'connectors') fetchSettings()
  }, [activeTab])

  const loadData = async () => {
    try {
      const [config, stats, logs] = await Promise.all([
        api.getClayConfig(),
        api.getClayStats(),
        api.getClayActivity(20),
      ])
      setClayConfig(config)
      setClayStats(stats)
      setActivity(logs)
      setWebhookUrl(config.webhook_url || '')
    } catch (err) {
      console.error('Failed to load integrations data', err)
    } finally {
      setLoading(false)
    }
  }

  /* ---- Source connector settings helpers ---- */
  const fetchSettings = async () => {
    try {
      setSettingsLoading(true)
      const data = await api.getSettings()
      setAppSettings(data)
    } catch (error) {
      console.error('Error fetching settings:', error)
    } finally {
      setSettingsLoading(false)
    }
  }

  const handleSaveSetting = async (key: string, value: string) => {
    try {
      setSavingKey(key)
      await api.updateSetting(key, value)
      setToast({ message: `${key} updated successfully`, type: 'success' })
      setEditingKey(null)
      setEditValue('')
      fetchSettings()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || `Failed to update ${key}`, type: 'error' })
    } finally {
      setSavingKey(null)
    }
  }

  const handleDeleteSetting = async (key: string) => {
    try {
      setSavingKey(key)
      await api.deleteSetting(key)
      setToast({ message: `${key} removed (will use env var if set)`, type: 'info' })
      fetchSettings()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || `Failed to remove ${key}`, type: 'error' })
    } finally {
      setSavingKey(null)
    }
  }

  /* ---- Clay helpers ---- */
  const saveClay = async () => {
    setSaving(true)
    try {
      await api.updateClayConfig(webhookUrl)
      setToast({ message: 'Clay webhook saved', type: 'success' })
      await loadData()
    } finally {
      setSaving(false)
    }
  }

  const testClay = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.testClayWebhook()
      setTestResult(res)
    } catch {
      setTestResult({ status: 'error', message: 'Request failed' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  /* ---- Render a single setting row (reusable) ---- */
  const renderSettingRow = (setting: AppSetting) => (
    <div key={setting.key} className="px-6 py-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0 mr-4">
          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
            <code className="text-sm font-mono font-medium text-gray-900 dark:text-gray-100">{setting.key}</code>
            {setting.required && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 uppercase tracking-wider">Required</span>
            )}
            {setting.is_set ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                <CheckCircle className="w-3 h-3 mr-1" />
                {setting.source === 'database' ? 'Set (DB)' : 'Set (ENV)'}
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
                <XCircle className="w-3 h-3 mr-1" />
                Not configured
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{setting.description}</p>
          {setting.hint && (
            <div className="mt-2 flex items-start gap-1.5 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30 rounded-md px-3 py-2">
              <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <span>
                {setting.hint}
                {setting.help_url && (
                  <>
                    {' '}
                    <a href={setting.help_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 font-medium underline hover:text-blue-700 dark:hover:text-blue-300">
                      Open <ExternalLink className="w-3 h-3" />
                    </a>
                  </>
                )}
              </span>
            </div>
          )}
          {setting.is_set && setting.value && (
            <div className="mt-2 flex items-center space-x-2">
              <code className="text-xs text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded font-mono">
                {setting.is_secret && !showSecrets[setting.key] ? '••••••••' : setting.value}
              </code>
              {setting.is_secret && (
                <button onClick={() => setShowSecrets(prev => ({ ...prev, [setting.key]: !prev[setting.key] }))} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  {showSecrets[setting.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center space-x-2 flex-shrink-0">
          {editingKey === setting.key ? (
            <>
              <input
                type={setting.is_secret ? 'password' : 'text'}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder={setting.placeholder || `Enter ${setting.key}`}
                className="w-64 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-mono"
                autoFocus
              />
              <button onClick={() => handleSaveSetting(setting.key, editValue)} disabled={!editValue || savingKey === setting.key} className="px-3 py-1.5 text-sm bg-primary hover:bg-primary/90 text-white rounded-lg disabled:opacity-60">
                {savingKey === setting.key ? '...' : 'Save'}
              </button>
              <button onClick={() => { setEditingKey(null); setEditValue('') }} className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg">Cancel</button>
            </>
          ) : (
            <>
              <button onClick={() => { setEditingKey(setting.key); setEditValue('') }} className="px-3 py-1.5 text-sm bg-primary hover:bg-primary/90 text-white rounded-lg">
                {setting.is_set ? 'Update' : 'Set'}
              </button>
              {setting.is_set && setting.source === 'database' && (
                <button onClick={() => handleDeleteSetting(setting.key)} disabled={savingKey === setting.key} className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800" title="Remove DB override">
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Integrations</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Configure source connectors and lead destinations to power your pipeline.
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('connectors')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'connectors'
                ? 'border-primary text-primary dark:text-primary'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <div className="flex items-center space-x-2">
              <Globe className="w-5 h-5" />
              <span>Source Connectors</span>
            </div>
          </button>
          <button
            onClick={() => setActiveTab('destinations')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'destinations'
                ? 'border-primary text-primary dark:text-primary'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <div className="flex items-center space-x-2">
              <Send className="w-5 h-5" />
              <span>Destinations</span>
            </div>
          </button>
        </nav>
      </div>

      {/* ============================================================ */}
      {/* SOURCE CONNECTORS TAB                                        */}
      {/* ============================================================ */}
      {activeTab === 'connectors' && (
        <div className="max-w-3xl space-y-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Configure API keys for each community source type. Sources added to projects will use these credentials to ingest data.
          </p>

          {/* Quick status */}
          {appSettings.length > 0 && (() => {
            const allConnectorKeys = SOURCE_CONNECTOR_GROUPS.flatMap(g => g.keys)
            const connectorSettings = appSettings.filter(s => allConnectorKeys.includes(s.key))
            const requiredMissing = connectorSettings.filter(s => s.required && !s.is_set)
            const totalSet = connectorSettings.filter(s => s.is_set).length
            if (connectorSettings.length === 0) return null
            return (
              <div className={`rounded-lg border p-4 flex items-start gap-3 ${
                requiredMissing.length > 0
                  ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700/50'
                  : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700/50'
              }`}>
                {requiredMissing.length > 0 ? (
                  <>
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                        {requiredMissing.length} required key{requiredMissing.length > 1 ? 's' : ''} not configured
                      </p>
                      <p className="text-xs text-amber-600 dark:text-amber-300 mt-0.5">
                        Missing: {requiredMissing.map(s => s.key).join(', ')}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-green-800 dark:text-green-200">
                        {totalSet} connector key{totalSet !== 1 ? 's' : ''} configured
                      </p>
                    </div>
                  </>
                )}
              </div>
            )
          })()}

          {settingsLoading && appSettings.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading connector settings...</div>
          ) : (
            SOURCE_CONNECTOR_GROUPS.map((group) => {
              const groupSettings = appSettings.filter(s => group.keys.includes(s.key))
              return (
                <div key={group.label} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{group.icon}</span>
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{group.label}</h3>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{group.desc}</p>
                        </div>
                      </div>
                      {group.status === 'tracking' ? (
                        <span className="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-600 rounded px-2 py-0.5 font-medium">Tracking Only</span>
                      ) : groupSettings.length > 0 ? (
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {groupSettings.filter(s => s.is_set).length}/{groupSettings.length} configured
                        </span>
                      ) : null}
                    </div>
                  </div>
                  {group.status === 'tracking' ? (
                    <div className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      You can register sources of this type now. Automated scanning will be available once the connector is implemented. Configure the API key ahead of time to be ready.
                    </div>
                  ) : groupSettings.length > 0 ? (
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                      {groupSettings.map(renderSettingRow)}
                    </div>
                  ) : (
                    <div className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      No configurable keys found for this connector.
                    </div>
                  )}
                </div>
              )
            })
          )}

          {/* How it works */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-start gap-3">
              <HelpCircle className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p className="font-medium text-gray-700 dark:text-gray-300">How connector credentials work</p>
                <p>Keys set here (in the database) take priority over environment variables. Removing a key reverts to the env var if one exists. Secrets are encrypted at rest.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* DESTINATIONS TAB                                             */}
      {/* ============================================================ */}
      {activeTab === 'destinations' && (
        <div className="space-y-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Push enriched leads to your sales tools. Configure where qualified leads should be sent after scoring.
          </p>

          {/* Tile grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Clay tile */}
            <button
              onClick={() => setShowClayDetail(!showClayDetail)}
              className={`text-left p-5 rounded-lg border transition-colors ${
                clayConfig?.connected
                  ? 'border-green-400/40 dark:border-green-600/40 bg-green-50 dark:bg-green-950/20 hover:border-green-500'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">Clay</span>
                {clayConfig?.connected ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500 dark:text-green-400" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-yellow-500 dark:text-yellow-400" />
                )}
              </div>
              <p className="text-gray-500 dark:text-gray-400 text-sm">Push enriched leads to Clay via webhook</p>
              <div className="mt-3 text-xs text-primary flex items-center gap-1">
                {clayConfig?.connected ? 'Connected' : 'Not configured'} <ChevronRight className="w-3 h-3" />
              </div>
            </button>

            {/* Coming soon / enterprise tiles */}
            {DESTINATION_TILES.map((tile) => (
              <button
                key={tile.name}
                onClick={() => setGatedModal(tile)}
                className="text-left p-5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 opacity-60 hover:opacity-90 hover:border-gray-400 dark:hover:border-gray-500 transition-all"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{tile.name}</span>
                  <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5">
                    {tile.status === 'enterprise' && <Lock className="w-3 h-3" />}
                    {tile.status === 'enterprise' ? 'Enterprise' : 'Coming Soon'}
                  </span>
                </div>
                <p className="text-gray-500 dark:text-gray-400 text-sm">{tile.desc}</p>
                <div className="mt-3 text-xs text-primary flex items-center gap-1">
                  Learn more <ChevronRight className="w-3 h-3" />
                </div>
              </button>
            ))}
          </div>

          {/* Clay detail panel */}
          {showClayDetail && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Clay Configuration</h2>

              {/* Webhook URL */}
              <div>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Webhook URL</label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder="https://api.clay.com/v1/webhooks/..."
                    className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:border-primary"
                  />
                  <button
                    onClick={saveClay}
                    disabled={saving}
                    className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>

              {/* Test */}
              {clayConfig?.connected && (
                <div>
                  <button
                    onClick={testClay}
                    disabled={testing}
                    className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:border-primary hover:text-primary disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    {testing ? 'Sending...' : 'Send Test Payload'}
                  </button>
                  {testResult && (
                    <div className={`mt-2 text-sm ${testResult.status === 'ok' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {testResult.status === 'ok' ? 'Test successful!' : testResult.message || 'Test failed'}
                    </div>
                  )}
                </div>
              )}

              {/* Stats */}
              {clayStats && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center">
                    <BarChart3 className="w-5 h-5 text-primary mx-auto mb-1" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{clayStats.total}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Total Pushes</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center">
                    <CheckCircle2 className="w-5 h-5 text-green-500 dark:text-green-400 mx-auto mb-1" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{clayStats.success}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Successful</div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-center">
                    <XCircle className="w-5 h-5 text-red-500 dark:text-red-400 mx-auto mb-1" />
                    <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{clayStats.failed}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Failed</div>
                  </div>
                </div>
              )}

              {/* Recent activity */}
              {activity.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                    <Activity className="w-4 h-4" /> Recent Activity
                  </h3>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {activity.map((log) => (
                      <div key={log.id} className="flex items-center gap-3 text-xs py-1.5 px-2 rounded bg-gray-50 dark:bg-gray-900/50">
                        {log.status === 'success' ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-500 dark:text-green-400 shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-red-500 dark:text-red-400 shrink-0" />
                        )}
                        <span className="text-gray-600 dark:text-gray-400 truncate flex-1">
                          {log.contributor_id.slice(0, 8)}...
                        </span>
                        <span className="text-gray-400 dark:text-gray-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {log.pushed_at ? new Date(log.pushed_at).toLocaleDateString() : '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Gated Integration Modal */}
      {gatedModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setGatedModal(null)}>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-3">
              {gatedModal.status === 'enterprise' && <Lock className="w-5 h-5 text-violet-500 dark:text-violet-400" />}
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{gatedModal.name} Integration</h3>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{gatedModal.desc}</p>
            <ul className="space-y-2 mb-6">
              {gatedModal.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            {gatedModal.status === 'enterprise' ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-500 dark:text-gray-400">Available on the Enterprise plan.</p>
                <div className="flex items-center gap-3">
                  <a
                    href="https://calendly.com/keshi8"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm font-medium inline-flex items-center gap-2"
                  >
                    Book a Call <ExternalLink className="w-3 h-3" />
                  </a>
                  <button onClick={() => setGatedModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 rounded-lg text-sm">Close</button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500 dark:text-gray-400">This integration is coming soon.</p>
                <button onClick={() => setGatedModal(null)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 rounded-lg text-sm">Close</button>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && (
        <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />
      )}
    </div>
  )
}
