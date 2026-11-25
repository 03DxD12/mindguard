import React, { useState, useEffect, useRef } from 'react';
import { Card } from './Card';
import { Button } from './Button';
import styles from './BreathingExercise.module.css';

export const BreathingExercise: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [phase, setPhase] = useState('Ready');
  const [instruction, setInstruction] = useState('Press Start to begin');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isActive) {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }

    let step = 0;

    const cycle = () => {
      // 4-7-8 Breathing Technique
      if (step === 0) {
        setPhase('Inhale');
        setInstruction('Breathe in through your nose...');
        timerRef.current = setTimeout(() => { step = 1; cycle(); }, 4000);
      } else if (step === 1) {
        setPhase('Hold');
        setInstruction('Hold your breath...');
        timerRef.current = setTimeout(() => { step = 2; cycle(); }, 7000);
      } else {
        setPhase('Exhale');
        setInstruction('Exhale slowly through your mouth...');
        timerRef.current = setTimeout(() => { step = 0; cycle(); }, 8000);
      }
    };

    cycle();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isActive]);

  const displayPhase = isActive ? phase : 'Ready';
  const displayInstruction = isActive ? instruction : 'Press Start to begin';

  return (
    <div className={styles.container}>
      <Card className={styles.breathingCard}>
        <div className={`${styles.circle} ${isActive ? styles[displayPhase.toLowerCase()] : ''}`}>
          <div className={styles.label}>{displayPhase}</div>
        </div>
        
        <p className={styles.instruction} aria-live="polite">{displayInstruction}</p>
        
        <Button 
          variant={isActive ? 'outline' : 'primary'} 
          onClick={() => setIsActive(!isActive)}
          className="mt-6"
        >
          {isActive ? 'Stop' : 'Start Breathing Exercise'}
        </Button>
      </Card>

      <div className={styles.tips}>
        <h4>Why 4-7-8 Breathing?</h4>
        <p>This rhythmic breathing pattern aims to reduce anxiety or help people get to sleep. It acts as a natural tranquilizer for the nervous system.</p>
      </div>
    </div>
  );
};
