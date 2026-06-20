import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { BreathingExercise } from '../components/BreathingExercise';

export const Wellness: React.FC = () => {
  const navigate = useNavigate();


  // Mood Tracking Logic
  const [moods, setMoods] = useState<{id: string, mood: string, timestamp: string}[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem('mood_history');
    if (saved) {
      setMoods(JSON.parse(saved));
    }
  }, []);

  const handleLogMood = (mood: string) => {
    const newMood = {
      id: Date.now().toString(),
      mood,
      timestamp: new Date().toISOString()
    };
    const updated = [...moods, newMood];
    setMoods(updated);
    localStorage.setItem('mood_history', JSON.stringify(updated));
  };

  const handleDeleteMood = (id: string) => {
    const updated = moods.filter(m => m.id !== id);
    setMoods(updated);
    localStorage.setItem('mood_history', JSON.stringify(updated));
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard')}>
          ←
        </Button>
        <h3 className="text-xl font-bold text-primary m-0">My Wellness</h3>
      </div>

      <BreathingExercise />

      <h4 className="font-bold text-gray-700 mt-2">How are you feeling?</h4>
      <Card className="flex flex-col gap-4">
        <div className="flex justify-between px-2">
          {['😄', '🙂', '😐', '😔', '😫'].map((emoji, idx) => {
            const labels = ['Great', 'Good', 'Okay', 'Down', 'Crisis'];
            return (
              <button
                key={idx}
                onClick={() => handleLogMood(labels[idx])}
                className="flex flex-col items-center gap-1 hover:scale-110 transition-transform"
              >
                <span className="text-3xl">{emoji}</span>
                <span className="text-xs text-gray-500">{labels[idx]}</span>
              </button>
            );
          })}
        </div>
      </Card>

      <h4 className="font-bold text-gray-700 mt-2">Suggested For You</h4>
      <Card className="grid grid-cols-2 gap-3">
        <a href="https://www.youtube.com/watch?v=inpok4MKVLM" target="_blank" rel="noreferrer" className="flex flex-col items-center p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
          <span className="text-2xl mb-1">🎵</span>
          <span className="text-sm font-medium text-center">Calming Music</span>
        </a>
        <a href="https://www.mindful.org/meditation/mindfulness-getting-started/" target="_blank" rel="noreferrer" className="flex flex-col items-center p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
          <span className="text-2xl mb-1">📖</span>
          <span className="text-sm font-medium text-center">Mindfulness Guide</span>
        </a>
        <a href="https://www.youtube.com/results?search_query=funny+animal+videos" target="_blank" rel="noreferrer" className="flex flex-col items-center p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
          <span className="text-2xl mb-1">🐶</span>
          <span className="text-sm font-medium text-center">Funny Animals</span>
        </a>
        <a href="https://greatergood.berkeley.edu/article/item/how_to_start_a_gratitude_practice" target="_blank" rel="noreferrer" className="flex flex-col items-center p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
          <span className="text-2xl mb-1">✍️</span>
          <span className="text-sm font-medium text-center">Gratitude</span>
        </a>
      </Card>

      <h4 className="font-bold text-gray-700 mt-2">Mood History</h4>
      <Card>
        {moods.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No moods logged yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {moods.slice().reverse().map((entry) => (
              <div key={entry.id} className="flex justify-between items-center border-b border-gray-50 last:border-0 pb-2 last:pb-0">
                <div>
                  <span className="font-medium text-gray-800">{entry.mood}</span>
                  <div className="text-xs text-gray-400">{new Date(entry.timestamp).toLocaleString()}</div>
                </div>
                <button 
                  onClick={() => handleDeleteMood(entry.id)}
                  className="text-red-400 hover:text-red-600 text-xs"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
