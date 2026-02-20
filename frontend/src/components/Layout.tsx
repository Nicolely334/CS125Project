import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { AuthModal } from './AuthModal';

export function Layout() {
  const location = useLocation();
  const { user, signOut } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

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
        <div>
          {user ? (
            <div className="user-info">
              <span className="user-email">{user.email}</span>
                <button onClick={signOut} className="auth-button">
                  Sign Out
                </button>
            </div>
          ) : (
            <button onClick={() => setShowAuthModal(true)} className="auth-button">
              Sign In
            </button>
          )}
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      {showAuthModal && (
        <AuthModal onClose={() => setShowAuthModal(false)} initialMode="signin" />
      )}
    </div>
  );
}
