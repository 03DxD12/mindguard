
export interface JournalEntry {
  id: number;
  text: string;
  mood?: string;
  themes: string[];
  risk_indicators: string[];
  date: string;
}

export interface WeeklyReflection {
  has_reflection: boolean;
  summary: string;
  themes: string[];
  dominant_emotions: string[];
  recommendation: string;
  entries_count: number;
}

export const JournalService = {
  async saveEntry(userId: number, text: string, mood?: string): Promise<JournalEntry> {
    const res = await fetch(`/api/journal/${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, mood })
    });
    if (!res.ok) throw new Error('Failed to save journal entry');
    return res.json();
  },

  async getEntries(userId: number, limit: number = 50): Promise<JournalEntry[]> {
    const res = await fetch(`/api/journal/${userId}?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch journal entries');
    return res.json();
  },

  async deleteEntry(userId: number, entryId: number): Promise<any> {
    const res = await fetch(`/api/journal/${userId}/${entryId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete journal entry');
    return res.json();
  },

  async getWeeklyReflection(userId: number): Promise<WeeklyReflection> {
    const res = await fetch(`/api/journal/${userId}/reflection`);
    if (!res.ok) throw new Error('Failed to fetch weekly reflection');
    return res.json();
  }
};
