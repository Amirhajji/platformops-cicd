import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, type Role, type User } from '../api'
import { Card, ErrorBox, Loaded, PageTitle } from '../components/States'
import { formatTime } from '../format'
import { useAuth } from '../session'
import { useLoad } from '../useLoad'

const messageOf = (error: unknown) => (error instanceof Error ? error.message : 'Unexpected error')

export function Users() {
  const { user } = useAuth()
  if (user?.role !== 'admin') {
    return (
      <>
        <PageTitle title="Users" />
        <ErrorBox message="This page needs the admin role." />
      </>
    )
  }
  return <UserAdmin me={user} />
}

function UserAdmin({ me }: { me: User }) {
  const load = useLoad((signal) => api.users(signal), [])
  const [error, setError] = useState<string>()
  const [confirming, setConfirming] = useState<number>()
  const [busy, setBusy] = useState(false)

  const remove = async (user: User) => {
    setBusy(true)
    setError(undefined)
    try {
      await api.deleteUser(user.id)
      load.reload()
    } catch (failure) {
      setError(messageOf(failure))
    }
    setConfirming(undefined)
    setBusy(false)
  }

  return (
    <>
      <PageTitle title="Users" />
      <Card title="New user">
        <CreateUser onCreated={load.reload} />
      </Card>
      <Card title="Accounts">
        {error && <ErrorBox message={error} />}
        <Loaded load={load}>
          {(users) => (
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Created (UTC)</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>
                        {user.username} {user.id === me.id && <span className="note">(you)</span>}
                      </td>
                      <td>{user.role}</td>
                      <td>{formatTime(user.created_at)}</td>
                      <td className="actions">
                        {user.id === me.id ? null : confirming === user.id ? (
                          <>
                            <span>Delete {user.username}?</span>
                            <button
                              type="button"
                              className="button danger"
                              disabled={busy}
                              onClick={() => remove(user)}
                            >
                              Delete
                            </button>
                            <button
                              type="button"
                              className="button"
                              onClick={() => setConfirming(undefined)}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            className="button"
                            aria-label={`Delete ${user.username}`}
                            onClick={() => setConfirming(user.id)}
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Loaded>
      </Card>
    </>
  )
}

function CreateUser({ onCreated }: { onCreated: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('viewer')
  const [error, setError] = useState<string>()
  const [created, setCreated] = useState<string>()
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(undefined)
    setCreated(undefined)
    try {
      const user = await api.createUser(username, password, role)
      setCreated(`User ${user.username} created.`)
      setUsername('')
      setPassword('')
      onCreated()
    } catch (failure) {
      setError(messageOf(failure))
    }
    setBusy(false)
  }

  return (
    <form className="filters" onSubmit={submit}>
      <label>
        Username
        <input
          required
          minLength={3}
          maxLength={64}
          pattern="[A-Za-z0-9._\-]+"
          title="Letters, digits, dot, underscore or dash"
          autoComplete="off"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </label>
      <label>
        Password (8 characters or more)
        <input
          type="password"
          required
          minLength={8}
          maxLength={128}
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      <label>
        Role
        <select value={role} onChange={(event) => setRole(event.target.value as Role)}>
          <option value="viewer">viewer</option>
          <option value="admin">admin</option>
        </select>
      </label>
      <button type="submit" className="button primary" disabled={busy}>
        Create
      </button>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      {created && (
        <p className="field-ok" role="status">
          {created}
        </p>
      )}
    </form>
  )
}
