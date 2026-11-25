import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../session'

export function Login() {
  const { user, expired, login } = useAuth()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    document.title = 'Log in · PlatformOPS'
  }, [])

  if (user) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? '/overview'} replace />
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(undefined)
    try {
      await login(username, password)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Unexpected error')
      setPassword('')
      setBusy(false)
    }
  }

  return (
    <main className="login">
      <form className="card" onSubmit={submit}>
        <div className="brand">
          <img src="/favicon.svg" alt="" width="34" height="34" /> PlatformOPS
        </div>
        <p className="note">Monitoring of the simulated Huawei Cloud telemetry platform</p>
        {expired && !error && (
          <p className="field-error" role="alert">
            Your session has ended. Please log in again.
          </p>
        )}
        <label>
          Username
          <input
            autoComplete="username"
            autoFocus
            required
            maxLength={64}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button primary" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </main>
  )
}
