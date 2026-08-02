import React, { useState, useEffect } from 'react';
import { FaBook, FaTrash, FaPlus, FaTimes, FaHeart, FaMagic, FaLightbulb } from 'react-icons/fa';
import { AnimatedItem } from '../components/AnimatedItem';
import { JournalService, JournalEntry, WeeklyReflection } from '../services/journal';
import { useAuth } from '../context/AuthContext';
import styles from './Journal.module.css';

const PROMPTS = [
  "Take a deep breath. Write as little or as much as you need...",
  "What's one thing you want to let go of today?",
  "Right now, I'm feeling overwhelmed by...",
  "If my mood was the weather, it would be...",
  "What made you smile today, even just a little?"
];

const MOODS = [
  { emoji: '😊', label: 'Okay' },
  { emoji: '😔', label: 'Sad' },
  { emoji: '😡', label: 'Frustrated' },
  { emoji: '🌸', label: 'Hopeful' },
  { emoji: '😞', label: 'Tired' },
  { emoji: '😶', label: 'Numb' }
];

export const Journal: React.FC = () => {
  const { user } = useAuth();
  const userId = user?.id || 0;

  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [reflection, setReflection] = useState<WeeklyReflection | null>(null);
  const [currentText, setCurrentText] = useState('');
  const [isWriting, setIsWriting] = useState(false);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState(PROMPTS[0]);
  const [showSaveMessage, setShowSaveMessage] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userId) {
      loadData();
    }
  }, [userId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [history, aiReflection] = await Promise.all([
        JournalService.getEntries(userId),
        JournalService.getWeeklyReflection(userId)
      ]);
      setEntries(history);
      setReflection(aiReflection);
    } catch (e) {
      console.error("Failed to load journal data", e);
    } finally {
      setLoading(false);
    }
  };

  const handleStartWriting = () => {
    setCurrentPrompt(PROMPTS[Math.floor(Math.random() * PROMPTS.length)]);
    setIsWriting(true);
    setShowSaveMessage(false);
  };

  const handleSave = async () => {
    if (!currentText.trim() && !selectedMood) return;

    try {
      const newEntry = await JournalService.saveEntry(userId, currentText.trim(), selectedMood || undefined);
      setEntries([newEntry, ...entries]);
      setCurrentText('');
      setSelectedMood(null);
      setIsWriting(false);
      
      setShowSaveMessage(true);
      setTimeout(() => setShowSaveMessage(false), 4000);
      
      // Refresh reflection
      const aiReflection = await JournalService.getWeeklyReflection(userId);
      setReflection(aiReflection);
    } catch (e) {
      console.error("Failed to save entry", e);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await JournalService.deleteEntry(userId, id);
      setEntries(entries.filter(entry => entry.id !== id));
    } catch (e) {
      console.error("Failed to delete entry", e);
    }
  };

  return (
    <div className={styles.journalContainer}>
      <header className={styles.header}>
        <div className={styles.headerIcon}>
          <FaBook />
        </div>
        <div className={styles.headerText}>
          <h2>Private Sanctuary</h2>
          <p>Your feelings matter. AI-powered reflections inside.</p>
        </div>
      </header>

      {reflection && reflection.has_reflection && (
        <AnimatedItem delay={0.2}>
          <div className={styles.reflectionCard}>
            <div className={styles.reflectionHeader}>
              <FaMagic className={styles.magicIcon} />
              <h4>AI Weekly Reflection</h4>
            </div>
            <p className={styles.reflectionSummary}>{reflection.summary}</p>
            <div className={styles.reflectionFooter}>
              <div className={styles.themes}>
                {reflection.themes.map(t => <span key={t} className={styles.themeBadge}>#{t}</span>)}
              </div>
              <div className={styles.recommendation}>
                <FaLightbulb /> {reflection.recommendation}
              </div>
            </div>
          </div>
        </AnimatedItem>
      )}

      {showSaveMessage && (
        <div className={styles.saveFeedback}>
          <FaHeart className={styles.heartIcon} />
          You did well sharing today. AI has analyzed your themes for your reflection.
        </div>
      )}

      {!isWriting && (
        <button 
          className={styles.newEntryBtn}
          onClick={handleStartWriting}
        >
          <FaPlus /> Open a New Page
        </button>
      )}

      {isWriting && (
        <div className={styles.editorCard}>
          <div className={styles.editorHeader}>
            <span className={styles.validationText}>This is your safe space. No judgment here.</span>
            <button 
              className={styles.discardBtn}
              onClick={() => {
                setIsWriting(false);
                setCurrentText('');
                setSelectedMood(null);
              }}
              title="Discard"
            >
              <FaTimes />
            </button>
          </div>

          <div className={styles.moodSelector}>
            <p className={styles.moodLabel}>How are you feeling?</p>
            <div className={styles.moodsList}>
              {MOODS.map((mood) => (
                <button
                  key={mood.label}
                  className={`${styles.moodBtn} ${selectedMood === mood.emoji ? styles.moodSelected : ''}`}
                  onClick={() => setSelectedMood(mood.emoji)}
                  title={mood.label}
                >
                  {mood.emoji}
                </button>
              ))}
            </div>
          </div>

          <textarea
            className={styles.textarea}
            value={currentText}
            onChange={(e) => setCurrentText(e.target.value)}
            placeholder={currentPrompt}
            rows={5}
            autoFocus
          />
          
          <div className={styles.editorActions}>
            <button 
              className={styles.saveBtn}
              onClick={handleSave}
              disabled={!currentText.trim() && !selectedMood}
            >
              Save Entry
            </button>
          </div>
        </div>
      )}

      <div className={styles.entriesList}>
        {loading ? (
          <div className={styles.emptyState}><p>Loading your sanctuary...</p></div>
        ) : entries.length === 0 && !isWriting ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}><FaBook /></div>
            <p>Your journal is currently empty.</p>
            <p className={styles.emptySub}>Even a single word or emoji is enough. You can write whenever you're ready.</p>
          </div>
        ) : (
          entries.map(entry => (
            <AnimatedItem key={entry.id}>
              <div className={styles.entryCard}>
                <div className={styles.entryHeader}>
                  <div className={styles.entryMeta}>
                    {entry.mood && <span className={styles.entryMood}>{entry.mood}</span>}
                    <span className={styles.entryDate}>{new Date(entry.date).toLocaleString()}</span>
                  </div>
                  <button 
                    className={styles.deleteBtn}
                    onClick={() => handleDelete(entry.id)}
                    title="Delete Entry"
                  >
                    <FaTrash />
                  </button>
                </div>
                {entry.text && (
                  <div className={styles.entryText}>
                    {entry.text}
                  </div>
                )}
                {entry.themes && entry.themes.length > 0 && (
                  <div className={styles.entryThemes}>
                    {entry.themes.map(t => <span key={t}>#{t}</span>)}
                  </div>
                )}
              </div>
            </AnimatedItem>
          ))
        )}
      </div>

      <div className={styles.crisisFooter}>
        <p>Need immediate support? <button className={styles.crisisLink} onClick={() => alert("Please contact emergency resources. You are not alone.")}>Tap here for emergency resources.</button></p>
      </div>
    </div>
  );
};

