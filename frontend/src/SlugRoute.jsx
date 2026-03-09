import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Dossier from './components/Dossier'

const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  return 'http://localhost:5002/api'
}

const API_URL = getApiUrl()

function SlugRoute() {
  const { company, date } = useParams()
  const navigate = useNavigate()
  const [dossier, setDossier] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const slug = `${company}/${date}`

    // Try localStorage first
    const cached = localStorage.getItem(`briefcase:${slug}`)
    if (cached) {
      try {
        setDossier(JSON.parse(cached))
        setLoading(false)
        return
      } catch {
        // corrupted, fall through to API
      }
    }

    // Fetch from backend
    fetch(`${API_URL}/dossier/by-slug/${slug}`)
      .then((resp) => {
        if (!resp.ok) throw new Error('Not found')
        return resp.json()
      })
      .then((data) => {
        setDossier(data.result)
        // Cache for future visits
        localStorage.setItem(`briefcase:${slug}`, JSON.stringify(data.result))
      })
      .catch(() => {
        setError('This dossier was not found. It may have expired.')
      })
      .finally(() => setLoading(false))
  }, [company, date])

  const handleReset = () => navigate('/')

  const handleExportNotion = async () => {
    if (!dossier?.dossier_id) return
    try {
      const resp = await fetch(`${API_URL}/dossier/${dossier.dossier_id}/export-notion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await resp.json()
      if (data.notion_url) {
        window.open(data.notion_url, '_blank')
      } else {
        alert(data.error || 'Export failed')
      }
    } catch (e) {
      alert('Export failed: ' + e.message)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          briefcase
        </h1>
        <p className="app-subtitle">team dossier generator</p>
      </header>

      <main className="app-main">
        {loading && (
          <div style={{ textAlign: 'center', padding: '4rem 0' }}>
            <div className="progress-spinner" style={{ width: '2rem', height: '2rem' }} />
            <p style={{ color: 'var(--text-dim)', marginTop: '1rem' }}>Loading dossier...</p>
          </div>
        )}
        {error && (
          <div style={{ textAlign: 'center', padding: '4rem 0' }}>
            <p style={{ color: 'var(--text-dim)', marginBottom: '1.5rem' }}>{error}</p>
            <button className="action-btn action-btn-primary" onClick={() => navigate('/')}>
              Generate a Dossier
            </button>
          </div>
        )}
        {dossier && (
          <Dossier
            data={dossier}
            onReset={handleReset}
            onExportNotion={handleExportNotion}
          />
        )}
      </main>
    </div>
  )
}

export default SlugRoute
