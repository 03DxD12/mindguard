import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { BreathingExercise } from '../components/BreathingExercise';
import { WellnessService, MoodLog, MoodAnalytics } from '../services/wellness';
import { useAuth } from '../context/AuthContext';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const COLORS = ['#10b981', '#34d399', '#9ca3af', '#f87171', '#ef4444'];

export const Wellness: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const userId = user?.id || 0;

  const [moods, setMoods] = useState<MoodLog[]>([]);
  const [analytics, setAnalytics] = useState<MoodAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userId) {
      loadData();
    }
  }, [userId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const history = await WellnessService.getMoods(userId);
      const stats = await WellnessService.getAnalytics(userId);
      setMoods(history);
      setAnalytics(stats);
    } catch (error) {
      console.error('Failed to load wellness data', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogMood = async (mood: string) => {
    try {
      await WellnessService.logMood(userId, mood);
      loadData();
    } catch (error) {
      console.error('Failed to log mood', error);
    }
  };

  const handleDeleteMood = async (id: number) => {
    try {
      await WellnessService.deleteMood(userId, id);
      setMoods(moods.filter(m => m.id !== id));
      // Refresh analytics too
      const stats = await WellnessService.getAnalytics(userId);
      setAnalytics(stats);
    } catch (error) {
      console.error('Failed to delete mood', error);
    }
  };

  const pieData = analytics ? Object.entries(analytics.distribution).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="flex flex-col gap-4 pb-10">
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

      {analytics && moods.length > 0 && (
        <>
          <h4 className="font-bold text-gray-700 mt-2">Personal Analytics</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card title="Mood Trend">
              <div h-48 style={{ height: 180 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={analytics.daily_data}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis domain={[1, 5]} hide />
                    <Tooltip 
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                      formatter={(value) => [labels[5 - Number(value)], 'Mood']}
                    />
                    <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 text-center">
                <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                  analytics.trend === 'improving' ? 'bg-green-100 text-green-700' :
                  analytics.trend === 'worsening' ? 'bg-red-100 text-red-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  Trend: {analytics.trend.charAt(0).toUpperCase() + analytics.trend.slice(1)}
                  {analytics.trend === 'improving' ? ' ↑' : analytics.trend === 'worsening' ? ' ↓' : ' →'}
                </span>
              </div>
            </Card>

            <Card title="Distribution">
              <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      innerRadius={40}
                      outerRadius={60}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      <h4 className="font-bold text-gray-700 mt-2">Mood History</h4>
      <Card>
        {loading ? (
          <div className="text-center py-8 text-gray-400">Loading history...</div>
        ) : moods.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No moods logged yet. Record your first mood above!</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
            {moods.map((entry) => (
              <div key={entry.id} className="flex justify-between items-center border-b border-gray-50 last:border-0 pb-2 last:pb-0">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">{entry.mood}</span>
                    <span className="text-sm">
                      {entry.mood === 'Great' ? '😄' : entry.mood === 'Good' ? '🙂' : entry.mood === 'Okay' ? '😐' : entry.mood === 'Down' ? '😔' : '😫'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400">{new Date(entry.timestamp).toLocaleString(undefined, {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  })}</div>
                </div>
                <button 
                  onClick={() => handleDeleteMood(entry.id)}
                  className="text-gray-300 hover:text-red-500 text-lg transition-colors"
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

const labels = ['', 'Crisis', 'Down', 'Okay', 'Good', 'Great'];

