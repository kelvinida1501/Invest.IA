import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './Pages/Login'
import Dashboard from './Pages/Dashboard'
import './Styles/global.css'

function AppRouter() {
  const [token, setToken] = React.useState<string | null>(() => localStorage.getItem('token'))

  React.useEffect(() => {
    const update = () => setToken(localStorage.getItem('token'))
    // dispara quando outra aba altera o storage
    window.addEventListener('storage', update)
    // evento custom pra esta própria aba
    window.addEventListener('auth-changed', update as any)
    return () => {
      window.removeEventListener('storage', update)
      window.removeEventListener('auth-changed', update as any)
    }
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={token ? <Dashboard /> : <Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')!).render(<AppRouter />)
