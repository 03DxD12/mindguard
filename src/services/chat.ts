import { ChatMessage } from '../types';

export const ChatService = {
  // Simple session ID generator
  getSessionId: () => {
    let sid = sessionStorage.getItem('chat_session_id');
    if (!sid) {
      sid = Math.random().toString(36).substring(2) + Date.now().toString(36);
      sessionStorage.setItem('chat_session_id', sid);
    }
    return sid;
  },

  async sendMessage(
    message: string, 
    history: string[], 
    turn: number = 0, 
    mood: string = 'Okay'
  ): Promise<{ 
    response: string; 
    sentiment: string; 
    action?: string;
    reasoning?: any;
    session_id?: string;
  }> {
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message,
          history, 
          session_id: ChatService.getSessionId(),
          turn,
          mood
        }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();
      return data;
    } catch (error) {
      console.error('Chat API Error:', error);
      return {
        response: "I'm having trouble connecting to my empathy engine right now. Please ensure the Python backend is running.",
        sentiment: "neutral",
        action: "none"
      };
    }
  }
};
