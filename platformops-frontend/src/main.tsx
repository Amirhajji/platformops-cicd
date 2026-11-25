import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Empty, PageTitle } from './components/States'
import { ComponentPage } from './pages/ComponentPage'
import { Alerts, IncidentPage, Incidents } from './pages/Detections'
import { Explorer } from './pages/Explorer'
import { Login } from './pages/Login'
import { Overview } from './pages/Overview'
import { Users } from './pages/Users'
import { AuthProvider, RunProvider, useAuth } from './session'
import './styles.css'

/** Everything except the login page. After the login, go back to the wanted page. */
function Private() {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return (
    <RunProvider>
      <Layout />
    </RunProvider>
  )
}

function NotFound() {
  return (
    <>
      <PageTitle title="Page not found" />
      <Empty>
        <Link to="/overview">Go to the overview</Link>
      </Empty>
    </>
  )
}

// HashRouter: deep links survive a page refresh whatever the web server does.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Private />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/components/:id" element={<ComponentPage />} />
            <Route path="/metrics" element={<Explorer />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route path="/incidents/:id" element={<IncidentPage />} />
            <Route path="/users" element={<Users />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </HashRouter>
  </StrictMode>,
)
