import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Building2, Plus, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

export default function SelectOrg() {
  const { user, selectOrg, logout, refreshUser } = useAuth()
  const orgs = user?.organizations || []
  const [showCreate, setShowCreate] = useState(false)
  const [newOrgName, setNewOrgName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const handleCreateOrg = async () => {
    if (!newOrgName.trim()) return
    setCreating(true)
    setError('')
    try {
      const org = await api.createOrganization(newOrgName.trim())
      await refreshUser()
      selectOrg(org.id)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create organization')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Building2 className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white">Select Organization</h1>
          <p className="text-gray-400 mt-2">Choose which organization to work in</p>
        </div>

        <div className="space-y-3">
          {orgs.map((org) => (
            <button
              key={org.id}
              onClick={() => selectOrg(org.id)}
              className="w-full flex items-center gap-4 p-4 rounded-lg border border-gray-700 bg-gray-900 hover:border-cyan-500 hover:bg-gray-800 transition-colors text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-cyan-400" />
              </div>
              <div className="flex-1">
                <div className="text-white font-medium">{org.name}</div>
                <div className="text-gray-500 text-sm">{org.slug} &middot; {org.role}</div>
              </div>
            </button>
          ))}
        </div>

        {user?.is_admin && (
          <div className="mt-4">
            {showCreate ? (
              <div className="p-4 rounded-lg border border-gray-700 bg-gray-900 space-y-3">
                <input
                  type="text"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateOrg()}
                  placeholder="Organization name"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  autoFocus
                />
                {error && <p className="text-red-400 text-sm">{error}</p>}
                <div className="flex gap-2">
                  <button
                    onClick={handleCreateOrg}
                    disabled={creating || !newOrgName.trim()}
                    className="flex-1 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 inline-flex items-center justify-center gap-2"
                  >
                    {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    Create
                  </button>
                  <button
                    onClick={() => { setShowCreate(false); setNewOrgName(''); setError('') }}
                    className="px-3 py-2 text-gray-400 hover:text-gray-200 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowCreate(true)}
                className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed border-gray-600 text-gray-400 hover:border-cyan-500 hover:text-cyan-400 transition-colors text-sm"
              >
                <Plus className="w-4 h-4" />
                Create New Organization
              </button>
            )}
          </div>
        )}

        <button
          onClick={logout}
          className="mt-6 w-full text-center text-gray-500 hover:text-gray-300 text-sm"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
