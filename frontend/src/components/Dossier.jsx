import { useState } from 'react'
import ProfileCard from './ProfileCard'
import InsightSection from './InsightSection'

function Dossier({ data, onReset, onExportNotion, tab, onTabChange }) {
  // Controlled by the URL on a shared dossier; local state on the transient
  // post-generation render, which has no slug to put in the address bar yet.
  const [localTab, setLocalTab] = useState('team')
  const activeTab = tab ?? localTab
  const setActiveTab = onTabChange ?? setLocalTab

  // Flatten all members across groups, sort alphabetically by last name
  const allMembers = data.groups.flatMap((g) => g.members).sort((a, b) => {
    const lastA = (a.name || '').trim().split(/\s+/).pop().toLowerCase()
    const lastB = (b.name || '').trim().split(/\s+/).pop().toLowerCase()
    return lastA.localeCompare(lastB)
  })

  return (
    <div className="dossier">
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

      <div className="dossier-header">
        <h2 className="dossier-company">{data.company}</h2>
        <div className="dossier-meta">
          {data.team_count} members
          {data.source_url && (
            <>
              {' · '}
              <a
                className="dossier-source-link"
                href={data.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {data.source_url}
              </a>
            </>
          )}
        </div>
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
          {data.unsupported_claims?.length > 0 && (
            <div className="grounding-warning">
              <strong>{data.unsupported_claims.length} claim
              {data.unsupported_claims.length === 1 ? '' : 's'} could not be traced to the
              source pages</strong> and may be wrong:
              <ul>
                {data.unsupported_claims.map((c, i) => (
                  <li key={i}>{c.person} — {c.claim}</li>
                ))}
              </ul>
            </div>
          )}
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
