import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './components/AuthContext'
import LoginPage from './pages/LoginPage'
import CandidatesPage from './pages/CandidatesPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import './styles.css'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading-state">Loading…</div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/candidates" element={<PrivateRoute><CandidatesPage /></PrivateRoute>} />
          <Route path="/candidates/:id" element={<PrivateRoute><CandidateDetailPage /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/candidates" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
