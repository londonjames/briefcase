function ProfileCard({ member }) {
  const initials = member.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)

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
        <div className="profile-info">
          <div className="profile-name">{member.name}</div>
          {member.title && <div className="profile-title">{member.title}</div>}
        </div>
      </div>

      {member.bio && (
        <div className="profile-bio">
          {member.bio}
        </div>
      )}
    </div>
  )
}

export default ProfileCard
