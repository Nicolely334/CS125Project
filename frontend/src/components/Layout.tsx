import { Link, Outlet, useLocation } from 'react-router-dom';

export function Layout() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Search', icon: '🔍' },
    { path: '/profile', label: 'Profile', icon: '👤' },
    { path: '/discover', label: 'Discover', icon: '✨' },
  ];

  return (
    <div className="layout">
      <header className="header">
        <Link to="/" className="brand">
          <span className="brand-icon">📦</span>
          <span className="brand-name">MusicBoxd</span>
        </Link>
        <nav className="nav">
          {navItems.map(({ path, label, icon }) => (
            <Link
              key={path}
              to={path}
              className={`nav-link ${location.pathname === path ? 'active' : ''}`}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
