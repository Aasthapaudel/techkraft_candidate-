import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../components/AuthContext'

const CATEGORIES = ['Technical', 'Communication', 'Problem Solving', 'Culture Fit', 'Leadership']
const STATUS_OPTIONS = ['new', 'reviewed', 'hired', 'rejected']

export default function CandidateDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Score form
  const [scoreForm, setScoreForm] = useState({ category: 'Technical', score: 3, note: '' })
  const [scoreLoading, setScoreLoading] = useState(false)
  const [scoreError, setScoreError] = useState('')
  const [scoreSuccess, setScoreSuccess] = useState('')

  // AI Summary
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState('')

  // Admin notes
  const [notesEdit, setNotesEdit] = useState(false)
  const [notesValue, setNotesValue] = useState('')
  const [notesSaving, setNotesSaving] = useState(false)

  const fetchCandidate = async () => {
    try {
      const data = await api.getCandidate(id)
      setCandidate(data)
      setNotesValue(data.internal_notes || '')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCandidate() }, [id])

  const handleSubmitScore = async (e) => {
    e.preventDefault()
    setScoreLoading(true)
    setScoreError('')
    setScoreSuccess('')
    try {
      await api.submitScore(id, scoreForm)
      setScoreSuccess('Score submitted!')
      setScoreForm({ category: 'Technical', score: 3, note: '' })
      fetchCandidate()
    } catch (err) {
      setScoreError(err.message)
    } finally {
      setScoreLoading(false)
    }
  }

  const handleTriggerSummary = async () => {
    setSummaryLoading(true)
    setSummaryError('')
    try {
      const data = await api.triggerSummary(id)
      setCandidate(c => ({ ...c, ai_summary: data.summary }))
    } catch (err) {
      setSummaryError(err.message)
    } finally {
      setSummaryLoading(false)
    }
  }

  const handleSaveNotes = async () => {
    setNotesSaving(true)
    try {
      await api.updateCandidate(id, { internal_notes: notesValue })
      setNotesEdit(false)
      setCandidate(c => ({ ...c, internal_notes: notesValue }))
    } catch (err) {
      alert(err.message)
    } finally {
      setNotesSaving(false)
    }
  }

  const handleStatusChange = async (newStatus) => {
    try {
      await api.updateCandidate(id, { status: newStatus })
      setCandidate(c => ({ ...c, status: newStatus }))
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) return <div className="page"><div className="loading-state">Loading…</div></div>
  if (error) return <div className="page"><div className="alert alert-error">{error}</div></div>
  if (!candidate) return null

  const avgScore = candidate.scores.length
    ? (candidate.scores.reduce((s, sc) => s + sc.score, 0) / candidate.scores.length).toFixed(1)
    : null

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-brand">
          <Link to="/candidates" className="back-link">← Candidates</Link>
        </div>
        <div className="topbar-right">
          <span className="role-badge">{user?.role}</span>
          <span className="user-email">{user?.email}</span>
        </div>
      </header>

      <main className="main-content detail-layout">
        {/* Left column: profile + scores */}
        <div className="detail-left">
          {/* Profile card */}
          <div className="card fade-in">
            <div className="profile-header">
              <div className="avatar">{candidate.name.charAt(0)}</div>
              <div>
                <h2>{candidate.name}</h2>
                <p className="text-muted">{candidate.email}</p>
              </div>
            </div>

            <div className="profile-meta">
              <div className="meta-row">
                <span className="meta-label">Role</span>
                <span>{candidate.role_applied}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Status</span>
                {isAdmin ? (
                  <select
                    className="inline-select"
                    value={candidate.status}
                    onChange={e => handleStatusChange(e.target.value)}
                  >
                    {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                ) : (
                  <span className="status-pill">{candidate.status}</span>
                )}
              </div>
              <div className="meta-row">
                <span className="meta-label">Applied</span>
                <span>{new Date(candidate.created_at).toLocaleDateString()}</span>
              </div>
              {avgScore && (
                <div className="meta-row">
                  <span className="meta-label">Avg Score</span>
                  <span className="avg-score">{avgScore} / 5</span>
                </div>
              )}
            </div>

            <div className="skills-section">
              <span className="meta-label">Skills</span>
              <div className="skills-list">
                {(candidate.skills || []).map(s => <span key={s} className="skill-tag">{s}</span>)}
              </div>
            </div>
          </div>

          {/* Scores list */}
          <div className="card fade-in" style={{ animationDelay: '0.1s' }}>
            <h3>
              {isAdmin ? 'All Scores' : 'Your Scores'}
              {candidate.scores.length > 0 && <span className="count-badge">{candidate.scores.length}</span>}
            </h3>
            {candidate.scores.length === 0 ? (
              <p className="text-muted">No scores yet.</p>
            ) : (
              <div className="scores-list">
                {candidate.scores.map(sc => (
                  <div key={sc.id} className="score-item">
                    <div className="score-top">
                      <span className="score-category">{sc.category}</span>
                      <div className="score-stars">
                        {[1,2,3,4,5].map(n => (
                          <span key={n} className={n <= sc.score ? 'star star--filled' : 'star'}>★</span>
                        ))}
                        <span className="score-num">{sc.score}/5</span>
                      </div>
                    </div>
                    {sc.note && <p className="score-note">{sc.note}</p>}
                    <span className="score-date">{new Date(sc.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column: score form + AI summary + admin notes */}
        <div className="detail-right">
          {/* Score form */}
          <div className="card fade-in" style={{ animationDelay: '0.2s' }}>
            <h3>Submit Score</h3>
            <form onSubmit={handleSubmitScore} className="score-form">
              {scoreError && <div className="alert alert-error">{scoreError}</div>}
              {scoreSuccess && <div className="alert alert-success">{scoreSuccess}</div>}

              <div className="field">
                <label>Category</label>
                <select
                  value={scoreForm.category}
                  onChange={e => setScoreForm(f => ({ ...f, category: e.target.value }))}
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="field">
                <label>Score (1–5)</label>
                <div className="star-picker">
                  {[1,2,3,4,5].map(n => (
                    <button
                      key={n}
                      type="button"
                      className={`star-btn ${n <= scoreForm.score ? 'star-btn--active' : ''}`}
                      onClick={() => setScoreForm(f => ({ ...f, score: n }))}
                    >★</button>
                  ))}
                  <span className="score-label">{scoreForm.score}/5</span>
                </div>
              </div>

              <div className="field">
                <label>Note (optional)</label>
                <textarea
                  value={scoreForm.note}
                  onChange={e => setScoreForm(f => ({ ...f, note: e.target.value }))}
                  placeholder="Additional context…"
                  rows={3}
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={scoreLoading}>
                {scoreLoading ? 'Submitting…' : 'Submit Score'}
              </button>
            </form>
          </div>

          {/* AI Summary */}
          <div className="card fade-in" style={{ animationDelay: '0.3s' }}>
            <div className="card-header-row">
              <h3>AI Summary</h3>
              <button
                className="btn btn-secondary"
                onClick={handleTriggerSummary}
                disabled={summaryLoading}
              >
                {summaryLoading ? '⏳ Generating…' : candidate.ai_summary ? '↻ Regenerate' : '✦ Generate'}
              </button>
            </div>

            {summaryError && <div className="alert alert-error">{summaryError}</div>}

            {summaryLoading ? (
              <div className="summary-loading">
                <div className="spinner" />
                <p>Analysing candidate profile… (this takes ~2s)</p>
              </div>
            ) : candidate.ai_summary ? (
              <p className="summary-text">{candidate.ai_summary}</p>
            ) : (
              <p className="text-muted">No summary yet. Click Generate to create one.</p>
            )}
          </div>

          {/* Admin internal notes */}
          {isAdmin && (
            <div className="card card--admin fade-in" style={{ animationDelay: '0.4s' }}>
              <div className="card-header-row">
                <h3>🔒 Internal Notes <span className="admin-only-badge">Admin only</span></h3>
                {!notesEdit && (
                  <button className="btn btn-ghost" onClick={() => setNotesEdit(true)}>Edit</button>
                )}
              </div>

              {notesEdit ? (
                <>
                  <textarea
                    value={notesValue}
                    onChange={e => setNotesValue(e.target.value)}
                    rows={4}
                    className="notes-textarea"
                    placeholder="Private notes visible only to admins…"
                  />
                  <div className="notes-actions">
                    <button className="btn btn-primary" onClick={handleSaveNotes} disabled={notesSaving}>
                      {notesSaving ? 'Saving…' : 'Save'}
                    </button>
                    <button className="btn btn-ghost" onClick={() => { setNotesEdit(false); setNotesValue(candidate.internal_notes || '') }}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <p className="notes-text">{candidate.internal_notes || <em className="text-muted">No notes yet.</em>}</p>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
