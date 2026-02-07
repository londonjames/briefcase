import { useState } from 'react'

function ProfileCard({ member }) {
  const [expanded, setExpanded] = useState(false)
  const initials = member.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)

  const hasDetails =
    (member.education && member.education.length > 0) ||
    (member.career && member.career.length > 0) ||
    (member.personal && member.personal.length > 0)

  return (
    <div className="profile-card">
      <div className="profile-top">
        {member.photo_url ? (
          <img
            className="profile-photo"
            src={member.photo_url}
            alt={member.name}
            loading="lazy"
          />
        ) : (
          <div className="profile-photo-placeholder">{initials}</div>
        )}
        <div>
          <div className="profile-name">{member.name}</div>
          {member.title && <div className="profile-title">{member.title}</div>}
        </div>
      </div>

      {member.bio && (
        <div
          className={`profile-bio ${expanded ? 'profile-bio-full' : ''}`}
          onClick={() => setExpanded(!expanded)}
          style={{ cursor: 'pointer' }}
        >
          {member.bio}
        </div>
      )}

      {hasDetails && (
        <details className="profile-details">
          <summary />
          {member.education && member.education.length > 0 && (
            <>
              <div className="profile-section-label">Education</div>
              <ul className="profile-list">
                {member.education.map((edu, i) => (
                  <li key={i}>
                    {edu.school}
                    {edu.degree && ` — ${edu.degree}`}
                    {edu.honors && ` (${edu.honors})`}
                  </li>
                ))}
              </ul>
            </>
          )}
          {member.career && member.career.length > 0 && (
            <>
              <div className="profile-section-label">Career</div>
              <ul className="profile-list">
                {member.career.map((c, i) => (
                  <li key={i}>
                    {c.company} — {c.role}
                  </li>
                ))}
              </ul>
            </>
          )}
          {member.personal && member.personal.length > 0 && (
            <>
              <div className="profile-section-label">Personal</div>
              <ul className="profile-list">
                {member.personal.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </>
          )}
        </details>
      )}
    </div>
  )
}

export default ProfileCard
