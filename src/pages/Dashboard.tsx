import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { FaRobot, FaWind, FaUsers, FaCalendarCheck, FaBook, FaLightbulb, FaMagic, FaShieldAlt } from 'react-icons/fa';
import { WellnessService } from '../services/wellness';
import { AffirmationService } from '../services/affirmations';
import styles from './Dashboard.module.css';

const moodOptions = [
  { label: 'Great', emoji: '😄' },
  { label: 'Good', emoji: '🙂' },
  { label: 'Okay', emoji: '😐' },
  { label: 'Down', emoji: '😔' },
  { label: 'Crisis', emoji: '😫' },
];

const quickActions = [
  { label: 'AI Chat', icon: FaRobot, path: '/chat', detail: 'Talk now' },
  { label: 'Wellness', icon: FaWind, path: '/wellness', detail: 'Breathing and mood' },
  { label: 'Journal', icon: FaBook, path: '/journal', detail: 'Write a reflection' },
  { label: 'Inspire', icon: FaLightbulb, path: '/affirmations', detail: 'Daily affirmation' },
  { label: 'Community', icon: FaUsers, path: '/groups', detail: 'Peer support' },
  { label: 'Specialist', icon: FaCalendarCheck, path: '/booking', detail: 'Book counseling' },
];

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const userId = user?.id || 0;
  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  const firstName = user?.fullname?.split(' ')[0] || 'Friend';

  const [dailyAffirmation, setDailyAffirmation] = useState<string | null>(null);
  const [loadingAffirmation, setLoadingAffirmation] = useState(false);

  useEffect(() => {
    if (userId) {
      loadAffirmation();
    }
  }, [userId]);

  const loadAffirmation = async () => {
    setLoadingAffirmation(true);
    try {
      const data = await AffirmationService.getDaily(userId);
      setDailyAffirmation(data.affirmation);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAffirmation(false);
    }
  };

  const handleLogMood = async (mood: string) => {
    try {
      await WellnessService.logMood(userId, mood);
      loadAffirmation();
    } catch (e) {
      console.error('Failed to log mood', e);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.hero}>
        <div>
          <span className={styles.eyebrow}>MindGuard home</span>
          <h2 className={styles.greeting}>Hi, {firstName}</h2>
          <p className={styles.date}>{dateStr}</p>
        </div>
        <button className={styles.profileBtn} onClick={() => navigate('/profile')} aria-label="Open profile">
          {user?.fullname?.charAt(0)?.toUpperCase() || 'U'}
        </button>
      </header>

      <div className={styles.dashboardGrid}>
        <section className={styles.primaryColumn}>
          <Card className={styles.moodCard}>
            <div className={styles.cardHeader}>
              <div>
                <h3>How are you feeling?</h3>
                <p>Log a quick check-in to update your wellness picture.</p>
              </div>
            </div>

            <div className={styles.moodGrid}>
              {moodOptions.map((mood) => (
                <button
                  key={mood.label}
                  className={styles.moodBtn}
                  onClick={() => handleLogMood(mood.label)}
                >
                  <span className={styles.moodEmoji}>{mood.emoji}</span>
                  <span className={styles.moodLabel}>{mood.label}</span>
                </button>
              ))}
            </div>
          </Card>

          <div className={styles.supportGrid}>
            <Card className={styles.affirmationPreview} onClick={() => navigate('/affirmations')}>
              <div className={styles.affirmationHeader}>
                <FaMagic />
                <span>Today's Inspiration</span>
              </div>
              <p className={styles.affirmationText}>
                {loadingAffirmation
                  ? 'Preparing a daily affirmation...'
                  : dailyAffirmation || 'Take one steady step today. You do not have to carry everything at once.'}
              </p>
            </Card>

            <Card className={styles.emergencyCard}>
              <div className={styles.emergencyHeader}>
                <FaShieldAlt />
                <strong className={styles.emergencyTitle}>Need immediate help?</strong>
              </div>
              <p className={styles.emergencyText}>LSPU Safety & Security is available 24/7.</p>
              <Button variant="alert" size="sm" className={styles.emergencyButton} onClick={() => navigate('/emergency')}>
                Call Emergency
              </Button>
            </Card>
          </div>
        </section>

        <aside className={styles.actionsPanel}>
          <div className={styles.panelHeader}>
            <h3>Quick Actions</h3>
            <p>Jump into common support tools.</p>
          </div>

          <div className={styles.actionGrid}>
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button key={action.path} className={styles.actionCard} onClick={() => navigate(action.path)}>
                  <Icon className={styles.actionIcon} />
                  <span className={styles.actionLabel}>{action.label}</span>
                  <small>{action.detail}</small>
                </button>
              );
            })}
          </div>
        </aside>
      </div>
    </div>
  );
};
