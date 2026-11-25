import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { FaHome, FaCommentDots, FaChartBar, FaUser, FaBook } from 'react-icons/fa';
import styles from './Navbar.module.css';

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className={styles.navbar} aria-label="Primary navigation">
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/dashboard') ? styles.active : ''}`}
        aria-current={isActive('/dashboard') ? 'page' : undefined}
        onClick={() => navigate('/dashboard')}
      >
        <FaHome aria-hidden="true" />
        <span className={styles.label}>Home</span>
      </button>
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/chat') ? styles.active : ''}`}
        aria-current={isActive('/chat') ? 'page' : undefined}
        onClick={() => navigate('/chat')}
      >
        <FaCommentDots aria-hidden="true" />
        <span className={styles.label}>Chat</span>
      </button>
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/journal') ? styles.active : ''}`}
        aria-current={isActive('/journal') ? 'page' : undefined}
        onClick={() => navigate('/journal')}
      >
        <FaBook aria-hidden="true" />
        <span className={styles.label}>Journal</span>
      </button>
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/wellness') ? styles.active : ''}`}
        aria-current={isActive('/wellness') ? 'page' : undefined}
        onClick={() => navigate('/wellness')}
      >
        <FaChartBar aria-hidden="true" />
        <span className={styles.label}>Wellness</span>
      </button>
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/resources') ? styles.active : ''}`}
        aria-current={isActive('/resources') ? 'page' : undefined}
        onClick={() => navigate('/resources')}
      >
        <FaBook aria-hidden="true" />
        <span className={styles.label}>Resources</span>
      </button>
      <button
        type="button"
        className={`${styles.navBtn} ${isActive('/profile') ? styles.active : ''}`}
        aria-current={isActive('/profile') ? 'page' : undefined}
        onClick={() => navigate('/profile')}
      >
        <FaUser aria-hidden="true" />
        <span className={styles.label}>Profile</span>
      </button>
    </nav>
  );
};
