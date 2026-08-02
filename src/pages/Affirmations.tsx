import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FaLightbulb, FaArrowLeft, FaSync, FaHeart, FaTrash, FaShareAlt, FaBookmark } from 'react-icons/fa';
import { useAuth } from '../context/AuthContext';
import { AffirmationService, SavedAffirmation } from '../services/affirmations';

export const Affirmations: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const userId = user?.id || 0;

  const [current, setCurrent] = useState('');
  const [saved, setSaved] = useState<SavedAffirmation[]>([]);
  const [savedTexts, setSavedTexts] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [isSpinning, setIsSpinning] = useState(false);
  const [loading, setLoading] = useState(true);
  const savedListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (userId) {
      loadData();
    }
  }, [userId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [daily, favorites] = await Promise.all([
        AffirmationService.getDaily(userId),
        AffirmationService.getSaved(userId)
      ]);
      setCurrent(daily.affirmation);
      setSaved(favorites);
      setSavedTexts(new Set(favorites.map(a => a.text)));
    } catch (e) {
      console.error("Failed to load affirmations", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsSpinning(true);
    try {
      const daily = await AffirmationService.getDaily(userId);
      setCurrent(daily.affirmation);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setIsSpinning(false), 500);
    }
  };

  const handleSave = async () => {
    if (!current || savedTexts.has(current) || saving) return;
    setSaving(true);
    setJustSaved(true);

    try {
      const newItem = await AffirmationService.saveAffirmation(userId, current);
      const updated = [newItem, ...saved];
      setSaved(updated);
      setSavedTexts(new Set(updated.map(a => a.text)));

      setTimeout(() => {
        savedListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
      setTimeout(() => setJustSaved(false), 1500);
    }
  };

  const handleRemove = async (item: SavedAffirmation) => {
    try {
      await AffirmationService.deleteSaved(userId, item.id);
      const updated = saved.filter(a => a.id !== item.id);
      setSaved(updated);
      setSavedTexts(new Set(updated.map(a => a.text)));
    } catch (e) {
      console.error(e);
    }
  };

  const handleShare = (text: string) => {
    if (navigator.share) {
      navigator.share({ text: `💬 "${text}" — MindGuard Daily Affirmation` });
    } else {
      navigator.clipboard.writeText(`"${text}" — MindGuard`);
      alert('Affirmation copied to clipboard!');
    }
  };

  const isCurrentSaved = savedTexts.has(current);

  if (loading) {
     return <div style={{ textAlign: 'center', padding: '50px', color: '#0f766e' }}>Preparing your daily inspiration...</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{ maxWidth: '600px', margin: '0 auto', padding: '16px 16px 80px', fontFamily: 'Inter, sans-serif' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <button
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#0f766e', padding: '8px', borderRadius: '8px', display: 'flex', alignItems: 'center' }}
        >
          <FaArrowLeft size={18} />
        </button>
        <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: '#0f766e' }}>Daily Affirmations</h2>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={current}
          initial={{ opacity: 0, y: 24, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -16, scale: 0.97 }}
          transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
          style={{
            background: 'linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 60%, #e0f2fe 100%)',
            border: '1.5px solid #99f6e4',
            borderRadius: '22px',
            padding: '40px 28px 32px',
            textAlign: 'center',
            marginBottom: '20px',
            boxShadow: '0 8px 32px rgba(15,118,110,0.12)',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ position: 'absolute', top: -20, right: -20, width: 80, height: 80, borderRadius: '50%', background: 'rgba(15,118,110,0.06)' }} />
          <div style={{ position: 'absolute', bottom: -10, left: -10, width: 60, height: 60, borderRadius: '50%', background: 'rgba(15,118,110,0.05)' }} />

          <FaLightbulb size={30} color="#0f766e" style={{ marginBottom: '18px', opacity: 0.55 }} />
          <p style={{
            fontSize: '1.15rem', fontWeight: 600, color: '#134e4a',
            lineHeight: 1.65, margin: 0, fontStyle: 'italic',
            position: 'relative', zIndex: 1,
          }}>
            "{current}"
          </p>
        </motion.div>
      </AnimatePresence>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '36px', justifyContent: 'center' }}>
        <button
          onClick={handleRefresh}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 24px',
            background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: '999px',
            fontWeight: 600, color: '#475569', cursor: 'pointer', fontSize: '0.9rem',
            transition: 'all 0.2s',
          }}
        >
          <motion.span
            animate={isSpinning ? { rotate: 360 } : { rotate: 0 }}
            transition={{ duration: 0.45 }}
            style={{ display: 'inline-flex' }}
          >
            <FaSync size={14} />
          </motion.span>
          Refresh
        </button>

        <motion.button
          onClick={handleSave}
          disabled={saving || isCurrentSaved}
          whileTap={!isCurrentSaved ? { scale: 0.93 } : {}}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 26px',
            background: isCurrentSaved ? '#f0fdf4' : '#0f766e',
            border: isCurrentSaved ? '1.5px solid #bbf7d0' : 'none',
            borderRadius: '999px', fontWeight: 700,
            color: isCurrentSaved ? '#15803d' : '#fff',
            cursor: isCurrentSaved ? 'default' : 'pointer', fontSize: '0.9rem',
            transition: 'all 0.25s ease',
            boxShadow: isCurrentSaved ? 'none' : '0 4px 14px rgba(15,118,110,0.3)',
          }}
        >
          <motion.span
            animate={justSaved ? { scale: [1, 1.4, 1] } : { scale: 1 }}
            transition={{ duration: 0.35 }}
          >
            <FaHeart />
          </motion.span>
          {isCurrentSaved ? '✓ Saved' : saving ? 'Saving…' : 'Save'}
        </motion.button>
      </div>

      <AnimatePresence>
        {saved.length > 0 && (
          <motion.div
            ref={savedListRef}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <FaBookmark size={14} color="#0f766e" />
              <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f766e', letterSpacing: '-0.01em' }}>
                Saved Affirmations
              </h3>
              <span style={{ marginLeft: 'auto', fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', background: '#f1f5f9', padding: '2px 10px', borderRadius: '999px' }}>
                {saved.length}
              </span>
            </div>

            <div
              style={{
                maxHeight: saved.length > 4 ? '420px' : 'none',
                overflowY: saved.length > 4 ? 'auto' : 'visible',
                paddingRight: saved.length > 4 ? '4px' : '0',
              }}
            >
              <AnimatePresence initial={false}>
                {saved.map((a) => (
                  <motion.div
                    key={a.id}
                    layout
                    initial={{ opacity: 0, y: -18, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, x: 40, scale: 0.92, transition: { duration: 0.22 } }}
                    transition={{
                      duration: 0.35,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                    style={{
                      background: '#fff',
                      border: '1px solid #f0fdf4',
                      borderLeft: '3px solid #0f766e',
                      borderRadius: '14px',
                      padding: '15px 16px',
                      marginBottom: '10px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                      boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
                      position: 'relative',
                      overflow: 'hidden',
                    }}
                  >
                    <span style={{ fontSize: '2rem', color: '#99f6e4', lineHeight: 1, flexShrink: 0, marginTop: '-4px', userSelect: 'none' }}>"</span>

                    <p style={{
                      margin: 0, color: '#374151', fontSize: '0.88rem',
                      fontStyle: 'italic', flex: 1, lineHeight: 1.6,
                    }}>
                      {a.text}
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flexShrink: 0 }}>
                      <button
                        onClick={() => handleShare(a.text)}
                        title="Share"
                        style={{
                          background: '#f0fdf4', border: 'none', cursor: 'pointer',
                          padding: '6px', borderRadius: '8px', display: 'flex', alignItems: 'center',
                          color: '#0f766e',
                        }}
                      >
                        <FaShareAlt size={12} />
                      </button>
                      <button
                        onClick={() => handleRemove(a)}
                        title="Remove"
                        style={{
                          background: '#fef2f2', border: 'none', cursor: 'pointer',
                          padding: '6px', borderRadius: '8px', display: 'flex', alignItems: 'center',
                          color: '#e11d48',
                        }}
                      >
                        <FaTrash size={12} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{ marginTop: '28px', textAlign: 'center', fontSize: '11px', color: '#94a3b8', letterSpacing: '0.4px' }}>
        🔒 All data is encrypted and protected for your privacy.
      </div>
    </motion.div>
  );
};

