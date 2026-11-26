
export interface SavedAffirmation {
  id: number;
  text: string;
  created_at: string;
}

export interface AffirmationResponse {
  affirmation: string;
  category?: string;
  mood_category?: string;
  is_personalized?: boolean;
  text?: string; // some endpoints return `text` as well
}

export const AffirmationService = {
  async getDaily(userId: number, mood?: string): Promise<AffirmationResponse> {
    // Backend endpoint: /api/affirmation/daily?mood=<mood>
    // Falls back to /api/affirmations/daily/<userId> for demo intercept compatibility
    const moodParam = mood ? `?mood=${encodeURIComponent(mood)}` : '';
    const url = userId
      ? `/api/affirmation/daily${moodParam}`
      : `/api/affirmation/daily${moodParam}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch daily affirmation');
    return res.json();
  },

  async saveAffirmation(userId: number, text: string): Promise<SavedAffirmation> {
    const res = await fetch(`/api/affirmations/${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error('Failed to save affirmation');
    return res.json();
  },

  async getSaved(userId: number): Promise<SavedAffirmation[]> {
    const res = await fetch(`/api/affirmations/${userId}`);
    if (!res.ok) throw new Error('Failed to fetch saved affirmations');
    return res.json();
  },

  async deleteSaved(userId: number, id: number): Promise<any> {
    const res = await fetch(`/api/affirmations/${userId}/${id}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete affirmation');
    return res.json();
  }
};
