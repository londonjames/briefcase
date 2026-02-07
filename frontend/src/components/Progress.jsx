function Progress({ progress, step, status }) {
  return (
    <div className="progress-container">
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="progress-pct">{progress}%</div>
      <div className="progress-step">
        {status !== 'complete' && <span className="progress-spinner" />}
        {step}
      </div>
    </div>
  )
}

export default Progress
