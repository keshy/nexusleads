import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import {
  Blocks, ExternalLink, CheckCircle2, XCircle, AlertCircle,
  Send, Activity, BarChart3, Clock, ChevronRight, Loader2, Lock, ArrowRight,
} from 'lucide-react'

interface ClayConfig {
  webhook_url: string
  connected: boolean
}

interface ClayStats {
  total: number
  success: number
  failed: number
}

interface ActivityLog {
  id: string
  contributor_id: string
  project_id: string | null
  status: string
  pushed_at: string | null
  error_message: string | null
}

const COMING_SOON_TILES = [
  { name: 'Apollo', desc: 'Enrich leads with Apollo.io contact data', status: 'coming_soon' as const, features: ['Contact data enrichment', 'Verified email addresses', 'Company intelligence'] },
  { name: 'Salesforce', desc: 'Sync leads to Salesforce CRM', status: 'enterprise' as const, features: ['Auto-create contacts from qualified leads', 'Map NexusLeads scores to Salesforce fields', 'Bi-directional sync for lead status', 'Custom field mapping'] },
  { name: 'HubSpot', desc: 'Push leads into HubSpot contacts', status: 'enterprise' as const, features: ['Create contacts and deals automatically', 'Sync lead scores and classifications', 'Trigger workflows on new leads', 'Custom property mapping'] },
  { name: 'Outreach', desc: 'Add leads to Outreach sequences', status: 'enterprise' as const, features: ['Add leads to sequences automatically', 'Personalize with NexusLeads enrichment data', 'Track engagement back to source repo', 'A/B test messaging by lead classification'] },
  { name: 'Slack', desc: 'Get notified about new qualified leads', status: 'enterprise' as const, features: ['Real-time alerts for high-score leads', 'Configurable notification rules', 'Channel-per-project routing', 'Rich lead preview cards'] },
  { name: 'Webhooks', desc: 'Send lead data to any endpoint', status: 'enterprise' as const, features: ['Push to any HTTP endpoint', 'Configurable payload format', 'Retry on failure', 'Event filtering by score/classification'] },
]

export default function Integrations() {
  const [clayConfig, setClayConfig] = useState<ClayConfig | null>(null)
  const [clayStats, setClayStats] = useState<ClayStats | null>(null)
  const [activity, setActivity] = useState<ActivityLog[]>([])
  const [webhookUrl, setWebhookUrl] = useState('')
  const [showDetail, setShowDetail] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message?: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [gatedModal, setGatedModal] = useState<typeof COMING_SOON_TILES[0] | null>(null)

  useEffect(() => {
    loadData()
  }, [])

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

  const saveClay = async () => {
    setSaving(true)
    try {
      await api.updateClayConfig(webhookUrl)
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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Blocks className="w-6 h-6 text-cyan-400" /> Integrations
        </h1>
        <p className="text-gray-400 mt-1">Connect NexusLeads to your sales stack. Push enriched leads directly into the tools your team already uses.</p>
      </div>

      {/* Pipeline Banner */}
      <div className="rounded-xl border border-cyan-500/20 bg-gradient-to-r from-cyan-950/40 to-violet-950/40 p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-cyan-400 uppercase tracking-wider mb-1">Your Pipeline</div>
            <div className="text-lg font-semibold text-white">Source <ArrowRight className="w-4 h-4 inline mx-1 text-gray-500" /> Enrich <ArrowRight className="w-4 h-4 inline mx-1 text-gray-500" /> Score <ArrowRight className="w-4 h-4 inline mx-1 text-cyan-400" /> <span className="text-cyan-400">ACT</span></div>
          </div>
          <p className="text-sm text-gray-400 max-w-xs text-right">NexusLeads finds the leads. These integrations close them.</p>
        </div>
      </div>

      {/* Tile grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Clay tile */}
        <button
          onClick={() => setShowDetail(!showDetail)}
          className={`text-left p-5 rounded-xl border transition-colors ${
            clayConfig?.connected
              ? 'border-green-600/40 bg-green-950/20 hover:border-green-500'
              : 'border-gray-700 bg-gray-900 hover:border-cyan-500'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-lg font-semibold text-white">Clay</span>
            {clayConfig?.connected ? (
              <CheckCircle2 className="w-5 h-5 text-green-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400" />
            )}
          </div>
          <p className="text-gray-400 text-sm">Push enriched leads to Clay via webhook</p>
          <div className="mt-3 text-xs text-cyan-400 flex items-center gap-1">
            {clayConfig?.connected ? 'Connected' : 'Not configured'} <ChevronRight className="w-3 h-3" />
          </div>
        </button>

        {/* Coming soon / enterprise tiles */}
        {COMING_SOON_TILES.map((tile) => (
          <button
            key={tile.name}
            onClick={() => setGatedModal(tile)}
            className="text-left p-5 rounded-xl border border-gray-800 bg-gray-900/50 opacity-70 hover:opacity-90 hover:border-gray-600 transition-all"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-lg font-semibold text-white">{tile.name}</span>
              <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-gray-500 border border-gray-700 rounded px-1.5 py-0.5">
                {tile.status === 'enterprise' && <Lock className="w-3 h-3" />}
                {tile.status === 'enterprise' ? 'Enterprise' : 'Coming Soon'}
              </span>
            </div>
            <p className="text-gray-500 text-sm">{tile.desc}</p>
            <div className="mt-3 text-xs text-cyan-400 flex items-center gap-1">
              Learn more <ChevronRight className="w-3 h-3" />
            </div>
          </button>
        ))}
      </div>

      {/* Clay detail panel */}
      {showDetail && (
        <div className="rounded-xl border border-gray-700 bg-gray-900 p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white">Clay Configuration</h2>

          {/* Webhook URL */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Webhook URL</label>
            <div className="flex gap-2">
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://api.clay.com/v1/webhooks/..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={saveClay}
                disabled={saving}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm disabled:opacity-50"
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
                className="flex items-center gap-2 px-4 py-2 border border-gray-600 rounded-lg text-sm text-gray-300 hover:border-cyan-500 hover:text-white disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                {testing ? 'Sending...' : 'Send Test Payload'}
              </button>
              {testResult && (
                <div className={`mt-2 text-sm ${testResult.status === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
                  {testResult.status === 'ok' ? 'Test successful!' : testResult.message || 'Test failed'}
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          {clayStats && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <BarChart3 className="w-5 h-5 text-cyan-400 mx-auto mb-1" />
                <div className="text-2xl font-bold text-white">{clayStats.total}</div>
                <div className="text-xs text-gray-400">Total Pushes</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <CheckCircle2 className="w-5 h-5 text-green-400 mx-auto mb-1" />
                <div className="text-2xl font-bold text-white">{clayStats.success}</div>
                <div className="text-xs text-gray-400">Successful</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <XCircle className="w-5 h-5 text-red-400 mx-auto mb-1" />
                <div className="text-2xl font-bold text-white">{clayStats.failed}</div>
                <div className="text-xs text-gray-400">Failed</div>
              </div>
            </div>
          )}

          {/* Recent activity */}
          {activity.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4" /> Recent Activity
              </h3>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {activity.map((log) => (
                  <div key={log.id} className="flex items-center gap-3 text-xs py-1.5 px-2 rounded bg-gray-800/50">
                    {log.status === 'success' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-400 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    )}
                    <span className="text-gray-400 truncate flex-1">
                      {log.contributor_id.slice(0, 8)}...
                    </span>
                    <span className="text-gray-500 flex items-center gap-1">
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
      {/* Gated Integration Modal */}
      {gatedModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setGatedModal(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-3">
              {gatedModal.status === 'enterprise' && <Lock className="w-5 h-5 text-violet-400" />}
              <h3 className="text-lg font-semibold text-white">{gatedModal.name} Integration</h3>
            </div>
            <p className="text-sm text-gray-400 mb-4">{gatedModal.desc}</p>
            <ul className="space-y-2 mb-6">
              {gatedModal.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-300">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            {gatedModal.status === 'enterprise' ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">Available on the Enterprise plan.</p>
                <div className="flex items-center gap-3">
                  <a
                    href="https://calendly.com/keshi8"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white rounded-lg text-sm font-medium inline-flex items-center gap-2"
                  >
                    Book a Call <ExternalLink className="w-3 h-3" />
                  </a>
                  <button onClick={() => setGatedModal(null)} className="px-4 py-2 border border-gray-600 text-gray-400 rounded-lg text-sm">Close</button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">This integration is coming soon.</p>
                <button onClick={() => setGatedModal(null)} className="px-4 py-2 border border-gray-600 text-gray-400 rounded-lg text-sm">Close</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
