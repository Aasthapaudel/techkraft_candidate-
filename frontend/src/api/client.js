const BASE = import.meta.env.VITE_API_URL || ''

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 204) return null
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Request failed')
  return data
}

export const api = {
  // Auth
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/auth/me'),

  // Candidates
  getCandidates: (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== '' && v != null) q.set(k, v) })
    return request(`/candidates?${q.toString()}`)
  },
  getCandidate: (id) => request(`/candidates/${id}`),
  createCandidate: (data) =>
    request('/candidates', { method: 'POST', body: JSON.stringify(data) }),
  updateCandidate: (id, data) =>
    request(`/candidates/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteCandidate: (id) =>
    request(`/candidates/${id}`, { method: 'DELETE' }),

  // Scores
  submitScore: (candidateId, data) =>
    request(`/candidates/${candidateId}/scores`, { method: 'POST', body: JSON.stringify(data) }),

  // AI Summary
  triggerSummary: (candidateId) =>
    request(`/candidates/${candidateId}/summary`, { method: 'POST' }),
}
