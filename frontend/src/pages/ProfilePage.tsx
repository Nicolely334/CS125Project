export function ProfilePage() {
  return (
    <section className="page profile-page">
      <h1>Your Profile</h1>
      <p className="page-desc">
        Your logged tracks, ratings, favorites, and listening history.
      </p>
      <div className="placeholder-card">
        <p>Profile features coming soon.</p>
        <ul>
          <li>Logged tracks & ratings</li>
          <li>Favorite artists & genres</li>
          <li>Mood/activity tags</li>
        </ul>
      </div>
    </section>
  );
}
