/**
 * Users & Roles management tab.
 * Lists users, allows role assignment, user creation, and deactivation.
 */

import { useCallback, useEffect, useState } from 'react'
import { api } from '@/utils/api'

interface UserItem {
  userId: string
  email: string
  displayName: string
  isActive: boolean
  roles: Array<{ roleName: string; buScope: string[] }>
  persona: string
}

interface RoleItem {
  id: number
  roleName: string
  description: string
  personaType: string
  isSystem: boolean
}

export function AdminUsersTab() {
  const [users, setUsers] = useState<UserItem[]>([])
  const [roles, setRoles] = useState<RoleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newName, setNewName] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState('analyst')
  const [toast, setToast] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [usersData, rolesData] = await Promise.all([
        api.gateway.get<{ users: UserItem[]; total: number }>('/admin/users'),
        api.gateway.get<RoleItem[]>('/admin/roles'),
      ])
      setUsers(usersData.users || [])
      setRoles(rolesData || [])
    } catch {
      // fallback
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = useCallback(async () => {
    try {
      await api.gateway.post('/admin/users', {
        email: newEmail,
        display_name: newName,
        password: newPassword,
        role_name: newRole,
      })
      setShowCreate(false)
      setNewEmail('')
      setNewName('')
      setNewPassword('')
      setToast('User created')
      setTimeout(() => setToast(null), 3000)
      fetchData()
    } catch (err: any) {
      setToast(err?.detail || 'Failed to create user')
      setTimeout(() => setToast(null), 3000)
    }
  }, [newEmail, newName, newPassword, newRole, fetchData])

  const handleDeactivate = useCallback(async (userId: string) => {
    try {
      await api.gateway.delete(`/admin/users/${userId}`)
      setToast('User deactivated')
      setTimeout(() => setToast(null), 3000)
      fetchData()
    } catch {
      setToast('Failed to deactivate')
      setTimeout(() => setToast(null), 3000)
    }
  }, [fetchData])

  return (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="section-label">USERS & ROLES</span>
        <div className="flex items-center gap-2">
          {toast && (
            <span className={`text-[10px] px-2 py-1 rounded ${toast.includes('created') || toast.includes('deactivated') ? 'bg-emerald/10 text-emerald' : 'bg-coral/10 text-coral'}`}>
              {toast}
            </span>
          )}
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-3 py-1 rounded-lg text-[10px] font-medium bg-accent/10 text-accent border border-accent/30 hover:bg-accent/20 transition-colors"
          >
            {showCreate ? 'Cancel' : '+ Add User'}
          </button>
        </div>
      </div>

      {/* Create user form */}
      {showCreate && (
        <div className="p-3 rounded-lg bg-surface/50 border border-accent/20 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Display name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="px-2 py-1.5 rounded bg-surface border border-border text-text text-[11px] focus:outline-none focus:ring-1 focus:ring-accent/50"
            />
            <input
              type="email"
              placeholder="Email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="px-2 py-1.5 rounded bg-surface border border-border text-text text-[11px] focus:outline-none focus:ring-1 focus:ring-accent/50"
            />
            <input
              type="password"
              placeholder="Password (min 6)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="px-2 py-1.5 rounded bg-surface border border-border text-text text-[11px] focus:outline-none focus:ring-1 focus:ring-accent/50"
            />
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="px-2 py-1.5 rounded bg-surface border border-border text-text text-[11px] focus:outline-none focus:ring-1 focus:ring-accent/50"
            >
              {roles.map((r) => (
                <option key={r.roleName} value={r.roleName}>{r.roleName}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleCreate}
            className="px-3 py-1 rounded-lg text-[10px] font-medium text-white"
            style={{ background: 'linear-gradient(135deg, var(--cobalt), var(--accent))' }}
          >
            Create User
          </button>
        </div>
      )}

      {/* User table */}
      {loading ? (
        <div className="text-center py-8 text-text-secondary text-[11px]">Loading users...</div>
      ) : (
        <div className="space-y-1.5">
          {users.map((u) => (
            <div
              key={u.userId}
              className={`flex items-center justify-between p-2.5 rounded-lg border transition-colors ${
                u.isActive
                  ? 'bg-surface/30 border-border/30 hover:border-accent/20'
                  : 'bg-surface/10 border-border/20 opacity-50'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-text truncate">{u.displayName}</span>
                  {!u.isActive && (
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-coral/10 text-coral">Inactive</span>
                  )}
                </div>
                <div className="text-[9px] text-text-secondary">{u.email}</div>
              </div>

              <div className="flex items-center gap-2">
                {u.roles.map((r) => (
                  <span
                    key={r.roleName}
                    className="text-[8px] px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20"
                  >
                    {r.roleName}
                  </span>
                ))}
                {u.isActive && (
                  <button
                    onClick={() => handleDeactivate(u.userId)}
                    className="text-[9px] px-2 py-0.5 rounded text-coral hover:bg-coral/10 transition-colors"
                    title="Deactivate user"
                  >
                    Deactivate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Roles reference */}
      <div className="mt-4 pt-3 border-t border-border/30">
        <span className="section-label">SYSTEM ROLES</span>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {roles.filter((r) => r.isSystem).map((r) => (
            <div key={r.roleName} className="text-[9px] flex justify-between">
              <span className="text-accent font-medium">{r.roleName}</span>
              <span className="text-text-secondary">{r.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
