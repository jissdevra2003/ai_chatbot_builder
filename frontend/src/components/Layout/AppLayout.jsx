import { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  Users,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import './Layout.css';

const navItems = [
  {
    section: 'Main',
    links: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/chatbots', label: 'Chatbots', icon: Bot },
    ],
  },
  {
    section: 'Organization',
    links: [
      { to: '/team', label: 'Team', icon: Users },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export default function AppLayout({ children, pageTitle }) {
  const { user, organization, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const location = useLocation();

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getInitials = (name) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleLogout = () => {
    setDropdownOpen(false);
    logout();
  };

  return (
    <div className="app-layout">
      {/* Mobile Overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">AI</div>
            <span>Chatbot Builder</span>
          </div>
          <button
            className="sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((section) => (
            <div className="sidebar-section" key={section.section}>
              <div className="sidebar-section-label">{section.section}</div>
              {section.links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'active' : ''}`
                  }
                >
                  <link.icon />
                  <span>{link.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer" ref={dropdownRef}>
          <div className="user-dropdown">
            {dropdownOpen && (
              <div className="user-dropdown-menu">
                <button className="user-dropdown-item danger" onClick={handleLogout}>
                  <LogOut />
                  <span>Sign out</span>
                </button>
              </div>
            )}
            <div
              className="sidebar-user"
              onClick={() => setDropdownOpen(!dropdownOpen)}
            >
              <div className="sidebar-avatar">
                {getInitials(user?.full_name)}
              </div>
              <div className="sidebar-user-info">
                <div className="sidebar-user-name">{user?.full_name || 'User'}</div>
                <div className="sidebar-user-org">{organization?.name || 'Organization'}</div>
              </div>
              <ChevronDown size={16} style={{ color: 'var(--color-text-tertiary)' }} />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="topbar">
          <div className="topbar-left">
            <button
              className="topbar-hamburger"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu size={22} />
            </button>
            <h2 className="topbar-title">{pageTitle || ''}</h2>
          </div>
          <div className="topbar-right" />
        </div>

        <div className="page-content">
          {children}
        </div>
      </main>
    </div>
  );
}
