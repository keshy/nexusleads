import { useState, useEffect, FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { User, Users, UserPlus, Trash2, Shield, Mail, Calendar, Save, Key, Eye, EyeOff, CheckCircle, XCircle, RotateCcw, HelpCircle, ExternalLink, AlertTriangle, Info, Lock } from 'lucide-react'
import { api } from '../lib/api'
import Toast from '../components/Toast'

interface UserData {
  id: string
  username: string
  email: string
  full_name?: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  last_login?: string
}

interface AppSettingData {
  key: string
  value: string
  description: string
  is_secret: boolean
  is_set: boolean
  source: string
  hint: string
  help_url: string
  required: boolean
  placeholder: string
}

export default function Settings() {
  const { user } = useAuth()
  const [users, setUsers] = useState<UserData[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'profile' | 'users' | 'apikeys'>('profile')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileFeedback, setProfileFeedback] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' | 'info' } | null>(null)
  const [showAddUser, setShowAddUser] = useState(false)
  const [newUser, setNewUser] = useState({ username: '', email: '', full_name: '', password: '' })
  const [creatingUser, setCreatingUser] = useState(false)
  
  // Profile form state
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordFeedback, setPasswordFeedback] = useState<{ msg: string; ok: boolean } | null>(null)

  // API Keys state
  const [appSettings, setAppSettings] = useState<AppSettingData[]>([])
  const [settingsLoading, setSettingsLoading] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (user) {
      setEmail(user.email || '')
      setFullName(user.full_name || '')
    }
  }, [user])

  useEffect(() => {
    if (user?.is_admin && activeTab === 'users') {
      fetchUsers()
    }
    if (user?.is_admin && activeTab === 'apikeys') {
      fetchSettings()
    }
  }, [user, activeTab])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const data = await api.getUsers()
      setUsers(data)
    } catch (error) {
      console.error('Error fetching users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveProfile = async () => {
    try {
      setProfileSaving(true)
      setProfileFeedback(null)
      await api.updateUserProfile({ email, full_name: fullName })
      setProfileFeedback('Profile updated.')
    } catch (error: any) {
      setProfileFeedback(error.response?.data?.detail || 'Failed to update profile.')
    } finally {
      setProfileSaving(false)
    }
  }

  const handleChangePassword = async () => {
    setPasswordFeedback(null)
    if (newPassword.length < 8) {
      setPasswordFeedback({ msg: 'Password must be at least 8 characters.', ok: false })
      return
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordFeedback({ msg: 'Passwords do not match.', ok: false })
      return
    }
    try {
      setPasswordSaving(true)
      await api.updateUserProfile({ password: newPassword })
      setPasswordFeedback({ msg: 'Password changed successfully.', ok: true })
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (error: any) {
      setPasswordFeedback({ msg: error.response?.data?.detail || 'Failed to change password.', ok: false })
    } finally {
      setPasswordSaving(false)
    }
  }

  const handleDeleteUser = async (userId: string) => {
    const confirmed = window.confirm('Delete this user? This cannot be undone.')
    if (!confirmed) return

    try {
      await api.deleteUser(userId)
      setUsers((prev) => prev.filter((u) => u.id !== userId))
    } catch (error) {
      console.error('Error deleting user:', error)
    }
  }

  const handleCreateUser = async (e: FormEvent) => {
    e.preventDefault()
    try {
      setCreatingUser(true)
      await api.createUser({
        username: newUser.username,
        email: newUser.email,
        password: newUser.password,
        full_name: newUser.full_name || undefined
      })
      setShowAddUser(false)
      setNewUser({ username: '', email: '', full_name: '', password: '' })
      setToast({ message: 'User created successfully', type: 'success' })
      fetchUsers()
    } catch (error: any) {
      setToast({ message: error.response?.data?.detail || 'Failed to create user', type: 'error' })
    } finally {
      setCreatingUser(false)
    }
  }

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

  const settingGroups: { label: string; keys: string[] }[] = [
    { label: 'GitHub', keys: ['GITHUB_TOKEN'] },
    { label: 'Azure OpenAI', keys: ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_DEPLOYMENT', 'AZURE_OPENAI_API_VERSION'] },
    { label: 'OpenAI (Non-Azure)', keys: ['OPENAI_API_KEY', 'OPENAI_MODEL'] },
    { label: 'Web Search', keys: ['SERPER_API_KEY'] },
  ]

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">Manage your account and preferences</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('profile')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'profile'
                ? 'border-primary text-primary dark:text-primary'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
            }`}
          >
            <div className="flex items-center space-x-2">
              <User className="w-5 h-5" />
              <span>My Profile</span>
            </div>
          </button>
          {user?.is_admin && (
            <button
              onClick={() => setActiveTab('apikeys')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'apikeys'
                  ? 'border-primary text-primary dark:text-primary'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Key className="w-5 h-5" />
                <span>API Keys</span>
              </div>
            </button>
          )}
          {user?.is_admin && (
            <button
              onClick={() => setActiveTab('users')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'users'
                  ? 'border-primary text-primary dark:text-primary'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Users className="w-5 h-5" />
                <span>User Management</span>
              </div>
            </button>
          )}
        </nav>
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="max-w-2xl space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
            <div className="flex items-center space-x-4">
              <div className="w-20 h-20 rounded-full bg-primary text-white flex items-center justify-center text-3xl font-bold">
                {fullName.charAt(0) || user?.username?.charAt(0) || 'U'}
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  {fullName || user?.username}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{email}</p>
                {user?.is_admin && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 mt-2">
                    <Shield className="w-3 h-3 mr-1" />
                    Administrator
                  </span>
                )}
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={user?.username || ''}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Username cannot be changed after account creation.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div className="pt-4 space-y-3">
                <button
                  onClick={handleSaveProfile}
                  disabled={profileSaving}
                  className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {profileSaving ? 'Saving...' : 'Save Changes'}
                </button>
                {profileFeedback && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">{profileFeedback}</p>
                )}
              </div>
            </div>
          </div>

          {/* Password Change */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Change Password</h3>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Choose a strong password with at least 8 characters including numbers and uppercase letters.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Confirm New Password</label>
              <input
                type="password"
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                placeholder="Re-enter new password"
                className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${
                  confirmNewPassword.length > 0
                    ? newPassword === confirmNewPassword
                      ? 'border-green-500/50 dark:border-green-500/50'
                      : 'border-red-500/50 dark:border-red-500/50'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
              />
              {confirmNewPassword.length > 0 && newPassword !== confirmNewPassword && (
                <p className="mt-1 text-xs text-red-500">Passwords do not match</p>
              )}
            </div>
            <div className="pt-2 space-y-3">
              <button
                onClick={handleChangePassword}
                disabled={passwordSaving || newPassword.length < 8 || newPassword !== confirmNewPassword}
                className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Lock className="w-4 h-4 mr-2" />
                {passwordSaving ? 'Changing...' : 'Change Password'}
              </button>
              {passwordFeedback && (
                <p className={`text-sm ${passwordFeedback.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {passwordFeedback.msg}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* API Keys Tab */}
      {activeTab === 'apikeys' && user?.is_admin && (
        <div className="max-w-3xl space-y-6">
          {/* Header with info banner */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Configure API keys and service credentials. Values stored here take priority over environment variables.
              </p>
            </div>
            <button
              onClick={fetchSettings}
              disabled={settingsLoading}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 inline-flex items-center"
            >
              <RotateCcw className={`w-4 h-4 mr-1 ${settingsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Quick status overview */}
          {appSettings.length > 0 && (() => {
            const requiredMissing = appSettings.filter(s => s.required && !s.is_set)
            const totalSet = appSettings.filter(s => s.is_set).length
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
                        Missing: {requiredMissing.map(s => s.key).join(', ')}. These are needed for core functionality.
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-green-800 dark:text-green-200">
                        All required keys configured ({totalSet}/{appSettings.length} total)
                      </p>
                      <p className="text-xs text-green-600 dark:text-green-300 mt-0.5">
                        Optional keys enhance AI classification and social enrichment features.
                      </p>
                    </div>
                  </>
                )}
              </div>
            )
          })()}

          {settingsLoading && appSettings.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">Loading settings...</div>
          ) : (
            settingGroups.map((group) => {
              const groupSettings = appSettings.filter((s) => group.keys.includes(s.key))
              if (groupSettings.length === 0) return null
              return (
                <div key={group.label} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{group.label}</h3>
                      <span className="text-xs text-gray-400">
                        {groupSettings.filter(s => s.is_set).length}/{groupSettings.length} configured
                      </span>
                    </div>
                    {group.label === 'GitHub' && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Required for fetching repository data, contributors, and stargazers from GitHub.
                      </p>
                    )}
                    {group.label === 'Azure OpenAI' && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Powers AI-driven lead classification and enrichment. Configure either Azure OpenAI or standard OpenAI below.
                      </p>
                    )}
                    {group.label === 'OpenAI (Non-Azure)' && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Alternative to Azure OpenAI. Only needed if you don't have an Azure OpenAI resource.
                      </p>
                    )}
                    {group.label === 'Web Search' && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Used for LinkedIn profile discovery and professional context enrichment via web search.
                      </p>
                    )}
                  </div>
                  <div className="divide-y divide-gray-200 dark:divide-gray-700">
                    {groupSettings.map((setting) => (
                      <div key={setting.key} className="px-6 py-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0 mr-4">
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <code className="text-sm font-mono font-medium text-gray-900 dark:text-gray-100">
                                {setting.key}
                              </code>
                              {setting.required && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 uppercase tracking-wider">
                                  Required
                                </span>
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

                            {/* Hint with help link */}
                            {setting.hint && (
                              <div className="mt-2 flex items-start gap-1.5 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30 rounded-md px-3 py-2">
                                <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                                <span>
                                  {setting.hint}
                                  {setting.help_url && (
                                    <>
                                      {' '}
                                      <a
                                        href={setting.help_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-0.5 font-medium underline hover:text-blue-700 dark:hover:text-blue-300"
                                      >
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
                                  {setting.is_secret && !showSecrets[setting.key]
                                    ? '••••••••'
                                    : setting.value}
                                </code>
                                {setting.is_secret && (
                                  <button
                                    onClick={() => setShowSecrets((prev) => ({ ...prev, [setting.key]: !prev[setting.key] }))}
                                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                    title={showSecrets[setting.key] ? 'Hide value' : 'Show value'}
                                  >
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
                                <button
                                  onClick={() => handleSaveSetting(setting.key, editValue)}
                                  disabled={!editValue || savingKey === setting.key}
                                  className="px-3 py-1.5 text-sm bg-primary hover:bg-primary/90 text-white rounded-lg disabled:opacity-60"
                                >
                                  {savingKey === setting.key ? '...' : 'Save'}
                                </button>
                                <button
                                  onClick={() => { setEditingKey(null); setEditValue('') }}
                                  className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => { setEditingKey(setting.key); setEditValue('') }}
                                  className="px-3 py-1.5 text-sm bg-primary hover:bg-primary/90 text-white rounded-lg"
                                >
                                  {setting.is_set ? 'Update' : 'Set'}
                                </button>
                                {setting.is_set && setting.source === 'database' && (
                                  <button
                                    onClick={() => handleDeleteSetting(setting.key)}
                                    disabled={savingKey === setting.key}
                                    className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                                    title="Remove DB override (will fall back to environment variable if set)"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })
          )}

          {/* How it works info box */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-start gap-3">
              <HelpCircle className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p className="font-medium text-gray-700 dark:text-gray-300">How settings priority works</p>
                <p>Settings can come from two sources. <strong>Database values</strong> (set here) always take priority over <strong>environment variables</strong> (set in .env files or docker-compose).</p>
                <p>Removing a database value will revert to the environment variable if one is set. Secret values are encrypted at rest and masked in the UI.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* User Management Tab */}
      {activeTab === 'users' && user?.is_admin && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage user accounts and permissions
            </p>
            <button
              onClick={() => setShowAddUser(true)}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
            >
              <UserPlus className="w-5 h-5 mr-2" />
              Add User
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="text-gray-600 dark:text-gray-400">Loading users...</div>
            </div>
          ) : users.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-4">
              <div className="rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 p-8 mb-6">
                <Users className="w-16 h-16 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
                No Additional Users Yet
              </h3>
              <p className="text-gray-600 dark:text-gray-400 text-center max-w-md mb-6">
                Invite team members to collaborate on lead sourcing
              </p>
              <button
                onClick={() => setShowAddUser(true)}
                className="px-6 py-3 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
              >
                <UserPlus className="w-5 h-5 mr-2" />
                Add Your First User
              </button>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Role
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Last Login
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{u.full_name || u.username}</div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">@{u.username}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center text-sm text-gray-900 dark:text-gray-100">
                            <Mail className="w-4 h-4 mr-2 text-gray-400" />
                            {u.email}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {u.is_admin ? (
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                              Admin
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
                              User
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {u.is_active ? (
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                              Active
                            </span>
                          ) : (
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200">
                              Inactive
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {u.last_login ? (
                            <div className="flex items-center">
                              <Calendar className="w-4 h-4 mr-2" />
                              {new Date(u.last_login).toLocaleDateString()}
                            </div>
                          ) : (
                            <span className="text-gray-400">Never</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            onClick={() => handleDeleteUser(u.id)}
                            className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300"
                            title="Delete user"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {showAddUser && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Add User</h3>
              <button
                onClick={() => setShowAddUser(false)}
                className="px-2 py-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
                <input
                  type="text"
                  required
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Full Name</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                />
              </div>
              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddUser(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingUser}
                  className="flex-1 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg disabled:opacity-60"
                >
                  {creatingUser ? 'Creating...' : 'Create User'}
                </button>
              </div>
            </form>
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
