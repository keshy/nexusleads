import { useAuth } from '../contexts/AuthContext'
import { Building2 } from 'lucide-react'

export default function SelectOrg() {
  const { user, selectOrg, logout } = useAuth()
  const orgs = user?.organizations || []

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
