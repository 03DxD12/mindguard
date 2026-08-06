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
    const payload = JSON.stringify({
      message,
      history,
      session_id: ChatService.getSessionId(),
      turn,
      mood
    });

    const postChat = async (url: string) => {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: payload,
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      return res.json();
    };

    try {
      return await postChat('/api/chat');
    } catch (error) {
      console.warn('Chat proxy request failed, trying backend directly:', error);

      try {
        return await postChat('http://127.0.0.1:8000/api/chat');
      } catch (directError) {
        console.error('Chat API Error:', directError);
      }

      return {
        response: "I'm having trouble connecting to MindGuard right now. Please start the Python backend on port 8000, then refresh and try again.",
        sentiment: "neutral",
        action: "none"
      };
    }
  }
};
