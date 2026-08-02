
export interface MoodLog {
  id: number;
  mood: string;
  value: number;
  note?: string;
  timestamp: string;
}

export interface MoodAnalytics {
  distribution: Record<string, number>;
  trend: 'improving' | 'stable' | 'worsening';
  average_value: number;
  total_entries: number;
  daily_data: { date: string, mood: string, value: number }[];
  risk_indicators: string[];
}

export const WellnessService = {
  async logMood(userId: number, mood: string, note?: string): Promise<any> {
    const moods: Record<string, number> = { 'Great': 5, 'Good': 4, 'Okay': 3, 'Down': 2, 'Crisis': 1 };
    const res = await fetch(`/api/mood/${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        mood, 
        value: moods[mood] || 3,
        note 
      })
    });
    if (!res.ok) throw new Error('Failed to log mood');
    return res.json();
  },

  async getMoods(userId: number, days: number = 30): Promise<MoodLog[]> {
    const res = await fetch(`/api/mood/${userId}?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch moods');
    return res.json();
  },

  async deleteMood(userId: number, moodId: number): Promise<any> {
    const res = await fetch(`/api/mood/${userId}/${moodId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete mood');
    return res.json();
  },

  async getAnalytics(userId: number, days: number = 30): Promise<MoodAnalytics> {
    const res = await fetch(`/api/mood/${userId}/analytics?days=${days}`);
    if (!res.ok) throw new Error('Failed to fetch analytics');
    return res.json();
  }
};
