import { useState } from 'react'
import ProfileCard from './ProfileCard'
import InsightSection from './InsightSection'

function Dossier({ data, onReset, onExportNotion }) {
  const [activeTab, setActiveTab] = useState('team')

  // Flatten all members across groups, sort alphabetically
  const allMembers = data.groups
    .flatMap((g) => g.members)
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <div className="dossier">
      <div className="dossier-header">
        <h2 className="dossier-company">{data.company}</h2>
        <div className="dossier-meta">
          {data.team_count} members
        </div>
      </div>

      <div className="dossier-tabs">
        <button
          className={`tab-btn ${activeTab === 'team' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('team')}
        >
          Team ({allMembers.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'insights' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('insights')}
        >
          Insights
        </button>
      </div>

      {activeTab === 'team' && (
        <div className="tab-content">
          <div className="profile-grid">
            {allMembers.map((member, j) => (
              <ProfileCard key={j} member={member} />
            ))}
          </div>
        </div>
      )}

      {activeTab === 'insights' && (
        <div className="tab-content">
          {data.insights && data.insights.length > 0 ? (
            data.insights.map((insight, i) => (
              <InsightSection
                key={i}
                title={insight.title}
                content={insight.content}
              />
            ))
          ) : (
            <p style={{ color: 'var(--text-dim)', padding: '2rem 0' }}>
              No insights generated.
            </p>
          )}
        </div>
      )}

      <div className="dossier-actions">
        <button className="action-btn action-btn-primary" onClick={onExportNotion}>
          Export to Notion
        </button>
        <button className="action-btn action-btn-secondary" onClick={onReset}>
          Generate Another
        </button>
      </div>
    </div>
  )
}

export default Dossier
