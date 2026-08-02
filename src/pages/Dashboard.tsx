import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { FaRobot, FaWind, FaUsers, FaCalendarCheck, FaBook, FaLightbulb, FaMagic } from 'react-icons/fa';
import { WellnessService } from '../services/wellness';
import { AffirmationService } from '../services/affirmations';
import styles from './Dashboard.module.css';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const userId = user?.id || 0;
  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

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
      alert(`Mood logged: ${mood}! Your dashboard will adapt.`);
      loadAffirmation(); // Reload affirmation as it might change based on mood
    } catch (e) {
      console.error("Failed to log mood", e);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h2 className={styles.greeting}>Hi, {user?.fullname.split(' ')[0] || 'Friend'}</h2>
          <p className={styles.date}>{dateStr}</p>
        </div>
        <div className={styles.headerActions}>
           <button className={styles.iconBtn} onClick={() => navigate('/profile')}>
             <div className={styles.avatarPlaceholder}>{user?.fullname.charAt(0)}</div>
           </button>
        </div>
      </header>

      <Card title="How are you feeling?" className={styles.moodCard}>
        <div className={styles.moodGrid}>
          {['Great', 'Good', 'Okay', 'Down', 'Crisis'].map((mood) => (
            <button 
              key={mood} 
              className={styles.moodBtn}
              onClick={() => handleLogMood(mood)}
            >
              <span className={styles.moodEmoji}>
                {mood === 'Great' ? '😄' : mood === 'Good' ? '🙂' : mood === 'Okay' ? '😐' : mood === 'Down' ? '😔' : '😫'}
              </span>
              <span className={styles.moodLabel}>{mood}</span>
            </button>
          ))}
        </div>
      </Card>

      {dailyAffirmation && (
        <Card className={styles.affirmationPreview} onClick={() => navigate('/affirmations')}>
          <div className={styles.affirmationHeader}>
            <FaMagic color="var(--primary)" />
            <span>Today's Inspiration</span>
          </div>
          <p className={styles.affirmationText}>"{dailyAffirmation}"</p>
        </Card>
      )}

      <h3 className={styles.sectionTitle}>Quick Actions</h3>
      <div className={styles.actionGrid}>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/chat')}>
            <FaRobot className={styles.actionIcon} />
            <span>AI Chat</span>
          </button>
        </Card>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/wellness')}>
            <FaWind className={styles.actionIcon} />
            <span>Wellness</span>
          </button>
        </Card>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/journal')}>
            <FaBook className={styles.actionIcon} />
            <span>Journal</span>
          </button>
        </Card>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/affirmations')}>
            <FaLightbulb className={styles.actionIcon} />
            <span>Inspire</span>
          </button>
        </Card>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/groups')}>
            <FaUsers className={styles.actionIcon} />
            <span>Community</span>
          </button>
        </Card>
        <Card className={styles.actionCard} padding={false}>
          <button className={styles.actionBtn} onClick={() => navigate('/booking')}>
            <FaCalendarCheck className={styles.actionIcon} />
            <span>Specialist</span>
          </button>
        </Card>
      </div>

      <Card className={styles.emergencyCard}>
        <strong className={styles.emergencyTitle}>Need immediate help?</strong>
        <p className={styles.emergencyText}>LSPU Safety & Security is available 24/7.</p>
        <Button variant="alert" size="sm" className="w-full" onClick={() => navigate('/emergency')}>Call Emergency</Button>
      </Card>
    </div>
  );
};

