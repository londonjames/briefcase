import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5002/api'

function ProfileCard({ member }) {
  // A photo that fails to load used to leave a bare grey disc, because the
  // initials only stood in when the URL was missing entirely. Now any failure
  // — blocked host, dead link, unsupported format — falls back to the initials.
  const [photoFailed, setPhotoFailed] = useState(false)

  const initials = member.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)

  const photoSrc =
    member.photo_url && !photoFailed
      ? `${API_URL}/image-proxy?url=${encodeURIComponent(member.photo_url)}`
      : null

  return (
    <div className="profile-card">
      <div className="profile-top">
        {photoSrc ? (
          <img
            className="profile-photo"
            src={photoSrc}
            alt={member.name}
            width="56"
            height="56"
            onError={() => setPhotoFailed(true)}
          />
        ) : (
          <div className="profile-photo-placeholder">{initials}</div>
        )}
        <div className="profile-info">
          <div className="profile-name">{member.name}</div>
          {member.title && <div className="profile-title">{member.title}</div>}
        </div>
      </div>

      {member.bio && <div className="profile-bio">{member.bio}</div>}
    </div>
  )
}

export default ProfileCard
