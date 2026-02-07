import { useState, useEffect, useRef } from 'react'

function Progress({ progress, step, status }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const phase2StartRef = useRef(null)
  const timerRef = useRef(null)

  const isPhase2 = progress >= 75

  // Start/stop elapsed timer for phase 2
  useEffect(() => {
    if (isPhase2 && !phase2StartRef.current) {
      phase2StartRef.current = Date.now()
      timerRef.current = setInterval(() => {
        setElapsedSeconds(Math.floor((Date.now() - phase2StartRef.current) / 1000))
      }, 1000)
    }
    if (!isPhase2) {
      phase2StartRef.current = null
      setElapsedSeconds(0)
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isPhase2])

  // Parse profile count from step text like "Fetching profiles (12/63)..."
  const countMatch = step?.match(/\((\d+)\/(\d+)\)/)
  const profileCurrent = countMatch ? parseInt(countMatch[1], 10) : null
  const profileTotal = countMatch ? parseInt(countMatch[2], 10) : null

  // Map backend progress to display progress
  let displayProgress
  if (!isPhase2) {
    // Backend 0-70 → display 0-50
    displayProgress = Math.round((Math.min(progress, 70) / 70) * 50)
  } else {
    // Backend 75-95 → display 50-95
    const phase2Pct = Math.min(Math.max(progress - 75, 0), 20) / 20
    displayProgress = Math.round(50 + phase2Pct * 45)
  }
  if (progress >= 100) displayProgress = 100

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`
  }

  return (
    <div className="progress-container">
      <div className="progress-phases">
        <div className={`progress-phase ${!isPhase2 ? 'progress-phase-active' : 'progress-phase-done'}`}>
          <span className="progress-phase-number">1</span>
          <span className="progress-phase-label">Pulling Profiles</span>
        </div>
        <div className="progress-phase-connector" />
        <div className={`progress-phase ${isPhase2 ? 'progress-phase-active' : ''}`}>
          <span className="progress-phase-number">2</span>
          <span className="progress-phase-label">Generating Insights</span>
        </div>
      </div>

      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${displayProgress}%` }}
        />
      </div>

      <div className="progress-detail-area">
        {!isPhase2 ? (
          <>
            <div className="progress-detail">
              {profileCurrent !== null ? (
                <>
                  <span className="progress-spinner" />
                  {profileCurrent} <span className="progress-detail-dim">/ {profileTotal}</span>
                </>
              ) : (
                <>
                  <span className="progress-spinner" />
                  <span className="progress-detail-small">Analyzing team page…</span>
                </>
              )}
            </div>
            {profileCurrent !== null && (
              <div className="progress-subtext">profiles pulled</div>
            )}
          </>
        ) : (
          <>
            <div className="progress-detail">
              <span className="progress-spinner" />
              {formatTime(elapsedSeconds)}
            </div>
            <div className="progress-subtext">
              This usually takes 60–90 seconds. Stay tuned.
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Progress
