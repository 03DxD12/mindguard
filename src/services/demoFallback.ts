/**
 * MindGuard Client-Side Demo Fallback Service
 * 
 * Provides mock API responses for GitHub Pages / static hosting when the
 * Python FastAPI backend is not accessible.
 * 
 * When running with the live backend, real responses take precedence.
 * If a request fails (404/network error), this service seamlessly provides
 * rich, realistic data so recruiters and portfolio reviewers can explore
 * all features (Chatbot, SuperAdmin, Staff Dashboard, Mood, Journal, etc.).
 */

import axios from 'axios';

// ── 1. Demo Datastores ──────────────────────────────────────────────────────

export const DEMO_ADMIN_USER = {
  id: 1,
  email: 'adminkapeeryu@edu.ph',
  role: 'admin',
  fullname: 'MindGuard Administrator',
  student_id: null,
  program: null,
  is_primary_admin: true,
  trusted_contacts: []
};

export const DEMO_STAFF_USER = {
  id: 2,
  email: 'kapeeryu@mindguard.edu.ph',
  role: 'staff',
  fullname: 'Ka-PEER Yu Staff',
  student_id: null,
  program: 'Ka-PEER Yu',
  is_primary_admin: false,
  trusted_contacts: []
};

let demoAlerts = [
  {
    id: 101,
    session_id: 'stud-B341',
    risk_level: 3,
    mood: 'Crisis',
    action: 'crisis_hotline',
    timestamp: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    is_reviewed: false
  },
  {
    id: 102,
    session_id: 'stud-A198',
    risk_level: 2,
    mood: 'Stressed',
    action: 'counselor_referral',
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    is_reviewed: false
  },
  {
    id: 103,
    session_id: 'stud-C890',
    risk_level: 2,
    mood: 'Anxious',
    action: 'wellness_check',
    timestamp: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
    is_reviewed: true
  },
  {
    id: 104,
    session_id: 'stud-D412',
    risk_level: 1,
    mood: 'Sad',
    action: 'guided_breathing',
    timestamp: new Date(Date.now() - 1000 * 60 * 720).toISOString(),
    is_reviewed: true
  }
];

let demoStaffList = [
  {
    id: 1,
    fullname: 'MindGuard Administrator',
    email: 'adminkapeeryu@edu.ph',
    role: 'Guidance Office',
    is_primary: true
  },
  {
    id: 2,
    fullname: 'Ka-PEER Yu Staff',
    email: 'kapeeryu@mindguard.edu.ph',
    role: 'Ka-PEER Yu',
    is_primary: false
  },
  {
    id: 3,
    fullname: 'Maria Santos, RGC',
    email: 'msantos@lspu.edu.ph',
    role: 'Guidance Office',
    is_primary: false
  }
];

let demoStudentsList = [
  {
    id: 11,
    fullname: 'Juan Dela Cruz',
    email: 'jdelacruz@lspu.edu.ph',
    student_id: '2023-01452',
    program: 'BS Information Technology',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 15).toISOString()
  },
  {
    id: 12,
    fullname: 'Alyssa Reyes',
    email: 'areyes@lspu.edu.ph',
    student_id: '2022-03918',
    program: 'BS Psychology',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString()
  },
  {
    id: 13,
    fullname: 'Mark Anthony Diaz',
    email: 'mdiaz@lspu.edu.ph',
    student_id: '2024-00219',
    program: 'BS Computer Science',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5).toISOString()
  },
  {
    id: 14,
    fullname: 'Patricia Mae Garcia',
    email: 'pgarcia@lspu.edu.ph',
    student_id: '2023-08711',
    program: 'BS Education',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 40).toISOString()
  }
];

let demoSystemLogs = [
  {
    id: 501,
    actor_admin_email: 'adminkapeeryu@edu.ph',
    action_type: 'STAFF_ADDED',
    target_email: 'msantos@lspu.edu.ph',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString()
  },
  {
    id: 502,
    actor_admin_email: 'kapeeryu@mindguard.edu.ph',
    action_type: 'ALERT_REVIEWED',
    target_email: 'stud-C890',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 6).toISOString()
  },
  {
    id: 503,
    actor_admin_email: 'system',
    action_type: 'CRISIS_ALERT_ESCALATED',
    target_email: 'stud-B341',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString()
  },
  {
    id: 504,
    actor_admin_email: 'adminkapeeryu@edu.ph',
    action_type: 'PRIMARY_ADMIN_LOGIN',
    target_email: 'adminkapeeryu@edu.ph',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString()
  }
];

// ── 2. Empathetic Chatbot Engine (Client-Side Demo Fallback) ────────────────

export function generateDemoChatResponse(
  message: string,
  history: string[] = [],
  turn: number = 0,
  mood: string = 'Okay'
): {
  response: string;
  sentiment: string;
  action: string;
  reasoning: Record<string, any>;
} {
  const lower = (message || '').toLowerCase();
  const contextMeta = { turn, history_depth: history.length };

  // Crisis detection
  const crisisPatterns = [
    'suicide', 'kill myself', 'end my life', 'want to die', 'end it all',
    'hurt myself', 'ayaw ko na mabuhay', 'gusto ko nang mawala', 'magpakamatay'
  ];
  if (crisisPatterns.some(p => lower.includes(p))) {
    return {
      response: "I hear how much pain you're in, and your safety is the most important thing right now. Please know you are not alone. Reach out immediately to the National Center for Mental Health Crisis Hotline at 1553 (toll-free) or Hopeline Philippines at 0917-558-4673. The LSPU Guidance & Counseling Office is also ready to support you. Please connect with someone who can help keep you safe.",
      sentiment: 'Crisis',
      action: 'crisis_hotline',
      reasoning: {
        fused_intent: 'crisis_intervention',
        fused_risk_level: 3,
        emotion: 'distressed',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Academic stress
  if (
    lower.includes('exam') || lower.includes('thesis') || lower.includes('grade') ||
    lower.includes('deadline') || lower.includes('bagsak') || lower.includes('school') ||
    lower.includes('study') || lower.includes('project') || lower.includes('overwhelmed') ||
    lower.includes('stress')
  ) {
    return {
      response: "Academic pressure can feel overwhelmingly heavy, lalo na kapag sabay-sabay ang requirements. Take a gentle breath — your worth as a person is not defined by any single grade or project. Would you like to try a quick 2-minute box breathing reset, or talk through what's feeling most demanding right now?",
      sentiment: 'Stressed',
      action: 'stress_reduction',
      reasoning: {
        fused_intent: 'academic_stress',
        fused_risk_level: 1,
        emotion: 'stressed',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Sadness / Loneliness
  if (
    lower.includes('sad') || lower.includes('malungkot') || lower.includes('lonely') ||
    lower.includes('alone') || lower.includes('crying') || lower.includes('depress') ||
    lower.includes('down') || lower.includes('umiiyak')
  ) {
    return {
      response: "I'm really sorry you're feeling down today. Nandito ako para makinig. It takes courage to acknowledge sadness, and it's completely okay not to be okay all the time. If you feel comfortable sharing, what's been weighing on your heart the most?",
      sentiment: 'Sad',
      action: 'emotional_support',
      reasoning: {
        fused_intent: 'emotional_support',
        fused_risk_level: 1,
        emotion: 'sad',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Anxiety / Panic
  if (
    lower.includes('anxious') || lower.includes('kinakabahan') || lower.includes('panic') ||
    lower.includes('takot') || lower.includes('scared') || lower.includes('nervous') ||
    lower.includes('overthinking')
  ) {
    return {
      response: "I hear you. When anxiety builds up, thoughts can race so quickly. Let's ground ourselves for a second: feel your feet resting firmly on the floor. Take a slow inhale for 4 seconds, hold for 2, and gently let it out. What thoughts are feeling loudest right now?",
      sentiment: 'Anxious',
      action: 'grounding_exercise',
      reasoning: {
        fused_intent: 'anxiety_management',
        fused_risk_level: 1,
        emotion: 'nervous',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Greetings
  if (
    lower.includes('hello') || lower.includes('hi') || lower.includes('kamusta') ||
    lower.includes('hey') || lower.includes('good morning') || lower.includes('good afternoon')
  ) {
    return {
      response: "Hello! Ako si MindGuard, your safe, private campus companion. Whether you're navigating a busy week or just need a mindful moment to pause, I'm here. How are you feeling today?",
      sentiment: 'Okay',
      action: 'greeting',
      reasoning: {
        fused_intent: 'greeting',
        fused_risk_level: 0,
        emotion: 'calm',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Gratitude / Closing
  if (
    lower.includes('thank') || lower.includes('salamat') || lower.includes('thanks') ||
    lower.includes('bye') || lower.includes('ok na')
  ) {
    return {
      response: "Walang anuman! I'm really glad we could take this moment together. Remember to be patient and kind with yourself today. I'm always here whenever you need a safe space.",
      sentiment: 'Great',
      action: 'closing',
      reasoning: {
        fused_intent: 'gratitude',
        fused_risk_level: 0,
        emotion: 'grateful',
        ai_provider: 'client_demo_engine'
      }
    };
  }

  // Default empathetic conversation
  return {
    response: "Naririnig kita. Nandito ako para makinig sa kahit anong gusto mong pag-usapan nang walang judgment. Can you tell me a little bit more about what you're experiencing today?",
    sentiment: mood || 'Okay',
    action: 'clarification',
    reasoning: {
      fused_intent: 'general_support',
      fused_risk_level: 0,
      emotion: 'receptive',
      ai_provider: 'client_demo_engine',
      ...contextMeta
    }
  };
}

// ── 3. Central Request Handler for Demo Fallback ────────────────────────────

export function handleDemoApiRequest(
  url: string,
  method: string = 'GET',
  bodyData?: any
): any | null {
  const normMethod = (method || 'GET').toUpperCase();
  const cleanUrl = url.split('?')[0];

  let body = bodyData;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body);
    } catch {
      body = {};
    }
  }

  // 1. Chat
  if (cleanUrl.endsWith('/api/chat') && normMethod === 'POST') {
    return generateDemoChatResponse(
      body?.message || '',
      body?.history || [],
      body?.turn || 0,
      body?.mood || 'Okay'
    );
  }

  // 2. Login
  if (cleanUrl.endsWith('/api/login') && normMethod === 'POST') {
    const email = (body?.email || '').toLowerCase().trim();
    const password = body?.password || '';

    // Primary Admin
    if (email === 'adminkapeeryu@edu.ph') {
      if (password === 'adminpiyu123') {
        return {
          status: 'success',
          message: 'Welcome back, adminkapeeryu@edu.ph',
          user: DEMO_ADMIN_USER
        };
      }
      throw new Error('Invalid email or password');
    }

    // Staff
    if (email === 'kapeeryu@mindguard.edu.ph') {
      if (password === 'kapeeryu123') {
        return {
          status: 'success',
          message: 'Welcome back, kapeeryu@mindguard.edu.ph',
          user: DEMO_STAFF_USER
        };
      }
      throw new Error('Invalid email or password');
    }

    // Demo student login (accepts student logins with password)
    if (email.includes('@') && password) {
      return {
        status: 'success',
        message: `Welcome back, ${email}`,
        user: {
          id: 10,
          email,
          role: 'student',
          fullname: email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
          student_id: '2024-00188',
          program: 'BS Information Technology',
          is_primary_admin: false,
          trusted_contacts: []
        }
      };
    }

    throw new Error('Invalid email or password');
  }

  // 3. Signup
  if (cleanUrl.endsWith('/api/signup') && normMethod === 'POST') {
    const newUser = {
      id: Date.now(),
      email: body?.email || 'student@lspu.edu.ph',
      role: 'student',
      fullname: body?.fullname || 'Student User',
      student_id: body?.student_id || '2024-99999',
      program: body?.program || 'College Student',
      is_primary_admin: false,
      trusted_contacts: []
    };
    return {
      status: 'success',
      message: 'Sign up successful',
      user: newUser
    };
  }

  // 4. Admin Summary
  if (cleanUrl.endsWith('/api/admin/summary') && normMethod === 'GET') {
    return {
      total_active_students: 48,
      conversations_today: 19,
      crisis_alerts: demoAlerts.filter(a => !a.is_reviewed && a.risk_level === 3).length,
      students_at_risk: demoAlerts.filter(a => a.risk_level >= 2).length
    };
  }

  // 5. Admin Mood Analytics
  if (cleanUrl.endsWith('/api/admin/mood-analytics') && normMethod === 'GET') {
    return {
      Happy: 24,
      Okay: 48,
      Stressed: 52,
      Sad: 28,
      Crisis: 3,
      Anxious: 36,
      Angry: 12,
      Insecure: 16
    };
  }

  // 6. Admin Risk Analytics
  if (cleanUrl.endsWith('/api/admin/risk-analytics') && normMethod === 'GET') {
    return {
      level_0: 62,
      level_1: 34,
      level_2: 11,
      level_3: 3
    };
  }

  // 7. Admin Risk Trends
  if (cleanUrl.endsWith('/api/admin/risk-trends') && normMethod === 'GET') {
    const trends = [];
    const now = new Date();
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      trends.push({
        date: d.toISOString().split('T')[0],
        level_0: Math.floor(8 + Math.random() * 6),
        level_1: Math.floor(4 + Math.random() * 5),
        level_2: Math.floor(1 + Math.random() * 3),
        level_3: i % 4 === 0 ? 1 : 0
      });
    }
    return trends;
  }

  // 8. Admin Alerts
  if (cleanUrl.endsWith('/api/admin/alerts') && normMethod === 'GET') {
    return demoAlerts;
  }

  // 9. Alert Review
  if (cleanUrl.includes('/api/admin/alerts/') && cleanUrl.endsWith('/review') && normMethod === 'PUT') {
    const parts = cleanUrl.split('/');
    const id = parseInt(parts[parts.length - 2], 10);
    demoAlerts = demoAlerts.map(a => a.id === id ? { ...a, is_reviewed: true } : a);
    return { status: 'success' };
  }

  // 10. Admin Students
  if (cleanUrl.endsWith('/api/admin/students')) {
    if (normMethod === 'GET') {
      return demoStudentsList;
    }
    if (normMethod === 'POST') {
      const newStudent = {
        id: Date.now(),
        fullname: body?.fullname || 'New Student',
        email: body?.email || 'student@lspu.edu.ph',
        student_id: body?.student_id || '2024-00000',
        program: body?.program || 'General',
        created_at: new Date().toISOString()
      };
      demoStudentsList.unshift(newStudent);
      return { status: 'success', student: newStudent };
    }
  }

  // 11. Admin Staff
  if (cleanUrl.endsWith('/api/admin/staff')) {
    if (normMethod === 'GET') {
      return demoStaffList;
    }
    if (normMethod === 'POST') {
      const newStaff = {
        id: Date.now(),
        fullname: body?.fullname || 'New Staff',
        email: body?.email || 'staff@mindguard.edu.ph',
        role: body?.role || 'Ka-PEER Yu',
        is_primary: false
      };
      demoStaffList.push(newStaff);
      return { status: 'success', staff: newStaff };
    }
  }

  // 12. Admin System Logs
  if (cleanUrl.endsWith('/api/admin/system-logs') && normMethod === 'GET') {
    return demoSystemLogs;
  }

  // 13. Daily Affirmations
  if (cleanUrl.includes('/api/affirmation') || cleanUrl.includes('/api/affirmations')) {
    return {
      status: 'success',
      affirmation: 'You have navigated tough days before, and you possess the inner strength to meet today with patience.',
      text: 'You have navigated tough days before, and you possess the inner strength to meet today with patience.'
    };
  }

  // 14. Mood logs
  if (cleanUrl.includes('/api/mood/')) {
    if (normMethod === 'POST') {
      return { status: 'success', id: Date.now(), mood: body?.mood || 'Okay' };
    }
    if (cleanUrl.endsWith('/analytics')) {
      return {
        summary: { average_score: 3.6, total_entries: 14, predominant_mood: 'Okay' },
        timeline: [
          { date: '2026-10-20', mood: 'Good', value: 4 },
          { date: '2026-10-22', mood: 'Stressed', value: 2 },
          { date: '2026-10-24', mood: 'Okay', value: 3 },
          { date: '2026-10-26', mood: 'Great', value: 5 }
        ]
      };
    }
    return [
      { id: 1, mood: 'Okay', value: 3, note: 'Regular study day', timestamp: new Date().toISOString() },
      { id: 2, mood: 'Good', value: 4, note: 'Group study session', timestamp: new Date(Date.now() - 86400000).toISOString() }
    ];
  }

  // 15. Journal entries
  if (cleanUrl.includes('/api/journal/')) {
    if (normMethod === 'POST') {
      return {
        status: 'success',
        id: Date.now(),
        themes: ['reflection', 'mindfulness'],
        risk_indicators: []
      };
    }
    return [
      {
        id: 1,
        text: 'Reflecting on the week and feeling grateful for small progress on assignments.',
        mood: 'Calm',
        timestamp: new Date().toISOString(),
        themes: ['gratitude', 'academics']
      }
    ];
  }

  // 16. Profile updates
  if (cleanUrl.includes('/api/profile/')) {
    return { status: 'success', message: 'Profile updated successfully' };
  }

  return null;
}

// ── 4. Global Interceptors Registration ─────────────────────────────────────

export function initDemoInterceptors(): void {
  // A. Hook Axios for /api/admin calls
  axios.interceptors.response.use(
    response => response,
    async error => {
      const config = error.config;
      if (config && config.url && config.url.includes('/api/')) {
        try {
          const fallbackData = handleDemoApiRequest(config.url, config.method, config.data);
          if (fallbackData !== null) {
            console.info(`[MindGuard Demo Mode] Handled axios fallback for ${config.method?.toUpperCase()} ${config.url}`);
            return {
              data: fallbackData,
              status: 200,
              statusText: 'OK',
              headers: {},
              config
            };
          }
        } catch (demoErr: any) {
          return Promise.reject(new Error(demoErr.message || 'Demo request failed'));
        }
      }
      return Promise.reject(error);
    }
  );

  // B. Hook window.fetch for /api/ calls
  if (typeof window !== 'undefined' && window.fetch) {
    const nativeFetch = window.fetch.bind(window);

    window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = typeof input === 'string'
        ? input
        : input instanceof URL
        ? input.href
        : (input as Request).url;

      const isApiCall = url.includes('/api/');

      if (!isApiCall) {
        return nativeFetch(input, init);
      }

      try {
        const response = await nativeFetch(input, init);
        // If server returned 404 or 502/503 for an API call (typical of static GitHub Pages hosting)
        if (!response.ok && (response.status === 404 || response.status >= 500)) {
          const fallbackData = handleDemoApiRequest(url, init?.method, init?.body);
          if (fallbackData !== null) {
            console.info(`[MindGuard Demo Mode] Handled fetch fallback for ${init?.method || 'GET'} ${url} (status was ${response.status})`);
            return new Response(JSON.stringify(fallbackData), {
              status: 200,
              headers: { 'Content-Type': 'application/json' }
            });
          }
        }
        return response;
      } catch (networkError: any) {
        // Network error (e.g. backend server completely offline or cross-origin refused)
        try {
          const fallbackData = handleDemoApiRequest(url, init?.method, init?.body);
          if (fallbackData !== null) {
            console.info(`[MindGuard Demo Mode] Handled fetch offline fallback for ${init?.method || 'GET'} ${url}`);
            return new Response(JSON.stringify(fallbackData), {
              status: 200,
              headers: { 'Content-Type': 'application/json' }
            });
          }
        } catch (demoErr: any) {
          // If demo handler explicitly rejected (e.g. wrong password)
          return new Response(JSON.stringify({ detail: demoErr.message }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        throw networkError;
      }
    };
  }
}
