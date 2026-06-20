import React from 'react';
import { Outlet, useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  MdDashboard, MdPeople, MdHistory, MdSettings, MdLogout, MdShield
} from 'react-icons/md';
import styles from './AdminDashboardLayout.module.css';

export function AdminDashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path: string) => location.pathname.includes(path);

  return (
    <div className={styles.adminContainer}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandHeader}>
            <MdShield size={24} color="#6366f1" />
            <span className={styles.brandTitle}>MindGuard</span>
          </div>
          <p className={styles.brandSubtitle}>Admin Control Panel</p>
        </div>

        <nav className={styles.nav}>
          <Link 
            to="/superadmin/dashboard" 
            className={`${styles.navLink} ${isActive('superadmin/dashboard') ? styles.activeLink : ''}`}
          >
            <MdDashboard size={20} />
            <span className={styles.navText}>Dashboard</span>
          </Link>
          <Link 
            to="/superadmin/manage-staff" 
            className={`${styles.navLink} ${isActive('manage-staff') ? styles.activeLink : ''}`}
          >
            <MdPeople size={20} />
            <span className={styles.navText}>Manage Staff</span>
          </Link>
          <Link 
            to="/superadmin/system-logs" 
            className={`${styles.navLink} ${isActive('system-logs') ? styles.activeLink : ''}`}
          >
            <MdHistory size={20} />
            <span className={styles.navText}>System Logs</span>
          </Link>
          <Link 
            to="/superadmin/settings" 
            className={`${styles.navLink} ${isActive('settings') ? styles.activeLink : ''}`}
          >
            <MdSettings size={20} />
            <span className={styles.navText}>Settings</span>
          </Link>
          
          <div style={{ flex: 1 }}></div>

          <button onClick={handleLogout} className={`${styles.navLink} ${styles.logoutBtn}`}>
            <MdLogout size={20} />
            <span className={styles.navText}>Logout</span>
          </button>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <div className={styles.userName}>{user?.fullname || 'Administrator'}</div>
            <div className={styles.userEmail}>{user?.email}</div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className={styles.main}>
        {/* Topbar */}
        <header className={styles.topbar}>
          <div>
            <h1 className={styles.topbarTitle}>Admin Dashboard</h1>
            <p className={styles.topbarSubtitle}>System administration & staff management</p>
          </div>
          <div className={styles.topbarRight}>
            <div className={styles.userAvatar}>
              {(user?.fullname || 'A')[0].toUpperCase()}
            </div>
          </div>
        </header>

        <div className={styles.content}>
          <Outlet />
        </div>

        <footer className={styles.footer}>
          🔒 All data is encrypted and protected for your privacy.
        </footer>
      </main>
    </div>
  );
}
