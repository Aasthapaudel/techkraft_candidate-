import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../components/AuthContext'

const STATUS_COLORS = {
  new: '#3b82f6',
  reviewed: '#f59e0b',
  hired: '#10b981',
  rejected: '#ef4444',
  archived: '#9ca3af',
}

const ROLES = ['', 'Frontend Engineer', 'Backend Engineer', 'Full Stack Engineer', 'DevOps Engineer']
const STATUSES = ['', 'new', 'reviewed', 'hired', 'rejected']

export default function CandidatesPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [filters, setFilters] = useState({ status: '', role_applied: '', skill: '', keyword: '' })
  const [offset, setOffset] = useState(0)
  const PAGE_SIZE = 10

  const fetchCandidates = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getCandidates({ ...filters, offset, page_size: PAGE_SIZE })
      setCandidates(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCandidates() }, [filters, offset])

  const updateFilter = (key, val) => {
    setFilters(f => ({ ...f, [key]: val }))
    setOffset(0)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-icon-sm">TK</span>
          <span>TechKraft Recruitment</span>
        </div>
        <div className="topbar-right">
          <span className="role-badge role-badge--{user?.role}">{user?.role}</span>
          <span className="user-email">{user?.email}</span>
          <button className="btn btn-ghost" onClick={() => { logout(); navigate('/login') }}>Sign out</button>
        </div>
      </header>

      <main className="main-content">
        <div className="page-header">
          <h2>Candidates</h2>
          <span className="total-count">{total} total</span>
        </div>

        {/* Filters */}
        <div className="filter-bar">
          <input
            className="filter-input"
            placeholder="Search name, email, role…"
            value={filters.keyword}
            onChange={e => updateFilter('keyword', e.target.value)}
          />
          <select className="filter-select" value={filters.status} onChange={e => updateFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="filter-select" value={filters.role_applied} onChange={e => updateFilter('role_applied', e.target.value)}>
            {ROLES.map(r => <option key={r} value={r}>{r || 'All roles'}</option>)}
          </select>
          <input
            className="filter-input"
            placeholder="Skill (e.g. React)"
            value={filters.skill}
            onChange={e => updateFilter('skill', e.target.value)}
          />
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {loading ? (
          <div className="loading-state">Loading candidates…</div>
        ) : candidates.length === 0 ? (
          <div className="empty-state">No candidates match your filters.</div>
        ) : (
          <div className="candidate-table">
            <div className="table-header">
              <span>Name</span>
              <span>Role</span>
              <span>Skills</span>
              <span>Status</span>
              <span>Applied</span>
            </div>
            {candidates.map(c => (
              <Link key={c.id} to={`/candidates/${c.id}`} className="table-row">
                <span className="candidate-name">{c.name}</span>
                <span className="candidate-role">{c.role_applied}</span>
                <span className="candidate-skills">
                  {(c.skills || []).slice(0, 3).map(s => (
                    <span key={s} className="skill-tag">{s}</span>
                  ))}
                  {c.skills?.length > 3 && <span className="skill-more">+{c.skills.length - 3}</span>}
                </span>
                <span>
                  <span className="status-badge" style={{ background: STATUS_COLORS[c.status] + '22', color: STATUS_COLORS[c.status] }}>
                    {c.status}
                  </span>
                </span>
                <span className="candidate-date">{new Date(c.created_at).toLocaleDateString()}</span>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button className="btn btn-ghost" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))}>
              ← Prev
            </button>
            <span>Page {currentPage} of {totalPages}</span>
            <button className="btn btn-ghost" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(o => o + PAGE_SIZE)}>
              Next →
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
