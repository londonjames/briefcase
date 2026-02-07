import { useState, useEffect, useCallback } from 'react'
import UrlForm from './components/UrlForm'
import Progress from './components/Progress'
import Dossier from './components/Dossier'

const getApiUrl = () => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }
  return 'http://localhost:5002/api'
}

const API_URL = getApiUrl()

function App() {
  const [view, setView] = useState('form') // form | progress | dossier
  const [jobId, setJobId] = useState(null)
  const [progress, setProgress] = useState({ progress: 0, step: '', status: 'pending' })
  const [dossier, setDossier] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async (url) => {
    setError(null)
    setView('progress')
    setProgress({ progress: 0, step: 'Submitting...', status: 'pending' })

    try {
      const resp = await fetch(`${API_URL}/dossier`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.error || 'Failed to start job')
      }
      const data = await resp.json()
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
      setView('form')
    }
  }

  const pollJob = useCallback(async () => {
    if (!jobId) return

    try {
      const resp = await fetch(`${API_URL}/dossier/${jobId}`)
      const data = await resp.json()

      setProgress({
        progress: data.progress,
        step: data.step,
        status: data.status,
      })

      if (data.status === 'complete') {
        setDossier(data.result)
        setView('dossier')
      } else if (data.status === 'error') {
        setError(data.step)
        setView('form')
      }
    } catch (e) {
      // Network error — keep polling
    }
  }, [jobId])

  useEffect(() => {
    if (view !== 'progress' || !jobId) return

    const interval = setInterval(pollJob, 2000)
    pollJob() // Immediate first poll
    return () => clearInterval(interval)
  }, [view, jobId, pollJob])

  const handleReset = () => {
    setView('form')
    setJobId(null)
    setDossier(null)
    setProgress({ progress: 0, step: '', status: 'pending' })
    setError(null)
  }

  const handleExportNotion = async () => {
    if (!jobId) return

    try {
      const resp = await fetch(`${API_URL}/dossier/${jobId}/export-notion`, {
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
        <h1 className="app-title">briefcase</h1>
        <p className="app-subtitle">team dossier generator</p>
      </header>

      <main className="app-main">
        {view === 'form' && (
          <UrlForm onSubmit={handleSubmit} error={error} />
        )}
        {view === 'progress' && (
          <Progress
            progress={progress.progress}
            step={progress.step}
            status={progress.status}
          />
        )}
        {view === 'dossier' && dossier && (
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

export default App
