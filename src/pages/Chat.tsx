import React, { useState, useRef, useEffect } from 'react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ChatMessage, ChatResponse } from '../types';
import { ChatService } from '../services/chat';
import { FaPaperPlane, FaRobot, FaExclamationTriangle } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { AnimatedItem } from '../components/AnimatedItem';
import styles from './Chat.module.css';

// Initial greeting from the empathy bot
const INITIAL_MESSAGE: ChatMessage = {
  id: 'init',
  role: 'ai',
  content: "Hello. I'm MindGuard, your safe space. How are you feeling today?",
  timestamp: new Date().toISOString()
};

const ThinkingIndicator = () => (
  <div className={styles.thinking}>
    <span>.</span><span>.</span><span>.</span>
  </div>
);

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [turn, setTurn] = useState(0);
  const [mood, setMood] = useState<string | null>(null);
  const [isCrisis, setIsCrisis] = useState(false);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  useEffect(() => {
    // Show initial message once mood is selected
    if (mood && messages.length === 0) {
      setMessages([INITIAL_MESSAGE]);
    }
  }, [mood]);

  const handleSend = async (overrideInput?: string) => {
    const text = overrideInput || input;
    if (!text.trim()) return;

    const currentTurn = turn + 1;
    setTurn(currentTurn);

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // Get all previous content for history
      const history = messages.map(m => m.content);
      
      const data = await ChatService.sendMessage(text, history, currentTurn, mood || 'Okay');
      
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: data.response,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, aiMsg]);

      // Check for crisis actions
      if (data.action?.startsWith('crisis_')) {
        setIsCrisis(true);
      }
    } catch (error) {
      console.error('Failed to get response', error);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: "I'm having trouble connecting right now. Please try again later.",
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const selectInitialMood = (selectedMood: string) => {
    setMood(selectedMood);
    // Optionally log this initial mood to the backend
  };

  if (!mood) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <h3>MindGuard Empathy</h3>
          <p className={styles.subtitle}>Let's check in before we start</p>
        </header>
        <Card className={styles.moodSelector}>
          <h4>How are you feeling right now?</h4>
          <div className={styles.moodGrid}>
            {[
              { label: 'Great', emoji: '😄' },
              { label: 'Good', emoji: '🙂' },
              { label: 'Okay', emoji: '😐' },
              { label: 'Down', emoji: '😔' },
              { label: 'Crisis', emoji: '😫' }
            ].map((m) => (
              <button 
                key={m.label} 
                className={styles.moodBtn}
                onClick={() => selectInitialMood(m.label)}
              >
                <span className={styles.moodEmoji}>{m.emoji}</span>
                <span className={styles.moodLabel}>{m.label}</span>
              </button>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h3>Empathy Companion</h3>
        <p className={styles.subtitle}>Turn {turn} • Mood: {mood}</p>
      </header>

      <Card className={styles.chatArea} padding={false}>
        <div className={styles.messages} ref={scrollRef}>
          {messages.map((msg, idx) => {
            const isCrisisMsg = isCrisis && idx === messages.length - 1 && msg.role === 'ai';
            return (
              <AnimatedItem key={msg.id} delay={0.1}>
                <div className={`
                  ${styles.message} 
                  ${msg.role === 'user' ? styles.user : (msg.role === 'system' ? styles.system : styles.ai)}
                  ${isCrisisMsg ? styles.crisis : ''}
                `}>
                  {msg.role === 'ai' && <div className={styles.avatar}><FaRobot /></div>}
                  {msg.role === 'system' && <div className={styles.avatar}><FaExclamationTriangle color="red"/></div>}
                  <div className={styles.bubble}>
                    {msg.content}
                    
                    {isCrisisMsg && (
                      <div className={styles.crisisActions}>
                         <Button variant="alert" size="sm" onClick={() => navigate('/emergency')}>
                           Call Emergency Hotline
                         </Button>
                         <Button variant="outline" size="sm" onClick={() => navigate('/booking')}>
                           Talk to a Counselor
                         </Button>
                      </div>
                    )}

                    {msg.role === 'ai' && msg.content.toLowerCase().includes("breathing") && (
                       <div style={{marginTop: '8px'}}>
                         <Button size="sm" variant="outline" onClick={() => navigate('/wellness')}>Go to Breathing Exercise</Button>
                       </div>
                    )}
                  </div>
                </div>
              </AnimatedItem>
            );
          })}
          {isTyping && (
             <div className={`${styles.message} ${styles.ai}`}>
               <div className={styles.avatar}><FaRobot /></div>
               <div className={styles.bubble}><ThinkingIndicator /></div>
             </div>
          )}
        </div>

        <div className={styles.inputArea}>
          <input
            type="text"
            className={styles.input}
            placeholder={isCrisis ? "Please reach out for help..." : "Type your message..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isTyping || isCrisis}
          />
          <Button 
            className={styles.sendBtn} 
            onClick={() => handleSend()} 
            disabled={!input.trim() || isTyping || isCrisis}
          >
            <FaPaperPlane />
          </Button>
        </div>
      </Card>
      
      <p className={styles.disclaimer}>
        MindGuard is an AI companion, not a replacement for professional help.
        <br />If you are in crisis, please contact emergency services.
      </p>
    </div>
  );
};

