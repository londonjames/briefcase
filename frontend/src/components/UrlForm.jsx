import { useState } from 'react'
import { Link } from 'react-router-dom'

function UrlForm({ onSubmit, error }) {
  const [url, setUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return
    setSubmitting(true)
    await onSubmit(url.trim())
    setSubmitting(false)
  }

  return (
    <form className="url-form" onSubmit={handleSubmit}>
      <div className="url-form-inner">
        <input
          type="url"
          className="url-input"
          placeholder="https://company.com/team"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          disabled={submitting}
        />
        <button
          type="submit"
          className="submit-btn"
          disabled={submitting || !url.trim()}
        >
          {submitting ? 'Starting...' : 'Generate'}
        </button>
      </div>
      <p className="form-hint">
        Enter any team or leadership page URL
      </p>
      <p className="form-samples">
        A few samples:{' '}
        <Link to="/linkedin/10March2026">LinkedIn</Link>,{' '}
        <Link to="/meta/10March2026">Meta</Link>,{' '}
        <Link to="/nvidia/10March2026">NVIDIA</Link>,{' '}
        <Link to="/apple/10March2026">Apple</Link>,{' '}
        <Link to="/sequoia-capital/10March2026">Sequoia</Link>
      </p>
      {error && <p className="form-error">{error}</p>}
    </form>
  )
}

export default UrlForm
