import ProfileCard from './ProfileCard'
import InsightSection from './InsightSection'

function Dossier({ data, onReset, onExportNotion }) {
  const groupSummary = data.groups
    .map((g) => `${g.name} (${g.count})`)
    .join(' · ')

  return (
    <div className="dossier">
      <div className="dossier-header">
        <h2 className="dossier-company">{data.company}</h2>
        <div className="dossier-meta">
          {data.team_count} members · {groupSummary}
        </div>
      </div>

      <div className="dossier-actions">
        <button className="action-btn action-btn-primary" onClick={onExportNotion}>
          Export to Notion
        </button>
        <button className="action-btn action-btn-secondary" onClick={onReset}>
          Generate Another
        </button>
      </div>

      {/* Insight sections first — the analytical value */}
      {data.insights && data.insights.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          {data.insights.map((insight, i) => (
            <InsightSection
              key={i}
              title={insight.title}
              content={insight.content}
            />
          ))}
        </div>
      )}

      {/* Team member sections */}
      {data.groups.map((group, i) => (
        <details key={i} className="section-toggle">
          <summary>
            <span className="section-title">{group.name}</span>
            <span className="section-count">{group.count}</span>
          </summary>
          <div className="section-content">
            <div className="profile-grid">
              {group.members.map((member, j) => (
                <ProfileCard key={j} member={member} />
              ))}
            </div>
          </div>
        </details>
      ))}
    </div>
  )
}

export default Dossier
