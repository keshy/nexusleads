import { useState, useEffect } from 'react'
import { Users, UserPlus, Trash2, Shield, Mail, Calendar } from 'lucide-react'
import axios from 'axios'

interface User {
  id: string
  username: string
  email: string
  full_name?: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  last_login?: string
}

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [_showAddDialog, setShowAddDialog] = useState(false)

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const response = await axios.get('/api/users', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
      setUsers(response.data)
    } catch (error) {
      console.error('Error fetching users:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading users...</div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">User Management</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage team access and permissions
          </p>
        </div>
        <button
          onClick={() => setShowAddDialog(true)}
          className="px-4 py-2 bg-primary hover:bg-primary/90 text-white font-medium rounded-lg transition-colors inline-flex items-center"
        >
          <UserPlus className="w-5 h-5 mr-2" />
          Add User
        </button>
      </div>

      {users.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4">
          <div className="rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 p-8 mb-6">
            <Users className="w-16 h-16 text-indigo-600 dark:text-indigo-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">
            No Additional Users Yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-center max-w-2xl mb-8 leading-relaxed">
            Invite team members to collaborate on lead sourcing. Each user can have their own projects 
            and access levels. Administrators can manage all users and settings.
          </p>
          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mb-8">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Shield className="w-10 h-10 text-blue-600 dark:text-blue-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Role-Based Access</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Set admin privileges or standard user access for each team member
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
              <Users className="w-10 h-10 text-purple-600 dark:text-purple-400 mb-3" />
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">Team Collaboration</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Multiple users can work on projects and track leads together
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAddDialog(true)}
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
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{user.full_name || user.username}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">@{user.username}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900 dark:text-gray-100">
                        <Mail className="w-4 h-4 mr-2 text-gray-400" />
                        {user.email}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_admin ? (
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
                      {user.is_active ? (
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
                      {user.last_login ? (
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 mr-2" />
                          {new Date(user.last_login).toLocaleDateString()}
                        </div>
                      ) : (
                        <span className="text-gray-400">Never</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
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
  )
}
