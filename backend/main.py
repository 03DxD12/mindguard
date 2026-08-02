"""
MindGuard Hybrid AI Chatbot — Mental Health Support Engine V11
==============================================================
Architecture:
  User Message → Semantic Understanding (all-MiniLM-L6-v2)
               → Emotion Classifier (Supervised ML)
               → BERT-like DL Analysis (LSTM Severity)
               → Risk Fusion Scoring Engine
               → Context-Aware Response Generator
               → Safety Filter
               → Chatbot Response → SQLite DB
               → Mood Analytics / Risk Monitoring / Staff Dashboard
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
from collections import defaultdict, deque
import re
import random
import logging
import json
import os
import datetime
import hashlib
import unicodedata
import numpy as np

# ── Database Imports ───────────────────────────────────────────────────────
from sqlalchemy.orm import Session
from sqlalchemy import func
import models
from database import SessionLocal, engine, get_db

# Create all database tables based on models.py
models.Base.metadata.create_all(bind=engine)

# ── 1. Scikit-learn (Machine Learning Stack) ───────────────────────────────
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.cluster import KMeans
from sklearn.semi_supervised import SelfTrainingClassifier

# ── 2. TensorFlow/Keras (Neural Network Stack) ────────────────────────────
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF warnings
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Embedding, GlobalMaxPooling1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

# ── 3. NLP Utilities ───────────────────────────────────────────────────────
import nltk
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from rapidfuzz import process as fuzz_process

# ── 4. Semantic Intelligence (Sentence Transformers) ──────────────────────
from chatbot import (
    semantic_model, encode_text, encode_texts,
    get_emotion_match, get_semantic_intent, get_semantic_risk_score,
    compute_embedding_similarity, analyze_text_themes,
    ANCHOR_RISK_LEVELS,
)
from ai_service import AIContext, AIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password Hashing Context
import bcrypt as _bcrypt

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

app = FastAPI(title="MindGuard Hybrid AI Chatbot (ML + DL + Semantic)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# DATA MODELS (Pydantic Schemas)
# =============================================================================
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[str]] = []
    session_id: Optional[str] = "default"
    turn: int = 0
    mood: Optional[str] = "Okay"

class ChatResponse(BaseModel):
    response: str
    sentiment: Optional[str] = "neutral"
    action: Optional[str] = None
    reasoning: Optional[Dict] = None

class UpdateProfileRequest(BaseModel):
    fullname: str
    email: str
    trusted_contacts: Optional[List[str]] = []

class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateAdminRequest(BaseModel):
    fullname: str
    email: str
    role: str
    password: str

class CreateStudentRequest(BaseModel):
    fullname: str
    email: str
    student_id: str
    program: str
    password: str

class UpdateStudentRequest(BaseModel):
    fullname: str
    email: str
    program: str

class UpdateAdminRequest(BaseModel):
    fullname: str
    email: str
    role: str

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateStaffRequest(BaseModel):
    fullname: str
    email: str
    role: str  # "Guidance Office" or "Ka-PEER Yu"
    password: str
    confirm_password: Optional[str] = None

class UpdateStaffRequest(BaseModel):
    fullname: str
    email: str
    role: str

class SaveAffirmationRequest(BaseModel):
    text: str

class MoodLogRequest(BaseModel):
    mood: str
    value: int  # 1-5
    note: Optional[str] = None

class JournalEntryRequest(BaseModel):
    text: str
    mood: Optional[str] = None


# =============================================================================
# STEP 1 — TEXT NORMALIZER
# =============================================================================
def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation for matching only (NOT for display)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text)

# =============================================================================
# STEP 2 — FUZZY TYPO CORRECTOR
# =============================================================================
KNOWN_CRISIS_TERMS = [
    "suicide", "kill myself", "magpapakamatay", "overdose",
    "laslas", "end my life", "hurt myself", "wala na akong rason",
    "gusto ko mamatay", "ayoko na mabuhay", "tired of being alive",
    "everyone would be better without me", "i dont want to exist",
]

def fuzzy_preprocess(text: str) -> str:
    """Returns standard normalized text for Regex checking."""
    return normalize_text(text)

# =============================================================================
# STEP 3 — LAYER 1: HARDENED CRISIS DETECTION (HIGHEST PRIORITY)
# =============================================================================
DIRECT_SUICIDE = [
    r"\bmagpapakamatay\b", r"\bkill\s+myself\b", r"\bend\s+my\s+life\b",
    r"\bwant\s+to\s+die\b", r"\bgusto\s+ko\s+mamatay\b",
    r"\bayoko\s+na\s+mabuhay\b", r"\bsuicide\b", r"\bpag-alay\s+ng\s+buhay\b",
]
METHOD_REQUEST = [
    r"\boverdose\b", r"\blaslas\b", r"\bhurt\s+myself\b",
    r"\bsaktan\s+sarili\b", r"\bpaano\s+mamatay\b",
    r"\bhow\s+to\s+kill\b", r"\bpills\b.*\bdie\b",
]
HOPELESSNESS = [
    r"\bwala\s+na\s+akong\s+rason\b", r"\bno\s+reason\s+to\s+live\b",
    r"\bwala\s+na\b.*\bpag\-asa\b", r"\bno\s+hope\b",
    r"\bmawala\s+na\s+lang\b", r"\bpagod\s+na\s+ako\s+mabuhay\b",
]
INDIRECT_HIGH_RISK = [
    r"\beveryone\s+would\s+be\s+better\s+without\s+me\b",
    r"\bi\s+don.?t\s+want\s+to\s+exist\b",
    r"\btired\s+of\s+being\s+alive\b",
    r"\bi\s+can.?t\s+do\s+this\s+anymore\b",
    r"\blahat\s+mas\s+magiging\s+okay\s+kung\s+wala\s+ako\b",
    r"\bit.?s\s+peaceful\s+when\s+everything\s+stops\b",
    r"\bi\s+just\s+want\s+it\s+to\s+stop\b",
]
PLAN_SIGNALS = [
    r"\btonight\b.*\b(die|kill|end)\b",
    r"\btomorrow\b.*\b(last|final|goodbye)\b",
    r"\bna\s+may\s+plano\s+na\s+ako\b",
    r"\bi\s+have\s+a\s+plan\b",
    r"\bna\s+nag\s*-\s*attempt\b",
    r"\btried\s+before\b",
]
DEPENDENCE_PHRASES = [
    r"\byou.?re\s+the\s+only\s+one\s+i\s+have\b",
    r"\bdon.?t\s+leave\s+me\b",
    r"\bi\s+only\s+trust\s+you\b",
    r"\bwala\s+na\s+akong\s+ibang\s+tatanungin\b",
]
FALSE_POSITIVE_CONTEXT = [
    r"\bexam\b.*\bdie\b", r"\bdie\s+laughing\b",
    r"\bi\s+want\s+to\s+die\s+from\s+(laughter|laughing|embarrassment)\b",
    r"\bkill\s+it\b",
]

ALL_CRISIS_PATTERNS = DIRECT_SUICIDE + METHOD_REQUEST + HOPELESSNESS + INDIRECT_HIGH_RISK

def crisis_detection(text: str) -> Optional[dict]:
    """HARD OVERRIDE. Returns crisis dict immediately if ANY pattern matches."""
    preprocessed = fuzzy_preprocess(text)
    for pat in FALSE_POSITIVE_CONTEXT:
        if re.search(pat, preprocessed, re.IGNORECASE):
            return None
    has_plan = any(re.search(p, preprocessed, re.IGNORECASE) for p in PLAN_SIGNALS)
    for pat in ALL_CRISIS_PATTERNS:
        if re.search(pat, preprocessed, re.IGNORECASE):
            level = "CRISIS_PLAN" if has_plan else "CRISIS"
            return {"level": level, "override": True, "pattern": pat}
    return None

# =============================================================================
# STEP 4 — LAYER 2: EMOTIONAL INTENSITY SCORING
# =============================================================================
sia = SentimentIntensityAnalyzer()

NEGATIVE_INTENSITY_WORDS = [
    "pagod", "sawa", "galit", "iyak", "luha", "desperado",
    "exhausted", "drained", "hopeless", "helpless", "overwhelmed",
    "panic", "anxious", "ngipin", "scared", "terrified",
]

def emotional_intensity(text: str) -> str:
    """Returns 'low', 'moderate', or 'high'."""
    normalized = normalize_text(text)
    scores = sia.polarity_scores(text)
    compound = scores["compound"]
    words = normalized.split()
    neg_hits = sum(1 for w in words if w in NEGATIVE_INTENSITY_WORDS)
    neg_density = neg_hits / max(len(words), 1)
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)

    score = 0
    if compound <= -0.6: score += 2
    elif compound <= -0.3: score += 1
    if neg_density >= 0.15: score += 2
    elif neg_density >= 0.07: score += 1
    if caps_ratio >= 0.3: score += 1

    if score >= 4: return "high"
    if score >= 2: return "moderate"
    return "low"

# =============================================================================
# STEP 5 — LAYER 3: SESSION MEMORY & ESCALATION MONITOR
# =============================================================================
_sessions: Dict[str, dict] = defaultdict(lambda: {
    "theme_counts": defaultdict(int),
    "distress_history": deque(maxlen=10),
    "used_responses": set(),
    "used_followups": set(),
    "turn": 0,
    "message_embeddings": deque(maxlen=10),  # Store last 10 embeddings for context
    "message_texts": deque(maxlen=10),        # Store last 10 messages for context
    "emotion_trajectory": deque(maxlen=10),    # Track emotional progression
    "last_intents": deque(maxlen=5),           # Track intent history
    "last_response_hashes": deque(maxlen=10),  # Anti-repetition
})

def monitor_escalation(session_id: str, intent: str, intensity: str) -> dict:
    """Track themes and distress history. Returns escalation flags."""
    session = _sessions[session_id]
    session["theme_counts"][intent] += 1
    session["distress_history"].append(intensity)
    session["turn"] += 1
    session["last_intents"].append(intent)

    theme_repeat = session["theme_counts"][intent] >= 3
    recent = list(session["distress_history"])[-3:]
    intensity_map = {"low": 0, "moderate": 1, "high": 2}
    worsening = (
        len(recent) == 3
        and intensity_map.get(recent[2], 0) > intensity_map.get(recent[0], 0)
    )

    # Detect consecutive Level 2+ interactions
    consecutive_distress = (
        len(recent) >= 2
        and all(intensity_map.get(r, 0) >= 1 for r in recent[-2:])
    )

    return {
        "theme_repeat": theme_repeat,
        "worsening": worsening,
        "consecutive_distress": consecutive_distress,
        "escalate": theme_repeat or worsening or consecutive_distress,
        "turn": session["turn"],
    }

def add_message_to_session(session_id: str, text: str, embedding: np.ndarray):
    """Store message text and embedding in session memory."""
    session = _sessions[session_id]
    session["message_embeddings"].append(embedding)
    session["message_texts"].append(text)

def add_emotion_to_trajectory(session_id: str, emotion: str, risk_level: int):
    """Track emotional progression."""
    session = _sessions[session_id]
    session["emotion_trajectory"].append({"emotion": emotion, "risk_level": risk_level})

def get_emotional_trend(session_id: str) -> str:
    """Analyze emotional trajectory: 'improving', 'stable', 'declining'."""
    trajectory = list(_sessions[session_id]["emotion_trajectory"])
    if len(trajectory) < 3:
        return "stable"
    recent_risks = [e["risk_level"] for e in trajectory[-5:]]
    avg_recent = sum(recent_risks[-3:]) / 3
    avg_earlier = sum(recent_risks[:max(len(recent_risks)-3, 1)]) / max(len(recent_risks)-3, 1)
    if avg_recent > avg_earlier + 0.3:
        return "declining"
    elif avg_recent < avg_earlier - 0.3:
        return "improving"
    return "stable"

def get_used_responses(session_id: str) -> set:
    return _sessions[session_id]["used_responses"]

def mark_response_used(session_id: str, response_key: str):
    _sessions[session_id]["used_responses"].add(response_key)

def is_response_repeated(session_id: str, response_text: str) -> bool:
    """Check if this exact response was recently used (anti-repetition)."""
    h = hashlib.md5(response_text.encode()).hexdigest()[:12]
    session = _sessions[session_id]
    if h in session["last_response_hashes"]:
        return True
    session["last_response_hashes"].append(h)
    return False


# =============================================================================
# STEP 6 — LAYER 4: EXPANDED ML INTENT CLASSIFIER (Scikit-Learn)
# =============================================================================
TRAINING_DATA = [
    # academic_stress (expanded)
    ("I failed my exam and I don't know what to do", "academic_stress"),
    ("My thesis is killing me, I can't finish it", "academic_stress"),
    ("Bagsak na naman ako sa subject ko", "academic_stress"),
    ("The deadline is tomorrow and I haven't started", "academic_stress"),
    ("I'm so stressed about my grades", "academic_stress"),
    ("Hindi ko ma-gets yung lesson, nahuhuli na ako", "academic_stress"),
    ("My professor is so unfair with grades", "academic_stress"),
    ("I have three exams this week and I'm not ready", "academic_stress"),
    ("Thesis defense ko bukas, wala pa akong laman", "academic_stress"),
    ("I think I'm going to fail this semester", "academic_stress"),
    ("Pressure sa school, hindi ko na kaya", "academic_stress"),
    ("Too many assignments, I am drowning", "academic_stress"),
    ("I can't keep up with my coursework anymore", "academic_stress"),
    ("My GPA is dropping and I feel terrible", "academic_stress"),
    ("The workload this semester is unbearable", "academic_stress"),
    ("I stayed up all night studying but still feel unprepared", "academic_stress"),
    ("Sobrang daming requirements, hindi ko na alam saan magsisimula", "academic_stress"),
    ("I feel like a fraud, everyone else understands but me", "academic_stress"),

    # relationship_issues (expanded)
    ("My boyfriend and I broke up and I'm devastated", "relationship_issues"),
    ("Naghiwalay kami ng jowa ko", "relationship_issues"),
    ("I feel like my partner doesn't listen to me", "relationship_issues"),
    ("I'm having trust issues with my boyfriend", "relationship_issues"),
    ("My ex keeps contacting me and I don't know what to do", "relationship_issues"),
    ("Parang hindi na ko mahal ng jowa ko", "relationship_issues"),
    ("I'm scared my partner will leave me", "relationship_issues"),
    ("We keep fighting and I'm exhausted", "relationship_issues"),
    ("Niloko ako ng boyfriend ko", "relationship_issues"),
    ("Heartbroken after long term relationship", "relationship_issues"),
    ("I feel betrayed by someone I trusted", "relationship_issues"),
    ("My relationship is toxic but I can't leave", "relationship_issues"),
    ("Masakit na wala na yung taong mahal mo", "relationship_issues"),

    # family_conflict (expanded)
    ("My parents fight all the time and I'm scared", "family_conflict"),
    ("Nagagalit lagi ang nanay ko sa akin", "family_conflict"),
    ("I feel like my family doesn't understand me", "family_conflict"),
    ("My dad is very strict and I can't breathe", "family_conflict"),
    ("I feel alone even when I'm at home", "family_conflict"),
    ("Palagi kaming nag-aaway ng tatay ko", "family_conflict"),
    ("My parents are separating and I don't know how to cope", "family_conflict"),
    ("Gulo sa bahay, ayaw ko na umuwi", "family_conflict"),
    ("My family expects too much from me and I can't meet their expectations", "family_conflict"),
    ("I wish my parents would stop comparing me to others", "family_conflict"),
    ("Hindi naman nila alam kung gaano kahirap yung pinagdadaanan ko", "family_conflict"),

    # financial_stress (expanded)
    ("I can't pay my tuition this semester", "financial_stress"),
    ("Wala na kaming pera, baka mag-stop out na ako", "financial_stress"),
    ("I'm worried about money and I can't focus", "financial_stress"),
    ("My scholarship got canceled and I don't know what to do", "financial_stress"),
    ("I have to work part time just to pay for college", "financial_stress"),
    ("Baon sa utang ang pamilya namin", "financial_stress"),
    ("Financial emergency, zero balance", "financial_stress"),
    ("I can't afford to eat properly because of money issues", "financial_stress"),
    ("Walang pera para sa allowance, paano makakapasok sa school", "financial_stress"),

    # loneliness (expanded)
    ("I feel like I have no real friends", "loneliness"),
    ("Nobody talks to me in class", "loneliness"),
    ("Parang wala akong kaibigan dito sa school", "loneliness"),
    ("I eat alone every day and it hurts", "loneliness"),
    ("I feel invisible to everyone around me", "loneliness"),
    ("I moved to a new city and I don't know anyone", "loneliness"),
    ("Outcast sa classroom, walang kumakausap", "loneliness"),
    ("No one notices when I'm gone", "loneliness"),
    ("I feel disconnected from everyone around me", "loneliness"),
    ("Parang hindi ako belong sa kahit anong grupo", "loneliness"),
    ("I have people around me but I still feel so alone", "loneliness"),

    # burnout (expanded)
    ("I'm so tired of everything, I can't keep going", "burnout"),
    ("I've been grinding for months and I feel empty", "burnout"),
    ("Pagod na pagod na ako, wala na akong energy", "burnout"),
    ("I don't feel motivated to do anything anymore", "burnout"),
    ("I used to love studying but now I hate it", "burnout"),
    ("I feel like I'm running on empty", "burnout"),
    ("Burnout na yata ako, drain na drain", "burnout"),
    ("I can't find the energy to get out of bed", "burnout"),
    ("Everything feels like a chore now", "burnout"),
    ("I don't care about anything anymore, I'm just going through the motions", "burnout"),

    # general_anxiety (expanded)
    ("I have panic attacks before class", "general_anxiety"),
    ("I'm always worried even when nothing is wrong", "general_anxiety"),
    ("Palagi akong nag-aalala tungkol sa lahat", "general_anxiety"),
    ("My heart races when I have to present in class", "general_anxiety"),
    ("I can't sleep because I overthink everything", "general_anxiety"),
    ("Anxious about the future", "general_anxiety"),
    ("I feel like something bad is always about to happen", "general_anxiety"),
    ("I get anxious in social situations and avoid people", "general_anxiety"),
    ("Hindi ako makatulog sa sobrang kaba at worry", "general_anxiety"),
    ("My anxiety is controlling my life", "general_anxiety"),

    # depression_grief (expanded)
    ("I lost someone I love and I can't move on", "depression_grief"),
    ("Namamatayan ako ng mahal sa buhay", "depression_grief"),
    ("Everything feels dark and hopeless", "depression_grief"),
    ("I haven't left my bed in days", "depression_grief"),
    ("The grief is too heavy, I miss them so much", "depression_grief"),
    ("Walang katapusang lungkot, parang walang liwanag", "depression_grief"),
    ("I don't feel joy in anything anymore", "depression_grief"),
    ("Life feels meaningless and grey", "depression_grief"),
    ("I cry for no reason sometimes", "depression_grief"),
    ("Parang laging maulap ang mundo ko", "depression_grief"),

    # self_esteem (expanded)
    ("I hate how I look, I feel so ugly", "self_esteem"),
    ("I am not good enough for anything", "self_esteem"),
    ("Mababa ang tingin ko sa sarili ko", "self_esteem"),
    ("Everyone else is smarter and better than me", "self_esteem"),
    ("I feel like a total failure", "self_esteem"),
    ("Insecure ako sa lahat ng kasama ko", "self_esteem"),
    ("I compare myself to others and always fall short", "self_esteem"),
    ("I don't deserve good things", "self_esteem"),
    ("Parang walang nagmamahal sa akin dahil pangit ako", "self_esteem"),

    # career_anxiety (expanded)
    ("I don't know what to do with my life after college", "career_anxiety"),
    ("What if I don't get a job after graduation?", "career_anxiety"),
    ("Takot ako sa future, baka maging tambay lang ako", "career_anxiety"),
    ("Is this the right course for me?", "career_anxiety"),
    ("I feel pressured about my career path", "career_anxiety"),
    ("Hindi ko alam kung anong landas ang tatahakin", "career_anxiety"),
    ("Everyone seems to have their life figured out except me", "career_anxiety"),
    ("I'm scared I chose the wrong major", "career_anxiety"),

    # bullying (expanded)
    ("People are spreading rumors about me at school", "bullying"),
    ("Binubully ako ng mga kaklase ko", "bullying"),
    ("I'm being harassed online", "bullying"),
    ("Cyberbullying is taking a toll on my mental health", "bullying"),
    ("They make fun of me every day", "bullying"),
    ("Pinagtutulungan nila ako, ayaw ko na pumasok", "bullying"),
    ("Someone at school is threatening me", "bullying"),
    ("I'm afraid to go to school because of bullies", "bullying"),

    # health_anxiety (expanded)
    ("I'm constantly worried I have a serious illness", "health_anxiety"),
    ("Takot ako na baka may sakit akong malala", "health_anxiety"),
    ("I keep checking my symptoms online and it scares me", "health_anxiety"),
    ("My health is failing and I'm terrified", "health_anxiety"),
    ("Every little pain makes me think the worst", "health_anxiety"),
    ("Hypochondriac na yata ako sa sobrang kaba sa sakit", "health_anxiety"),
    ("I can't stop worrying about my health", "health_anxiety"),

    # general_chat (expanded)
    ("Hello how are you", "general_chat"),
    ("I just wanted to talk to someone", "general_chat"),
    ("Kumusta ka", "general_chat"),
    ("What can you do", "general_chat"),
    ("I'm okay I just wanted to check in", "general_chat"),
    ("Can we just talk", "general_chat"),
    ("Hi there", "general_chat"),
    ("Good morning", "general_chat"),
    ("Hey MindGuard", "general_chat"),
    ("Anong ginagawa mo?", "general_chat"),
    ("Just wanted to say hello", "general_chat"),
    ("I'm doing fine today actually", "general_chat"),

    # seeking_support (expanded)
    ("I need help, can you guide me?", "seeking_support"),
    ("Tulong po, kailangan ko ng makakausap", "seeking_support"),
    ("I want to seek professional help", "seeking_support"),
    ("Saan ba pwedeng mag-reach out?", "seeking_support"),
    ("Please support me through this", "seeking_support"),
    ("Where can I find a counselor?", "seeking_support"),
    ("I need someone to talk to professionally", "seeking_support"),
    ("Can you help me find resources for my mental health?", "seeking_support"),
    ("Paano magpa-counsel sa school?", "seeking_support"),
]

X_train = [t[0] for t in TRAINING_DATA]
y_train = [t[1] for t in TRAINING_DATA]

# TF-IDF + Logistic Regression Pipeline
intent_clf = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
    ("clf", LogisticRegression(max_iter=2000, C=1.5, class_weight='balanced')),
])
intent_clf.fit(X_train, y_train)

def classify_intent(text: str) -> tuple:
    """Returns (intent: str, confidence: float)."""
    probs = intent_clf.predict_proba([text])[0]
    classes = intent_clf.classes_
    idx = probs.argmax()
    return classes[idx], round(float(probs[idx]), 3)

# =============================================================================
# STEP 7 — SEMI-SUPERVISED LOGGING
# =============================================================================
LOG_FILE = os.path.join(os.path.dirname(__file__), "low_confidence_log.jsonl")

def log_low_confidence(text: str, intent: str, confidence: float, intensity: str):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "text_hash": hashlib.md5(text.encode()).hexdigest()[:12],
        "predicted_intent": intent,
        "confidence": confidence,
        "intensity": intensity,
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Could not write log: {e}")

# =============================================================================
# STEP 8 — LANGUAGE DETECTOR
# =============================================================================
class LanguageDetector:
    def __init__(self):
        self.tl_func = {
            "ang", "ng", "sa", "mga", "ay", "na", "ba", "po", "ko",
            "mo", "niya", "kami", "tayo", "sila", "natin", "nila", "ito",
            "hindi", "wala", "kaya", "pero", "kasi", "talaga",
        }
        self.en_func = {
            "the", "a", "an", "is", "are", "was", "were", "to",
            "in", "for", "on", "with", "as", "by", "at", "i", "me",
        }

    def detect(self, text: str) -> str:
        words = set(re.findall(r"\b\w+\b", text.lower()))
        if not words: return "tl"
        tl = len(words & self.tl_func)
        en = len(words & self.en_func)
        total = tl + en
        if total == 0: return "tl"
        ratio = tl / total
        if ratio > 0.65: return "tl"
        if ratio < 0.35: return "en"
        return "taglish"

lang_det = LanguageDetector()


# =============================================================================
# STEP 9 — DYNAMIC RESPONSE ENGINE (Fragment-Based + Follow-Up Questions)
# =============================================================================

DYNAMIC_FRAGMENTS = {
    "validation": {
        "en": [
            "I hear you, and it's completely valid to feel this way.",
            "That sounds like a lot to carry. Thank you for sharing it with me.",
            "I'm listening, and I want you to know your feelings matter.",
            "It takes courage to be this open about what you're going through.",
            "I can sense how much this is weighing on you right now.",
            "That sounds like a difficult situation to carry by yourself.",
            "You've been dealing with a lot lately, and I appreciate you opening up.",
            "What you're feeling is real, and it deserves to be acknowledged.",
        ],
        "tl": [
            "Naririnig kita, at valid na valid ang nararamdaman mo.",
            "Ang bigat niyan, salamat sa pagbabahagi mo sa akin.",
            "Nakikinig ako, at gusto kong malaman mo na mahalaga ang nararamdaman mo.",
            "Kailangan ng lakas ng loob para maging ganito ka-open sa pinagdadaanan mo.",
            "Ramdam ko ang bigat ng dinadala mo ngayon.",
            "Mahirap talaga kapag mag-isa mong dinadala ang lahat.",
            "Salamat sa pagtitiwala at pagbubukas ng loob mo sa akin.",
            "Totoo ang nararamdaman mo, at deserve nitong mapakinggan.",
        ],
        "taglish": [
            "I hear you, and valid na valid ang nararamdaman mo.",
            "That sounds heavy, salamat sa pagbabahagi nito sa akin.",
            "I'm listening, and I want you to know na important ang feelings mo.",
            "It takes courage to be this open about what you're going through.",
            "I can sense na medyo mabigat ang pinagdadaanan mo right now.",
            "That's a lot to carry by yourself, at I appreciate you opening up.",
            "What you're feeling is real, at deserve nitong ma-acknowledge.",
            "You've been dealing with a lot lately, salamat sa pagbukas ng loob.",
        ]
    },
    "reflection": {
        "academic_stress": {
            "en": ["School pressure can feel truly overwhelming, especially with everything on your plate.", "The weight of academic expectations is a heavy thing to balance.", "Missing a deadline or struggling with coursework doesn't define your worth."],
            "tl": ["Mabigat talaga ang pressure sa school, lalo na sa dami ng kailangang gawin.", "Hindi biro ang bigat ng expectations sa pag-aaral.", "Hindi ka nasasakal lang sa deadlines — may karapatan kang huminga."],
            "taglish": ["Ang bigat talaga ng pressure sa school, especially with everything on your plate.", "Hindi biro ang bigat ng academic expectations na kailangang i-balance.", "Missing a deadline doesn't define your worth — kaya mo 'to."],
        },
        "relationship_issues": {
            "en": ["Relationship pain is deeply personal and can feel very isolating.", "It's hard when things with the people we care about aren't going well.", "Heartbreak can feel like losing a part of yourself, and that's valid."],
            "tl": ["Ang sakit sa puso kapag may problema sa mga taong mahalaga sa atin.", "Mahirap talaga kapag hindi okay ang sitwasyon sa relasyon.", "Ang sakit ng puso ay parang nawawala ang isang bahagi ng sarili mo."],
            "taglish": ["Ang hirap talaga kapag may issues sa relationship with the people we care about.", "Relationship pain is deeply personal at minsan ay nakaka-isolate.", "Heartbreak can feel like losing a part of yourself, at valid lang yan."],
        },
        "family_conflict": {
            "en": ["Family tension is such a difficult burden to navigate.", "It's tough when home doesn't feel like the peaceful place it should be.", "You deserve to feel safe and understood, even at home."],
            "tl": ["Ang hirap harapin ng tensyon sa loob mismo ng pamilya.", "Mahirap kapag ang tahanan ay hindi nagbibigay ng kapayapaan.", "Deserve mong maramdaman na ligtas ka at naiintindihan, kahit sa bahay."],
            "taglish": ["Minsan ang hirap i-navigate ng family tension, it's a difficult burden.", "It's tough kapag ang home ay hindi nagbibigay ng peace of mind.", "You deserve to feel safe at understood, even at home."],
        },
        "financial_stress": {
            "en": ["Financial worries can steal your focus and create so much uncertainty.", "Worrying about money while trying to study is an immense burden."],
            "tl": ["Nakakaubos ng lakas ang isipin ang gastusin habang nag-aaral.", "Ang problema sa pera ay parang ulan na walang tigil minsan."],
            "taglish": ["Nakaka-drain iisipin ang financial problems while trying to focus sa studies.", "Financial worries can really create so much uncertainty sa school life."],
        },
        "burnout": {
            "en": ["Burnout is real, and it's a signal that you've been pushing yourself too hard.", "That feeling of being completely drained is your mind and body asking for rest.", "Running on empty isn't sustainable — your body is telling you something important."],
            "tl": ["Totoo ang burnout, at senyales ito na kailangan mo nang mag-slow down.", "Ang pagka-ubos ng lakas ay paraan ng katawan mo para humingi ng pahinga.", "Hindi sustainable ang walang pahinga — may sinasabi ang katawan mo."],
            "taglish": ["Real ang burnout, and it's a signal na push ka na nang push sa limit mo.", "That feeling of being drained is your body's way of asking for rest.", "Running on empty isn't sustainable — your body is telling you something."],
        },
        "general_anxiety": {
            "en": ["Anxiety can make the world feel much louder and more uncertain than it really is.", "That feeling of constant worry is incredibly draining.", "Your mind is trying to protect you, even when the threat isn't clear."],
            "tl": ["Pinapalaki talaga ng anxiety ang mga kaba at pag-aalinlangan natin.", "Nakakaubos ng lakas ang palagiang pag-aalala.", "Ang isip mo ay nagsusumikap na protektahan ka, kahit hindi pa klaro ang banta."],
            "taglish": ["Anxiety can make things feel super uncertain and overwhelming.", "That feeling of constant worry is really draining, physically at mentally.", "Your mind is trying to protect you, kahit na minsan walang clear na threat."],
        },
        "loneliness": {
            "en": ["Loneliness can feel like a cold shadow, even when people are around.", "It's painful to feel like you're facing things all by yourself.", "You reaching out right now shows you're looking for connection, and that matters."],
            "tl": ["Napakahirap ng pakiramdam na mag-isa, kahit may ibang tao pa sa paligid.", "Ang sakit maramdaman na parang wala kang kasama sa laban.", "Ang pagbubukas mo ngayon ay tanda na hinahanap mo ang koneksyon, at mahalaga iyan."],
            "taglish": ["Loneliness can feel like a cold shadow, kahit marami pang tao sa paligid.", "Ang sakit talaga ng feeling na parang you're facing everything all alone.", "You reaching out now shows na you're looking for connection, and that truly matters."],
        },
        "depression_grief": {
            "en": ["The weight of loss and sadness is something no one should have to carry alone.", "Grief is a heavy path, and it's okay to feel completely lost in it for a while.", "There's no timeline for healing — your grief is uniquely yours."],
            "tl": ["Ang bigat ng pangungulila at lungkot ay hindi biro.", "Dugo't pawis ang kailangan para malampasan ang ganitong klaseng lumbay.", "Walang timeline ang paggaling — ang pangungulila mo ay sa iyo lang."],
            "taglish": ["The weight of loss and sadness is something na hindi mo dapat i-carry mag-isa.", "Grief is a heavy path, at okay lang na ma-feel na nawawala ka for a while.", "There's no timeline for healing — your grief is uniquely yours."],
        },
        "self_esteem": {
            "en": ["It's hard when your inner voice is your harshest critic.", "Struggling with self-worth can make every small challenge feel like a mountain.", "The way you see yourself right now isn't the full picture — there's more to you."],
            "tl": ["Mahirap kapag ang sarili nating isip ang pinaka-malupit nating kaaway.", "Ang kawalan ng tiwala sa sarili ay parang tanikala sa ating pag-unlad.", "Ang nakikita mo sa sarili mo ngayon ay hindi pa buong larawan — mas marami ka pa roon."],
            "taglish": ["Ang hirap kapag ang inner voice mo is your harshest critic.", "Struggling with self-worth can make every challenge feel like a mountain.", "The way you see yourself right now isn't the full picture — there's so much more to you."],
        },
        "career_anxiety": {
            "en": ["The uncertainty of the future can feel like a massive, looming shadow.", "It's normal to feel pressured about your path when the road ahead isn't clear."],
            "tl": ["Ang kaba sa kung ano ang mangyayari sa future ay natural lang.", "Mahirap talagang mag-isip ng career path kapag puno ng pressure ang paligid."],
            "taglish": ["Uncertainty about the future can feel like a massive shadow hanging over you.", "Normal lang na ma-pressure sa path mo lalo na kung blurred pa ang road ahead."],
        },
        "bullying": {
            "en": ["No one deserves to be treated that way. Your safety and peace matter.", "Bullying can leave deep scars, but you don't have to face those people alone."],
            "tl": ["Walang may deserve na tratuhin nang ganyan. Mahalaga ka.", "Hindi tama ang ginagawa nila sa'yo, at nandito ako para damayan ka."],
            "taglish": ["No one deserves na ma-treat nang ganyan. Important ang safety at peace mo.", "Bullying can leave deep scars, pero hindi mo kailangang harapin ito alone."],
        },
        "health_anxiety": {
            "en": ["Worrying about your health can create a terrifying loop of fear.", "It's exhausting when every sensation in your body feels like a threat."],
            "tl": ["Nakakapagod ang palagiang takot na baka may malalang sakit.", "Ang pag-aalala sa kalusugan ay nakaka-ubos ng peace of mind."],
            "taglish": ["Health worries can create a scary loop ng fear at anxiety.", "Nakatuon ang attention mo sa body sensations at it feels like a threat."],
        },
        "seeking_support": {
            "en": ["Reaching out for help is a huge, positive step toward healing.", "Asking for support shows so much self-awareness and strength."],
            "tl": ["Ang paghingi ng tulong ay malaking hakbang tungo sa pag-galing.", "Ang pag-seek ng support ay tanda ng iyong katapangan at lakas."],
            "taglish": ["Reaching out for help is a huge at positive step towards healing.", "Asking for support shows so much self-awareness at inner strength."],
        },
        "general_chat": {
            "en": ["I'm here to support you in whatever way I can as your digital companion.", "It's good to connect. I'm ready to listen to whatever is on your mind."],
            "tl": ["Nandito ako para suportahan ka sa abot ng aking makakaya bilang digital companion mo.", "Mabuti at nag-connect tayo. Handa akong makinig sa kahit ano."],
            "taglish": ["I'm here to support you as your digital companion in any way I can.", "It's good to connect. Handa akong makinig sa kahit anong nasa isip mo."],
        },
        "other": {
            "en": ["I'm reflecting on what you've shared and trying to understand your perspective.", "Thank you for letting me in on what you're experiencing."],
            "tl": ["Pinag-iisipan ko ang sinabi mo at sinusubukang intindihin ang sitwasyon mo.", "Salamat sa pagtitiwala at pagbabahagi ng iyong karanasan."],
            "taglish": ["I'm reflecting on what you shared at tinitignan ko ang perspective mo.", "Salamat sa pagtitiwala and for letting me know what you're experiencing."],
        }
    },
    "suggestion": {
        "en": [
            "Maybe we could take a small, deep breath together? It might help ground us.",
            "Have you tried writing down exactly what's on your mind? Sometimes just getting it out helps.",
            "It's okay to take things one tiny step at a time. What feels like the very smallest thing you can handle right now?",
            "Remember that you don't have to figure everything out in this exact moment. Resting is also a form of progress.",
            "Sometimes stepping away from the situation — even for just 5 minutes — can give you a fresh perspective.",
            "Would it help to talk through what happened step by step? We can go at your pace.",
        ],
        "tl": [
            "Gusto mo bang huminga muna tayo nang malalim? Makakatulong ito para kumalma.",
            "Nasubukan mo na bang isulat ang lahat ng nasa isip mo? Nakakagaan din ito ng loob.",
            "Okay lang na dahan-dahan ang pag-usad. Ano ang pinakamaliit na hakbang na kaya mong gawin ngayon?",
            "Tandaan na hindi mo kailangang ayusin ang lahat ngayon din. Ang pagpahinga ay bahagi rin ng pag-unlad.",
            "Minsan ang pag-alis sa sitwasyon — kahit 5 minutos lang — ay makakatulong sa iyo.",
            "Gusto mo bang pag-usapan natin ang nangyari, dahan-dahan? Sa pace mo lang tayo.",
        ],
        "taglish": [
            "Gusto mo bang i-try ang 4-7-8 breathing together? It might help you calm down.",
            "Have you tried writing down your thoughts? Minsan nakakatulong ang ma-release ang nasa isip.",
            "Okay lang na mag-start small. What feels like the smallest thing na pwede mong gawin ngayon?",
            "Remember na hindi mo kailangang i-figure out lahat right now. Resting is progress too.",
            "Sometimes stepping away — kahit 5 minutes lang — can give you fresh perspective.",
            "Gusto mo bang pag-usapan natin step by step? We'll go at your pace.",
        ]
    },
    "presence": {
        "en": "I'm here to listen. Nandito ako para makinig.",
        "tl": "Nandito ako para makinig.",
        "taglish": "Nandito ako para makinig. I'm here to listen.",
    },
    "closing": {
        "en": [
            "I'm right here with you.",
            "I'm listening. Go on when you're ready.",
            "You're not alone in this.",
            "We can talk more about it if you'd like.",
            "Take your time. There's no rush at all.",
            "I'm not going anywhere — I'm here for as long as you need.",
        ],
        "tl": [
            "Nandito lang ako para sa iyo.",
            "Nakikinig ako. Ituloy mo lang kung handa ka na.",
            "Hindi ka nag-iisa sa labang ito.",
            "Pwede pa nating pag-usapan ito kung gusto mo.",
            "Dahan-dahan lang. Walang apuran.",
            "Hindi ako aalis — nandito ako habang kailangan mo.",
        ],
        "taglish": [
            "Nandito lang ako if you need someone to talk to.",
            "Nakikinig ako, kaya ituloy mo lang whenever you're ready.",
            "You're not alone in this fight, nandito ako.",
            "We can talk more about this if you want.",
            "Take your time. Walang apuran.",
            "I'm not going anywhere — nandito ako for as long as you need.",
        ]
    }
}

# ── Follow-Up Questions Engine ─────────────────────────────────────────────
FOLLOW_UP_QUESTIONS = {
    "academic_stress": {
        "en": [
            "What subject or deadline is weighing on you the most right now?",
            "Is there a specific assignment or exam that's been on your mind?",
            "How long have you been feeling this academic pressure?",
            "Is there anyone at school you feel comfortable talking to about this?",
        ],
        "tl": [
            "Anong subject o deadline ang pinaka-mabigat para sa iyo ngayon?",
            "May specific ba na assignment o exam na bumabagabag sa iyo?",
            "Gaano katagal mo nang nararamdaman ang academic pressure na ito?",
            "May kaibigan ka ba sa school na pwede mong pagkuwentuhan?",
        ],
        "taglish": [
            "What subject or deadline ang pinaka-mabigat for you right now?",
            "Is there a specific assignment o exam na nasa isip mo?",
            "How long mo nang nararamdaman itong academic pressure?",
            "May someone ba sa school na comfortable ka i-approach about this?",
        ],
    },
    "relationship_issues": {
        "en": [
            "Would you like to share more about what happened?",
            "How long has this relationship situation been affecting you?",
            "Do you have someone you trust that you can talk to about this?",
        ],
        "tl": [
            "Gusto mo bang magkwento pa tungkol sa nangyari?",
            "Gaano na katagal na naapektuhan ka ng sitwasyon sa relasyon?",
            "Mayroon ka bang taong pinagkakatiwalaan na pwede mong kausapin?",
        ],
        "taglish": [
            "Would you like to share more about what happened?",
            "How long na ba na naapektuhan ka ng situation na ito?",
            "May trusted person ka ba na pwede mong kausapin about this?",
        ],
    },
    "family_conflict": {
        "en": [
            "What happens at home that makes you feel this way?",
            "Do you feel safe when these conflicts happen?",
            "Is there anyone outside your family who supports you?",
        ],
        "tl": [
            "Ano ba ang nangyayari sa bahay na ganito ka makaramdam?",
            "Ligtas ka ba kapag nagaganap ang mga conflict na ito?",
            "May tao ba sa labas ng pamilya mo na nagsu-support sa iyo?",
        ],
        "taglish": [
            "What happens ba at home na ganito ka makaramdam?",
            "Do you feel safe kapag nagaganap ang conflicts?",
            "Is there someone outside your family who supports you?",
        ],
    },
    "loneliness": {
        "en": [
            "What does your typical day look like? Who do you interact with?",
            "Is there a group or activity at school you'd feel comfortable joining?",
            "When was the last time you felt truly connected to someone?",
        ],
        "tl": [
            "Ano ang typical na araw mo? Sino mga kausap mo?",
            "May grupo o activity ba sa school na comfortable ka sumali?",
            "Kailan ka huling nakaramdam na may totoong koneksyon sa isang tao?",
        ],
        "taglish": [
            "What does your typical day look like? Sino mga nakakausap mo?",
            "Is there a group or activity sa school na you'd feel comfortable joining?",
            "When was the last time na you felt truly connected sa someone?",
        ],
    },
    "burnout": {
        "en": [
            "When was the last time you felt truly rested and recharged?",
            "What takes up most of your energy every day?",
            "Have you been able to do anything just for yourself lately?",
        ],
        "tl": [
            "Kailan ka huling nakaramdam na totoong naka-pahinga at naka-recharge?",
            "Ano ang pinaka-nakakaubos ng energy mo araw-araw?",
            "Nakagawa ka ba ng kahit ano para lang sa sarili mo lately?",
        ],
        "taglish": [
            "When was the last time na you felt truly rested at recharged?",
            "Ano ang pinaka-draining sa day-to-day life mo?",
            "Na-try mo ba mag-do ng something for yourself lately?",
        ],
    },
    "general_anxiety": {
        "en": [
            "What worries tend to come up the most for you?",
            "Do you notice any patterns in when your anxiety gets worse?",
            "Have you ever tried any techniques that helped even a little?",
        ],
        "tl": [
            "Ano ang mga worry na palaging bumabalik sa isip mo?",
            "May napapansin ka bang pattern kung kailan lumalala ang anxiety mo?",
            "Nasubukan mo na ba ang kahit anong technique na nakatulong kahit konti?",
        ],
        "taglish": [
            "What worries ang palaging bumabalik sa isip mo?",
            "May napansin ka bang pattern kung kailan lumalala ang anxiety mo?",
            "Have you tried any techniques na nakatulong kahit konti?",
        ],
    },
    "depression_grief": {
        "en": [
            "Would you like to tell me about the person or situation you're grieving?",
            "How has this been affecting your daily life?",
            "Is there anything that brings you even a small moment of comfort?",
        ],
        "tl": [
            "Gusto mo bang ikwento sa akin ang taong o sitwasyong pinangungulilaan mo?",
            "Paano naapektuhan nito ang araw-araw mong buhay?",
            "May kahit anong bagay ba na nagbibigay sa iyo ng kahit maliit na comfort?",
        ],
        "taglish": [
            "Would you like to tell me more about what you're grieving?",
            "How does this affect your daily life?",
            "Is there anything na nagbibigay sa iyo ng kahit maliit na comfort?",
        ],
    },
    "self_esteem": {
        "en": [
            "What kind of thoughts do you have about yourself most often?",
            "Is there something specific that triggered these feelings?",
            "Can you think of one thing you've done recently that you're even a little proud of?",
        ],
        "tl": [
            "Anong klaseng mga thoughts ang palaging nasa isip mo tungkol sa sarili?",
            "May specific ba na nangyari na nag-trigger ng feelings na ito?",
            "May naaalala ka ba na kahit isang bagay na nagawa mo recently na proud ka kahit konti?",
        ],
        "taglish": [
            "What kind of thoughts ang palaging bumabalik about yourself?",
            "Is there something specific na nag-trigger ng feelings na ito?",
            "Can you think of one thing na nagawa mo recently na proud ka kahit konti?",
        ],
    },
    "financial_stress": {
        "en": [
            "What's the most pressing financial concern you're dealing with right now?",
            "Have you been able to explore any financial aid or scholarship options?",
        ],
        "tl": [
            "Ano ang pinaka-urgent na financial concern mo ngayon?",
            "Na-explore mo na ba ang mga financial aid o scholarship options?",
        ],
        "taglish": [
            "What's the most pressing financial concern mo right now?",
            "Have you explored any financial aid o scholarship options?",
        ],
    },
    "career_anxiety": {
        "en": [
            "What part of the future feels most uncertain to you?",
            "Is there a career or field that genuinely interests you?",
        ],
        "tl": [
            "Anong bahagi ng future ang pinaka-uncertain para sa iyo?",
            "May career o field ba na totoong interesado ka?",
        ],
        "taglish": [
            "What part of the future ang feels most uncertain for you?",
            "Is there a career o field na genuinely interesting for you?",
        ],
    },
    "bullying": {
        "en": [
            "Can you tell me a little about what's been happening?",
            "Have you told anyone else about what's going on?",
            "Do you feel safe going to school right now?",
        ],
        "tl": [
            "Pwede mo bang ikwento kahit konti ang nangyayari?",
            "May sinabihan ka na ba ng iba tungkol dito?",
            "Ligtas ka bang pumasok sa school ngayon?",
        ],
        "taglish": [
            "Can you tell me a little about what's been happening?",
            "Sinabihan mo na ba ang ibang tao about this?",
            "Do you feel safe going to school ngayon?",
        ],
    },
    "health_anxiety": {
        "en": [
            "What symptoms are you most worried about right now?",
            "Have you been able to see a doctor about your concerns?",
        ],
        "tl": [
            "Anong symptoms ang pinaka-iniisip mo ngayon?",
            "Nakapunta ka na ba sa doctor tungkol sa concerns mo?",
        ],
        "taglish": [
            "What symptoms ang most worried ka about right now?",
            "Nakapunta ka na ba sa doctor about your concerns?",
        ],
    },
    "seeking_support": {
        "en": [
            "What kind of support are you looking for right now?",
            "Would you like me to share information about campus resources?",
        ],
        "tl": [
            "Anong klase ng support ang hinahanap mo ngayon?",
            "Gusto mo bang mag-share ako ng information tungkol sa campus resources?",
        ],
        "taglish": [
            "What kind of support ang hinahanap mo right now?",
            "Would you like me to share info about campus resources?",
        ],
    },
    "general_chat": {
        "en": [
            "Is there anything specific on your mind today?",
            "How has your week been going so far?",
        ],
        "tl": [
            "May specific ba na nasa isip mo ngayon?",
            "Kumusta ang week mo so far?",
        ],
        "taglish": [
            "Is there anything specific na nasa isip mo today?",
            "How has your week been going so far?",
        ],
    },
}

GROUNDING_TECHNIQUES = {
    "en": [
        "Try this: name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste. This can help ground you in the present moment.",
        "Let's try a breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. Repeat this 3 times.",
        "It might help to get a glass of water and take a short walk, even just around the room.",
        "Try placing your hand on your chest and feeling your heartbeat. Focus on it for 30 seconds.",
    ],
    "tl": [
        "Subukan natin ito: pangalanan mo ang 5 bagay na nakikita mo, 4 na nararamdaman, 3 na naririnig, 2 na naaaamoy, at 1 na nalalasahan. Makakatulong ito.",
        "Subukan nating huminga: huminga ng 4 beses, pigilan ng 4, ilabas ng 6. Ulitin ng 3 beses.",
        "Pwede kang kumuha ng tubig at maglakad sandali, kahit sa paligid lang ng kwarto.",
        "Subukan mong ilagay ang kamay sa dibdib at maramdaman ang tibok ng puso. Focus dito ng 30 segundo.",
    ],
}

CRISIS_RESPONSES = {
    "en": {
        "standard": "I hear you, and I'm concerned about you. What you're feeling is real, and you don't have to face it alone. Nandito ako para makinig. Kapag handa ka, pwede mong kausapin ang Ka-PEER Yu organization o ang Guidance and Counseling Office sa iyong campus.",
        "plan": "I'm genuinely worried about you right now. Your safety is the most important thing. Nandito ako para makinig. Para sa mas malalim na tulong, please speak with the Ka-PEER Yu organization or the Guidance and Counseling Office on your campus right now.",
        "high_risk": "I hear how much pain you're in, and I'm here. Ang kaligtasan mo ang pinaka-importante. Nandito ako para makinig. Please talk to the Ka-PEER Yu organization or the Guidance and Counseling Office sa iyong campus ngayon din.",
    },
    "tl": {
        "standard": "Naririnig kita, at nag-aalala ako sa iyo. Totoo ang nararamdaman mo. Nandito ako para makinig. Kapag handa ka, pwede mong kausapin ang Ka-PEER Yu organization o ang Guidance and Counseling Office sa iyong campus.",
        "plan": "Nag-aalala talaga ako sa iyo ngayon. Ang kaligtasan mo ang pinaka-importante. Nandito ako para makinig. Para sa mas malalim na tulong, kailangang makausap mo ang Ka-PEER Yu organization o ang Guidance and Counseling Office sa iyong campus ngayon din.",
        "high_risk": "Ramdam ko ang bigat ng iyong pinagdadaanan, at nandito ako. Ang kaligtasan mo ang pinaka-importante. Nandito ako para makinig. Pwede mong kausapin ang Ka-PEER Yu organization o ang Guidance and Counseling Office sa iyong campus ngayon din.",
    },
    "taglish": {
        "standard": "I hear you, at nag-aalala ako sa iyo. Your feelings are valid. Nandito ako para makinig. Kapag ready ka na, you can talk to Ka-PEER Yu or the Guidance Office sa iyong campus.",
        "plan": "I'm really worried about you right now. Pinaka-importante ang safety mo. Nandito ako para makinig. For deeper support, please reach out sa Ka-PEER Yu organization or the Guidance and Counseling Office on your campus right now.",
        "high_risk": "I can feel your pain, and I'm here. Safety is the most important thing. Nandito ako para makinig. You can talk to Ka-PEER Yu or the Guidance Office sa iyong campus ngayon din.",
    }
}

ESCALATION_BUMP = {
    "en": " It might help to speak with the Ka-PEER Yu organization or the Guidance Office on your campus — they're ready to support you.",
    "tl": " Maaaring makatulong ang pakikipag-usap sa Ka-PEER Yu o sa Guidance Office ng inyong campus — handa silang suportahan ka.",
    "taglish": " It might help if you talk to Ka-PEER Yu or the Guidance Office sa campus niyo — they are there to support you.",
}

ANTI_DEPENDENCE = {
    "en": "I'm glad you trust me. And because I care, I also want to encourage you to connect with people who can help you in person, like Ka-PEER Yu or your campus Guidance Office.",
    "tl": "Natutuwa ako sa tiwala mo. Dahil mahalaga ka, gusto rin kitang i-encourage na lumapit sa Ka-PEER Yu o sa Guidance Office ng inyong campus para sa dagdag na suporta.",
    "taglish": "I'm glad you trust me. Because I care about you, I want to encourage you to connect with Ka-PEER Yu or your campus Guidance Office too.",
}

TRANSPARENCY = {
    "en": "I'm your MindGuard AI companion, here to listen. ",
    "tl": "Ako ang iyong MindGuard AI companion, nandito para makinig. ",
    "taglish": "I'm your MindGuard AI companion, nandito para makinig. ",
}


# =============================================================================
# STEP 10 — CONTEXT-AWARE RESPONSE GENERATOR
# =============================================================================
def pick_fragment(pool: list, used: set) -> str:
    """Pick a fragment not yet used, or reset if all used."""
    available = [f for f in pool if f not in used]
    if not available:
        available = pool
    choice = random.choice(available)
    used.add(choice)
    return choice

def pick_followup(intent: str, lang_key: str, used_followups: set) -> str:
    """Pick a context-appropriate follow-up question."""
    pool = FOLLOW_UP_QUESTIONS.get(intent, FOLLOW_UP_QUESTIONS.get("general_chat", {}))
    questions = pool.get(lang_key, pool.get("en", ["Would you like to tell me more?"]))
    available = [q for q in questions if q not in used_followups]
    if not available:
        available = questions
    choice = random.choice(available)
    used_followups.add(choice)
    return choice

def generate_response(
    intent: str,
    confidence: float,
    intensity: str,
    lang: str,
    escalation: dict,
    session_id: str,
    is_first_turn: bool,
    emotion_trend: str = "stable",
    semantic_emotion: str = None,
) -> dict:
    used = get_used_responses(session_id)
    used_followups = _sessions[session_id]["used_followups"]
    lang_key = lang if lang in ["en", "tl", "taglish"] else "tl"
    prefix = TRANSPARENCY[lang_key] if is_first_turn else ""
    turn = _sessions[session_id]["turn"]

    # 1. Validation
    val = pick_fragment(DYNAMIC_FRAGMENTS["validation"][lang_key], used)

    # 2. Supportive Presence
    pres = DYNAMIC_FRAGMENTS["presence"][lang_key]

    # 3. Reflection
    intent_pool = DYNAMIC_FRAGMENTS["reflection"].get(intent, DYNAMIC_FRAGMENTS["reflection"]["other"])[lang_key]
    ref = pick_fragment(intent_pool, used)

    # 4. Context-aware follow-up question
    followup = pick_followup(intent, lang_key, used_followups)

    # 5. Coping suggestion
    sug = pick_fragment(DYNAMIC_FRAGMENTS["suggestion"][lang_key], used)
    cls = pick_fragment(DYNAMIC_FRAGMENTS["closing"][lang_key], used)

    # Assemble based on intensity AND turn count for variety
    if intensity == "high":
        grounding = random.choice(GROUNDING_TECHNIQUES.get(lang_key, GROUNDING_TECHNIQUES["tl"]))
        if turn <= 1:
            final_text = f"{prefix}{val} {ref} {grounding} {pres}"
        else:
            final_text = f"{prefix}{val} {ref} {grounding} {followup}"
        action = "high_distress_grounding"
    elif confidence < 0.55:
        # Low confidence: ask for clarification
        clarifier = " Can you tell me a bit more about what's on your mind?" if lang_key == "en" else " Maaari mo bang ikwento pa ang nasa isip mo?"
        final_text = f"{prefix}{val} {pres}{clarifier}"
        action = "clarification"
    elif turn <= 1:
        # First couple turns: validate + reflect + gentle explore
        final_text = f"{prefix}{val} {ref} {pres} {followup}"
        action = intent
    elif turn <= 4:
        # Mid-conversation: validate + reflect + suggestion
        final_text = f"{prefix}{val} {ref} {sug} {cls}"
        action = intent
    else:
        # Deeper conversation: vary structure to avoid pattern fatigue
        structures = [
            f"{prefix}{ref} {sug} {followup}",
            f"{prefix}{val} {followup} {cls}",
            f"{prefix}{ref} {pres} {sug}",
            f"{prefix}{val} {ref} {cls}",
        ]
        final_text = random.choice(structures)
        action = intent

    # Add escalation bump if needed
    if escalation["escalate"]:
        final_text += ESCALATION_BUMP[lang_key]

    # Add declining trend warning
    if emotion_trend == "declining" and not escalation["escalate"]:
        trend_msg = {
            "en": " I've noticed you've been going through a tough stretch. You don't have to carry this alone.",
            "tl": " Napansin ko na patuloy mong dinadala ang mabibigat na bagay. Hindi mo kailangang mag-isa sa labang ito.",
            "taglish": " I've noticed na medyo mahirap ang pinagdadaanan mo lately. Hindi mo kailangang i-carry ito alone.",
        }
        final_text += trend_msg.get(lang_key, trend_msg["en"])

    # Anti-repetition check
    max_attempts = 3
    attempt = 0
    while is_response_repeated(session_id, final_text) and attempt < max_attempts:
        # Regenerate with different fragments
        val = pick_fragment(DYNAMIC_FRAGMENTS["validation"][lang_key], used)
        ref = pick_fragment(intent_pool, used)
        sug = pick_fragment(DYNAMIC_FRAGMENTS["suggestion"][lang_key], used)
        final_text = f"{prefix}{val} {ref} {sug} {cls}"
        attempt += 1

    # Ensure length < 100 words
    words = final_text.split()
    if len(words) > 95:
        final_text = " ".join(words[:95]) + "..."

    return {
        "response": final_text,
        "action": action,
    }


# =============================================================================
# MAIN ENGINE — ORCHESTRATOR (Hybrid ML + Semantic + DL)
# =============================================================================
class MentalHealthEngine:
    def __init__(self):
        logger.info("Initializing MindGuard Hybrid ML System V11 (Scikit + TF + Semantic)...")
        self._initialize_models()

    def _initialize_models(self):
        # --- 1. Vectorization (TF-IDF) & 2. Intent Classification (SVM) ---
        self.vectorizer = TfidfVectorizer(max_features=5000)

        intent_texts = [t[0] for t in TRAINING_DATA]
        intent_labels = [t[1] for t in TRAINING_DATA]

        X_tfidf = self.vectorizer.fit_transform(intent_texts)

        self.intent_classifier = LinearSVC(C=1.0, dual="auto")
        self.intent_classifier.fit(X_tfidf, intent_labels)

        # --- 3. Mood / Sentiment Detection (Logistic Regression) ---
        mood_map = {
            "academic_stress": "Stressed", "relationship_issues": "Sad",
            "family_conflict": "Angry", "financial_stress": "Stressed", "loneliness": "Sad",
            "burnout": "Stressed", "general_anxiety": "Anxious", "depression_grief": "Sad",
            "self_esteem": "Insecure", "career_anxiety": "Anxious", "bullying": "Sad",
            "health_anxiety": "Anxious", "general_chat": "Okay", "seeking_support": "Okay",
        }
        mood_labels = [mood_map.get(l, "Okay") for l in intent_labels]
        self.mood_classifier = LogisticRegression(max_iter=1000)
        self.mood_classifier.fit(X_tfidf, mood_labels)

        # --- 4. Risk Detection Model (Binary) ---
        risk_labels = [1 if "crisis" in l.lower() or l in ["depression_grief"] else 0 for l in intent_labels]
        self.risk_classifier = LogisticRegression(max_iter=1000)
        self.risk_classifier.fit(X_tfidf, risk_labels)

        # --- 5. Unsupervised Learning (KMeans Clustering) ---
        self.clustering_model = KMeans(n_clusters=6, random_state=42, n_init='auto')
        self.clustering_model.fit(X_tfidf)

        # --- 6. Semi-Supervised Learning (Self-Training) ---
        base_lr = LogisticRegression(max_iter=1000)
        self.semi_supervised = SelfTrainingClassifier(base_lr, threshold=0.8)
        try:
            self.semi_supervised.fit(X_tfidf, intent_labels)
        except Exception:
            pass

        # --- 7. Neural Network (LSTM Severity Analyzer) ---
        logger.info("Initializing TensorFlow Neural Context Network...")
        self.tokenizer = Tokenizer(num_words=5000)
        self.tokenizer.fit_on_texts(intent_texts)
        self.max_len = 20

        X_seq = self.tokenizer.texts_to_sequences(intent_texts)
        X_pad = pad_sequences(X_seq, maxlen=self.max_len)

        severity_map = {
            "academic_stress": 0.5, "depression_grief": 0.8, "bullying": 0.7,
            "self_esteem": 0.6, "burnout": 0.6, "loneliness": 0.5,
            "general_anxiety": 0.5, "health_anxiety": 0.5,
            "relationship_issues": 0.5, "family_conflict": 0.5,
            "financial_stress": 0.5, "career_anxiety": 0.4,
            "general_chat": 0.1, "seeking_support": 0.3,
        }
        y_lstm = np.array([severity_map.get(l, 0.4) for l in intent_labels])

        self.lstm_model = Sequential([
            Embedding(input_dim=5000, output_dim=32, input_length=self.max_len),
            LSTM(32, return_sequences=False),
            Dense(16, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        self.lstm_model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        self.lstm_model.fit(X_pad, y_lstm, epochs=3, verbose=0)
        logger.info("Hybrid ML Architecture (Scikit + LSTM + Semantic) Loaded Successfully!")

    def process(self, req: ChatRequest, db: Session) -> dict:
        text = req.message
        lang = lang_det.detect(text)
        lang_key = lang
        is_first_turn = req.turn == 0

        # ── Semantic Understanding ──────────────────────────────────────
        text_embedding = encode_text(text)
        semantic_intent_result = get_semantic_intent(text)
        emotion_match = get_emotion_match(text, top_k=3)
        semantic_risk = get_semantic_risk_score(text)

        # Store in session memory
        add_message_to_session(req.session_id, text, text_embedding)
        if emotion_match:
            top_emotion = emotion_match[0]
            add_emotion_to_trajectory(req.session_id, top_emotion["emotion"], top_emotion["risk_level"])
        emotion_trend = get_emotional_trend(req.session_id)

        # ── Database: Get or Create Session ─────────────────────────────
        db_session = db.query(models.ChatSession).filter(
            models.ChatSession.session_id == req.session_id
        ).first()
        if not db_session:
            db_session = models.ChatSession(
                session_id=req.session_id,
                latest_mood=req.mood or "Okay",
                total_turns=0,
                highest_risk_level=0
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)

        # Log User Message
        user_msg = models.MessageLog(
            session_id=db_session.session_id, sender="user", text=text
        )
        db.add(user_msg)

        # ── ML Pipeline ─────────────────────────────────────────────────
        vec_input = self.vectorizer.transform([text])
        ml_intent = self.intent_classifier.predict(vec_input)[0]
        ml_confidence = 0.85

        # Use TF-IDF + LogReg for confidence score
        tfidf_intent, tfidf_confidence = classify_intent(text)

        ml_mood = self.mood_classifier.predict(vec_input)[0]
        ml_risk_flag = self.risk_classifier.predict(vec_input)[0] == 1

        # LSTM Severity
        seq = self.tokenizer.texts_to_sequences([text])
        pad_seq = pad_sequences(seq, maxlen=self.max_len)
        lstm_score = float(self.lstm_model.predict(pad_seq, verbose=0)[0][0])

        # ── HYBRID INTENT FUSION ────────────────────────────────────────
        # Combine ML intent + Semantic intent for better accuracy
        semantic_intent = semantic_intent_result["intent"]
        semantic_conf = semantic_intent_result["confidence"]

        if tfidf_confidence >= 0.7 and semantic_conf >= 0.5:
            # Both agree or ML is highly confident → use ML
            fused_intent = tfidf_intent if tfidf_confidence > semantic_conf else semantic_intent
            fused_confidence = max(tfidf_confidence, semantic_conf)
        elif semantic_conf > tfidf_confidence:
            fused_intent = semantic_intent
            fused_confidence = semantic_conf
        else:
            fused_intent = tfidf_intent
            fused_confidence = tfidf_confidence

        # ── RISK FUSION SCORE ───────────────────────────────────────────
        # Combine: Rule Score + ML Score + DL Score + Semantic Score
        rule_crisis = crisis_detection(text)
        rule_score = 3 if rule_crisis else 0

        ml_risk_score = 1.0 if ml_risk_flag else 0.0
        dl_risk_score = lstm_score
        sem_risk_score = semantic_risk["score"]

        # Fused risk level
        if rule_crisis or (sem_risk_score > 0.6 and ml_risk_flag):
            fused_risk_level = 3
        else:
            weighted_risk = (
                rule_score * 0.4 +
                ml_risk_score * 3 * 0.2 +
                dl_risk_score * 3 * 0.15 +
                sem_risk_score * 3 * 0.25
            )
            if weighted_risk >= 2.5:
                fused_risk_level = 3
            elif weighted_risk >= 1.5:
                fused_risk_level = 2
            elif weighted_risk >= 0.5:
                fused_risk_level = 1
            else:
                fused_risk_level = 0

        # ── Log AI Decision (Responsible AI) ────────────────────────────
        ai_log = models.AIDecisionLog(
            session_id=req.session_id,
            user_message_hash=hashlib.md5(text.encode()).hexdigest()[:12],
            ml_intent=tfidf_intent,
            ml_confidence=tfidf_confidence,
            semantic_intent=semantic_intent,
            semantic_confidence=semantic_conf,
            fused_intent=fused_intent,
            emotion_detected=emotion_match[0]["emotion"] if emotion_match else None,
            risk_rule_score=rule_score,
            risk_ml_score=ml_risk_score,
            risk_semantic_score=sem_risk_score,
            risk_dl_score=dl_risk_score,
            final_risk_level=fused_risk_level,
            action_taken=None,
        )

        # ── CRISIS OVERRIDE ────────────────────────────────────────────
        if fused_risk_level >= 3:
            level = rule_crisis["level"] if rule_crisis else "CRISIS"
            logger.critical(f"⚠️ CRISIS [{level}] | Session: {req.session_id}")

            if level == "CRISIS_PLAN":
                response_type = "plan"
            elif lstm_score > 0.8 or sem_risk_score > 0.7:
                response_type = "high_risk"
            else:
                response_type = "standard"

            reply_text = CRISIS_RESPONSES[lang_key][response_type]

            db_session.highest_risk_level = 3
            db_session.latest_mood = ml_mood
            db_session.action_taken = f"crisis_{response_type}"
            db_session.total_turns += 1

            new_alert = models.AlertLog(
                session_id=db_session.session_id,
                risk_level=3,
                action_taken=db_session.action_taken,
                latest_mood=db_session.latest_mood
            )
            bot_msg = models.MessageLog(
                session_id=db_session.session_id, sender="bot", text=reply_text
            )

            ai_log.action_taken = f"crisis_{response_type}"
            db.add_all([new_alert, bot_msg, ai_log])
            db.commit()

            return {
                "response": reply_text,
                "action": f"crisis_{response_type}",
                "sentiment": ml_mood,
                "reasoning": {
                    "crisis": True,
                    "level": response_type,
                    "lstm_severity": round(lstm_score, 3),
                    "semantic_risk": round(sem_risk_score, 3),
                    "fused_risk_level": fused_risk_level,
                    "emotion": emotion_match[0]["emotion"] if emotion_match else None,
                    "emotion_trend": emotion_trend,
                },
            }

        # ── Non-crisis processing ──────────────────────────────────────
        cluster_id = int(self.clustering_model.predict(vec_input)[0])
        intensity = emotional_intensity(text)
        escalation = monitor_escalation(req.session_id, fused_intent, intensity)

        # Generate response
        result = generate_response(
            fused_intent, fused_confidence, intensity, lang,
            escalation, req.session_id, is_first_turn,
            emotion_trend=emotion_trend,
            semantic_emotion=emotion_match[0]["emotion"] if emotion_match else None,
        )

        # ── Update DB ──────────────────────────────────────────────────
        db_session.highest_risk_level = max(db_session.highest_risk_level, fused_risk_level)
        db_session.latest_mood = ml_mood
        db_session.action_taken = result["action"]
        db_session.total_turns += 1
        db_session.last_updated = datetime.datetime.utcnow()

        if fused_risk_level >= 2 or escalation["escalate"]:
            new_alert = models.AlertLog(
                session_id=db_session.session_id,
                risk_level=fused_risk_level,
                action_taken=result["action"],
                latest_mood=db_session.latest_mood
            )
            db.add(new_alert)

        bot_msg = models.MessageLog(
            session_id=db_session.session_id, sender="bot", text=result["response"]
        )
        ai_log.action_taken = result["action"]
        db.add_all([bot_msg, ai_log])
        db.commit()

        return {
            "response": result["response"],
            "action": result["action"],
            "sentiment": ml_mood,
            "reasoning": {
                "ml_intent": tfidf_intent,
                "ml_confidence": tfidf_confidence,
                "semantic_intent": semantic_intent,
                "semantic_confidence": semantic_conf,
                "fused_intent": fused_intent,
                "ml_mood": ml_mood,
                "cluster_id": cluster_id,
                "lstm_severity_score": round(lstm_score, 3),
                "semantic_risk_score": round(sem_risk_score, 3),
                "fused_risk_level": fused_risk_level,
                "emotion": emotion_match[0]["emotion"] if emotion_match else None,
                "emotion_trend": emotion_trend,
            },
        }

engine_app = MentalHealthEngine()
ai_service = AIService()


# =============================================================================
# API ENDPOINTS
# =============================================================================
@app.get("/")
def home():
    return {"status": "MindGuard Hybrid Engine V11 (ML + DL + Semantic) Ready"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = engine_app.process(req, db)
        ai_result = ai_service.generate_response(
            AIContext(
                message=req.message,
                history=req.history or [],
                local_response=result["response"],
                sentiment=result.get("sentiment", "neutral"),
                action=result.get("action", "none"),
                reasoning=result.get("reasoning") or {},
                mood=req.mood or "Okay",
            )
        )
        if ai_result.response != result["response"]:
            latest_bot_message = db.query(models.MessageLog).filter(
                models.MessageLog.session_id == req.session_id,
                models.MessageLog.sender == "bot",
            ).order_by(models.MessageLog.id.desc()).first()
            if latest_bot_message:
                latest_bot_message.text = ai_result.response
                db.commit()

        reasoning = result.get("reasoning") or {}
        reasoning["ai_provider"] = ai_result.provider
        reasoning["ai_provider_fallback"] = ai_result.used_fallback
        if ai_result.error:
            reasoning["ai_provider_error"] = ai_result.error

        return ChatResponse(
            response=ai_result.response,
            sentiment=result.get("sentiment", "neutral"),
            action=result.get("action", "none"),
            reasoning=reasoning,
        )
    except Exception as e:
        logger.error(f"Engine error: {str(e)}", exc_info=True)
        return ChatResponse(
            response=(
                "Naririnig kita. Nandito ako para sa iyo."
                if "tl" in lang_det.detect(req.message)
                else "I hear you. I'm here for you."
            ),
            sentiment="neutral",
            action="fallback",
        )


# =============================================================================
# MOOD TRACKING API (Server-side)
# =============================================================================
MOOD_VALUE_MAP = {"Great": 5, "Good": 4, "Okay": 3, "Down": 2, "Crisis": 1}

@app.post("/api/mood/{user_id}")
def log_mood(user_id: int, req: MoodLogRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    mood_log = models.MoodLog(
        user_id=user_id,
        mood=req.mood,
        value=req.value if req.value else MOOD_VALUE_MAP.get(req.mood, 3),
        note=req.note,
    )
    db.add(mood_log)
    db.commit()
    db.refresh(mood_log)
    return {"status": "success", "id": mood_log.id, "mood": mood_log.mood}

@app.get("/api/mood/{user_id}")
def get_moods(user_id: int, days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    moods = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == user_id,
        models.MoodLog.timestamp >= cutoff
    ).order_by(models.MoodLog.timestamp.desc()).all()
    return [
        {"id": m.id, "mood": m.mood, "value": m.value, "note": m.note,
         "timestamp": m.timestamp.isoformat()}
        for m in moods
    ]

@app.delete("/api/mood/{user_id}/{mood_id}")
def delete_mood(user_id: int, mood_id: int, db: Session = Depends(get_db)):
    mood = db.query(models.MoodLog).filter(
        models.MoodLog.id == mood_id, models.MoodLog.user_id == user_id
    ).first()
    if not mood:
        raise HTTPException(status_code=404, detail="Mood log not found")
    db.delete(mood)
    db.commit()
    return {"status": "success"}

@app.get("/api/mood/{user_id}/analytics")
def get_mood_analytics_user(user_id: int, days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    moods = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == user_id,
        models.MoodLog.timestamp >= cutoff
    ).order_by(models.MoodLog.timestamp.asc()).all()

    if not moods:
        return {
            "distribution": {},
            "trend": "stable",
            "average_value": 3.0,
            "total_entries": 0,
            "daily_data": [],
        }

    # Distribution
    distribution = {}
    for m in moods:
        distribution[m.mood] = distribution.get(m.mood, 0) + 1

    # Trend analysis
    values = [m.value for m in moods]
    avg_value = sum(values) / len(values)

    if len(values) >= 4:
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        if avg_second > avg_first + 0.3:
            trend = "improving"
        elif avg_second < avg_first - 0.3:
            trend = "worsening"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Daily data for charts
    daily_data = []
    for m in moods:
        daily_data.append({
            "date": m.timestamp.strftime("%Y-%m-%d"),
            "mood": m.mood,
            "value": m.value,
        })

    # Risk indicators
    risk_indicators = []
    low_moods = [m for m in moods if m.value <= 2]
    if len(low_moods) >= 3:
        risk_indicators.append("prolonged_low_mood")
    crisis_moods = [m for m in moods if m.mood == "Crisis"]
    if crisis_moods:
        risk_indicators.append("crisis_detected")

    return {
        "distribution": distribution,
        "trend": trend,
        "average_value": round(avg_value, 2),
        "total_entries": len(moods),
        "daily_data": daily_data,
        "risk_indicators": risk_indicators,
    }


# =============================================================================
# JOURNAL API (Server-side with AI Analysis)
# =============================================================================
@app.post("/api/journal/{user_id}")
def save_journal_entry(user_id: int, req: JournalEntryRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # AI Analysis of journal text
    themes_result = analyze_text_themes([req.text])
    themes_json = json.dumps([t[0] for t in themes_result.get("themes", [])[:3]])
    risk_json = json.dumps(themes_result.get("risk_indicators", []))

    entry = models.JournalEntry(
        user_id=user_id,
        text=req.text,
        mood=req.mood,
        themes_json=themes_json,
        risk_indicators=risk_json,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "status": "success",
        "id": entry.id,
        "themes": json.loads(themes_json),
        "risk_indicators": json.loads(risk_json),
    }

@app.get("/api/journal/{user_id}")
def get_journal_entries(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == user_id
    ).order_by(models.JournalEntry.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "text": e.text,
            "mood": e.mood,
            "themes": json.loads(e.themes_json) if e.themes_json else [],
            "risk_indicators": json.loads(e.risk_indicators) if e.risk_indicators else [],
            "date": e.timestamp.isoformat(),
        }
        for e in entries
    ]

@app.delete("/api/journal/{user_id}/{entry_id}")
def delete_journal_entry(user_id: int, entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.JournalEntry).filter(
        models.JournalEntry.id == entry_id, models.JournalEntry.user_id == user_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
    return {"status": "success"}

@app.get("/api/journal/{user_id}/reflection")
def get_weekly_reflection(user_id: int, db: Session = Depends(get_db)):
    """AI-generated weekly reflection based on journal entries."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == user_id,
        models.JournalEntry.timestamp >= cutoff
    ).all()

    if not entries:
        return {
            "has_reflection": False,
            "summary": "No journal entries this week. Writing even a single line can be a powerful step.",
            "themes": [],
            "recommendation": "Try journaling today — even one sentence about how you're feeling.",
        }

    texts = [e.text for e in entries if e.text]
    if not texts:
        return {
            "has_reflection": False,
            "summary": "Your entries this week didn't contain enough text for analysis.",
            "themes": [],
            "recommendation": "Try writing a bit more about your feelings next time.",
        }

    analysis = analyze_text_themes(texts)
    dominant_themes = [t[0] for t in analysis.get("themes", [])[:3]]
    risk_indicators = analysis.get("risk_indicators", [])
    dominant_emotions = analysis.get("dominant_emotions", [])[:3]

    # Generate human-readable summary
    theme_labels = {
        "academic_stress": "academic pressure",
        "relationship_issues": "relationship concerns",
        "family_conflict": "family tension",
        "financial_stress": "financial worries",
        "loneliness": "feelings of isolation",
        "burnout": "exhaustion and burnout",
        "general_anxiety": "anxiety and worry",
        "depression_grief": "sadness and grief",
        "self_esteem": "self-image challenges",
        "career_anxiety": "career uncertainty",
        "bullying": "social conflict",
        "health_anxiety": "health concerns",
        "general_chat": "general reflection",
        "seeking_support": "seeking help and support",
    }

    readable_themes = [theme_labels.get(t, t) for t in dominant_themes]
    if readable_themes:
        themes_text = ", ".join(readable_themes[:-1])
        if len(readable_themes) > 1:
            themes_text += f" and {readable_themes[-1]}"
        else:
            themes_text = readable_themes[0]
        summary = f"This week, your entries frequently touched on {themes_text}."
    else:
        summary = "This week, you wrote reflectively about various topics."

    # Gentle recommendation
    recommendations = {
        "academic_stress": "Consider breaking tasks into smaller steps and celebrating small wins. You don't have to solve everything at once.",
        "loneliness": "Reaching out to even one person — a classmate, a counselor, or a friend — can make a difference.",
        "burnout": "Your body is telling you something important. Try to build in small rest breaks, even 5 minutes.",
        "general_anxiety": "Breathing exercises and grounding techniques can help when worry feels overwhelming.",
        "depression_grief": "If the heaviness persists, talking to a professional counselor can provide real relief.",
        "self_esteem": "Try listing one thing you did well today, no matter how small. You deserve your own kindness.",
        "relationship_issues": "Giving yourself space to heal is not selfish — it's necessary.",
        "family_conflict": "Remember, you can't control others' actions, but you can protect your peace.",
    }
    recommendation = recommendations.get(
        dominant_themes[0] if dominant_themes else "",
        "Keep journaling — reflecting on your feelings is a powerful form of self-care."
    )

    return {
        "has_reflection": True,
        "summary": summary,
        "themes": dominant_themes,
        "dominant_emotions": [e["emotion"] for e in dominant_emotions],
        "risk_indicators": risk_indicators,
        "recommendation": recommendation,
        "entries_count": len(entries),
    }


# =============================================================================
# DAILY AFFIRMATION API
# =============================================================================
AFFIRMATION_POOL = {
    "general": [
        "You are capable of amazing things — take it one step at a time.",
        "Your feelings are valid, and it's okay to ask for help when you need it.",
        "You have overcome challenges before, and you can do it again.",
        "You are worthy of love and kindness, starting with yourself.",
        "Progress, not perfection — celebrate your small wins today.",
        "You are stronger than your struggles; keep going.",
        "It's okay to rest and recharge; self-care is a strength.",
        "You bring unique value to the world — believe in your potential.",
        "Tough days don't last, but tough people like you do.",
        "You deserve peace and happiness.",
        "Every step forward is a victory, no matter how small.",
        "You are not defined by your mistakes.",
        "Your journey is unique, and that's what makes you special.",
        "Breathe deeply; this moment is temporary, and better days are coming.",
        "You have the power to create positive change in your life.",
        "You are enough, just as you are right now.",
        "Your resilience inspires those around you.",
        "Focus on what you can control, and let go of the rest.",
        "You are a work in progress, and that's perfectly okay.",
        "Take pride in how far you've come.",
    ],
    "stressed": [
        "You do not have to solve everything today.",
        "One thing at a time — that's all anyone can ask.",
        "Pressure does not define your value. You're doing enough.",
        "Even mountains are climbed one step at a time.",
        "It's okay to pause. Rest is productive, too.",
    ],
    "sad": [
        "Small steps forward are still progress.",
        "Even on your hardest days, you are still worthy of love.",
        "The sun will rise again, even after the longest night.",
        "Your sadness is valid. You don't have to smile through the pain.",
        "Healing is not linear, and every day is a new chance.",
    ],
    "anxious": [
        "You are safe in this moment. Breathe.",
        "Worry is a feeling, not a fact. You are okay.",
        "You have survived every anxious moment so far.",
        "One breath at a time — you've got this.",
        "The future isn't written yet. You have the power to shape it.",
    ],
}

@app.get("/api/affirmation/daily")
def get_daily_affirmation(mood: Optional[str] = None, db: Session = Depends(get_db)):
    """Return today's affirmation, mood-aware and non-repeating within 30 days."""
    today = datetime.datetime.utcnow().date()

    # Check if we already have today's affirmation
    existing = db.query(models.DailyAffirmationHistory).filter(
        func.date(models.DailyAffirmationHistory.shown_date) == today
    ).first()
    if existing:
        return {"affirmation": existing.affirmation_text, "mood_category": existing.mood_category}

    # Get recent 30 days' affirmations to avoid repetition
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    recent = db.query(models.DailyAffirmationHistory).filter(
        models.DailyAffirmationHistory.shown_date >= cutoff
    ).all()
    recent_texts = {r.affirmation_text for r in recent}

    # Select pool based on mood
    mood_lower = (mood or "general").lower()
    pool = AFFIRMATION_POOL.get(mood_lower, AFFIRMATION_POOL["general"])
    # Also include general pool for variety
    combined_pool = list(set(pool + AFFIRMATION_POOL["general"]))

    available = [a for a in combined_pool if a not in recent_texts]
    if not available:
        available = combined_pool  # Reset if all used

    selected = random.choice(available)

    # Save to history
    history_entry = models.DailyAffirmationHistory(
        affirmation_text=selected,
        mood_category=mood_lower,
        shown_date=datetime.datetime.utcnow(),
    )
    db.add(history_entry)
    db.commit()

    return {"affirmation": selected, "mood_category": mood_lower}


# =============================================================================
# ADMIN DASHBOARD ENDPOINTS (SQLITE BACKED)
# =============================================================================
@app.get("/api/admin/students")
def get_admin_students(db: Session = Depends(get_db)):
    sessions = db.query(models.ChatSession).order_by(models.ChatSession.last_updated.desc()).all()
    return [
        {
            "session_id": s.session_id,
            "user_id": s.user_id,
            "user_email": s.user.email if s.user else "Anonymous",
            "student_id": s.user.student_id if s.user else "N/A",
            "fullname": s.user.fullname if s.user else "N/A",
            "course": s.user.program if s.user else "N/A",
            "latest_mood": s.latest_mood,
            "highest_risk_level": s.highest_risk_level,
            "total_turns": s.total_turns,
            "action_taken": s.action_taken or "none",
            "last_interaction": s.last_updated.isoformat() if s.last_updated else "N/A",
        }
        for s in sessions
    ]


# ── PROFILE / PASSWORD MANAGEMENT ──────────────────────────────────────────
@app.put("/api/profile/{user_id}")
def update_profile(user_id: int, req: UpdateProfileRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.fullname = req.fullname
    user.email = req.email
    user.trusted_contacts = json.dumps(req.trusted_contacts) if req.trusted_contacts else None
    db.commit()
    db.refresh(user)
    return {"status": "success", "message": "Profile updated successfully"}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    user_payload = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "fullname": user.fullname,
        "student_id": user.student_id,
        "program": user.program,
        "is_primary_admin": user.is_primary_admin,
        "trusted_contacts": json.loads(user.trusted_contacts) if user.trusted_contacts else []
    }
    return {"status": "success", "message": f"Welcome back, {user.email}", "user": user_payload}

@app.post("/api/signup")
def signup(req: CreateStudentRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        email=req.email,
        password_hash=hash_password(req.password),
        fullname=req.fullname,
        student_id=req.student_id,
        program=req.program,
        role="student"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    user_payload = {
        "id": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "fullname": new_user.fullname,
        "student_id": new_user.student_id,
        "program": new_user.program,
        "is_primary_admin": new_user.is_primary_admin,
        "trusted_contacts": []
    }
    return {"status": "success", "message": "Sign up successful", "user": user_payload}

@app.put("/api/profile/password/{user_id}")
def update_password(user_id: int, req: UpdatePasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully"}


# ── ADMIN CRUD: MANAGE STUDENTS ───────────────────────────────────────────
@app.post("/api/admin/students")
def create_student(req: CreateStudentRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_student = models.User(
        email=req.email,
        password_hash=hash_password(req.password),
        fullname=req.fullname,
        student_id=req.student_id,
        program=req.program,
        role="student"
    )
    db.add(new_student)
    db.commit()
    return {"status": "success", "message": "Student created successfully"}

@app.put("/api/admin/students/{user_id}")
def update_student(user_id: int, req: UpdateStudentRequest, db: Session = Depends(get_db)):
    student = db.query(models.User).filter(models.User.id == user_id, models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.fullname = req.fullname
    student.email = req.email
    student.program = req.program
    db.commit()
    return {"status": "success", "message": "Student updated successfully"}

@app.delete("/api/admin/students/{user_id}")
def delete_student(user_id: int, db: Session = Depends(get_db)):
    student = db.query(models.User).filter(models.User.id == user_id, models.User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"status": "success", "message": "Student deleted successfully"}


# ── ADMIN CRUD: MANAGE ADMINS ─────────────────────────────────────────────
@app.get("/api/admin/admins")
def get_admins(db: Session = Depends(get_db)):
    admins = db.query(models.User).filter(models.User.role == "admin").all()
    return [
        {
            "id": a.id,
            "fullname": a.fullname,
            "email": a.email,
            "role_title": a.program,
            "is_primary": a.is_primary_admin
        }
        for a in admins
    ]

@app.post("/api/admin/admins")
def create_admin(req: CreateAdminRequest, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can create new administrators.")
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_admin = models.User(
        email=req.email,
        password_hash=hash_password(req.password),
        fullname=req.fullname,
        program=req.role,
        role="admin",
        is_primary_admin=False
    )
    db.add(new_admin)
    audit = models.AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="CREATED_ADMIN",
        target_email=req.email
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": f"Admin {req.email} successfully created."}

@app.put("/api/admin/admins/{user_id}")
def update_admin(user_id: int, req: UpdateAdminRequest, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can edit other administrators.")
    admin = db.query(models.User).filter(models.User.id == user_id, models.User.role == "admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    admin.fullname = req.fullname
    admin.email = req.email
    admin.program = req.role
    db.commit()
    return {"status": "success"}

@app.delete("/api/admin/admins/{user_id}")
def delete_admin(user_id: int, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can delete administrators.")
    admin = db.query(models.User).filter(models.User.id == user_id, models.User.role == "admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if admin.is_primary_admin:
        raise HTTPException(status_code=400, detail="Cannot delete the Primary Admin.")
    db.delete(admin)
    audit = models.AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="DELETED_ADMIN",
        target_email=admin.email
    )
    db.add(audit)
    db.commit()
    return {"status": "success"}


# ── DASHBOARD ANALYTICS ──────────────────────────────────────────────────
@app.get("/api/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    active = db.query(models.ChatSession).count()
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_convos = db.query(models.MessageLog).filter(models.MessageLog.timestamp >= today_start).count()
    crisis_alerts = db.query(models.AlertLog).filter(models.AlertLog.is_reviewed == False).count()
    students_at_risk = db.query(models.ChatSession).filter(models.ChatSession.highest_risk_level >= 2).count()
    return {
        "total_active_students": active,
        "conversations_today": today_convos,
        "crisis_alerts": crisis_alerts,
        "students_at_risk": students_at_risk
    }

@app.get("/api/admin/mood-analytics")
def get_mood_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = Depends(get_db)):
    sessions = db.query(models.ChatSession).all()
    moods = {"Happy": 0, "Okay": 0, "Stressed": 0, "Sad": 0, "Crisis": 0, "Anxious": 0, "Angry": 0, "Insecure": 0}
    for s in sessions:
        m = s.latest_mood.capitalize() if s.latest_mood else "Okay"
        if m in moods:
            moods[m] += s.total_turns
        elif s.highest_risk_level == 3:
            moods["Crisis"] += s.total_turns
        else:
            moods["Okay"] += s.total_turns
    return moods

@app.get("/api/admin/risk-analytics")
def get_risk_analytics(db: Session = Depends(get_db)):
    sessions = db.query(models.ChatSession).all()
    risks = {"level_0": 0, "level_1": 0, "level_2": 0, "level_3": 0}
    for s in sessions:
        lvl = s.highest_risk_level
        if lvl in [0, 1, 2, 3]:
            risks[f"level_{lvl}"] += 1
    return risks

@app.get("/api/admin/risk-trends")
def get_risk_trends(days: int = 14, db: Session = Depends(get_db)):
    """Time-series risk data for charts."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    alerts = db.query(models.AlertLog).filter(
        models.AlertLog.timestamp >= cutoff
    ).order_by(models.AlertLog.timestamp.asc()).all()

    daily_risks = defaultdict(lambda: {"level_0": 0, "level_1": 0, "level_2": 0, "level_3": 0})
    for a in alerts:
        day = a.timestamp.strftime("%Y-%m-%d")
        lvl = a.risk_level
        if lvl in [0, 1, 2, 3]:
            daily_risks[day][f"level_{lvl}"] += 1

    return [{"date": d, **counts} for d, counts in sorted(daily_risks.items())]

@app.get("/api/admin/alerts")
def get_admin_alerts(db: Session = Depends(get_db)):
    alerts = db.query(models.AlertLog).order_by(models.AlertLog.timestamp.desc()).all()
    return [
        {
            "id": a.id,
            "session_id": a.session_id,
            "risk_level": a.risk_level,
            "mood": a.latest_mood or "Unknown",
            "action": a.action_taken,
            "timestamp": a.timestamp.isoformat(),
            "is_reviewed": a.is_reviewed
        }
        for a in alerts
    ]

@app.put("/api/admin/alerts/{alert_id}/review")
def review_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(models.AlertLog).filter(models.AlertLog.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_reviewed = True
    db.commit()
    return {"status": "success"}

@app.get("/api/admin/behavioral-clusters")
def get_behavioral_clusters(db: Session = Depends(get_db)):
    """Return unsupervised clustering insights for staff dashboard."""
    sessions = db.query(models.ChatSession).all()
    if not sessions:
        return {"clusters": []}

    cluster_a = {"label": "Low Risk / Positive", "count": 0, "description": "Positive mood, low risk, regular usage"}
    cluster_b = {"label": "Moderate Risk / Active", "count": 0, "description": "Moderate stress, frequent interaction, some risk"}
    cluster_c = {"label": "High Risk / Withdrawal", "count": 0, "description": "Negative mood trend, reduced interaction, high risk"}

    for s in sessions:
        if s.highest_risk_level <= 0:
            cluster_a["count"] += 1
        elif s.highest_risk_level <= 2:
            cluster_b["count"] += 1
        else:
            cluster_c["count"] += 1

    return {"clusters": [cluster_a, cluster_b, cluster_c]}


# ── STAFF MANAGEMENT ─────────────────────────────────────────────────────
@app.get("/api/admin/staff")
def get_staff(db: Session = Depends(get_db)):
    staff = db.query(models.User).filter(models.User.role == "staff").all()
    return [
        {
            "id": s.id,
            "fullname": s.fullname,
            "email": s.email,
            "role_title": s.program or "Staff",
            "is_primary": s.is_primary_admin
        }
        for s in staff
    ]

@app.post("/api/admin/staff")
def create_staff(req: CreateStaffRequest, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or requester.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create staff accounts.")
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_staff = models.User(
        email=req.email,
        password_hash=hash_password(req.password),
        fullname=req.fullname,
        program=req.role,
        role="staff",
        is_primary_admin=False
    )
    db.add(new_staff)
    audit = models.AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="CREATED_STAFF",
        target_email=req.email
    )
    db.add(audit)
    db.commit()
    return {"status": "success", "message": f"Staff {req.email} created successfully."}

@app.put("/api/admin/staff/{user_id}")
def update_staff(user_id: int, req: UpdateStaffRequest, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or requester.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can edit staff accounts.")
    staff = db.query(models.User).filter(models.User.id == user_id, models.User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    staff.fullname = req.fullname
    staff.email = req.email
    staff.program = req.role
    audit = models.AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="UPDATED_STAFF",
        target_email=req.email
    )
    db.add(audit)
    db.commit()
    return {"status": "success"}

@app.delete("/api/admin/staff/{user_id}")
def delete_staff(user_id: int, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(models.User).filter(models.User.email == requester_email).first()
    if not requester or requester.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete staff accounts.")
    staff = db.query(models.User).filter(models.User.id == user_id, models.User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    audit = models.AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="DELETED_STAFF",
        target_email=staff.email
    )
    db.add(audit)
    db.delete(staff)
    db.commit()
    return {"status": "success"}


# ── SAVED AFFIRMATIONS ──────────────────────────────────────────────────
@app.get("/api/affirmations/{user_id}")
def get_saved_affirmations(user_id: int, db: Session = Depends(get_db)):
    affirmations = db.query(models.SavedAffirmation).filter(
        models.SavedAffirmation.user_id == user_id
    ).order_by(models.SavedAffirmation.created_at.desc()).all()
    return [{"id": a.id, "text": a.text, "created_at": a.created_at.isoformat()} for a in affirmations]

@app.post("/api/affirmations/{user_id}")
def save_affirmation(user_id: int, req: SaveAffirmationRequest, db: Session = Depends(get_db)):
    existing = db.query(models.SavedAffirmation).filter(
        models.SavedAffirmation.user_id == user_id,
        models.SavedAffirmation.text == req.text
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already saved")
    new_aff = models.SavedAffirmation(user_id=user_id, text=req.text)
    db.add(new_aff)
    db.commit()
    db.refresh(new_aff)
    return {"status": "success", "id": new_aff.id}

@app.delete("/api/affirmations/{user_id}/{affirmation_id}")
def delete_saved_affirmation(user_id: int, affirmation_id: int, db: Session = Depends(get_db)):
    aff = db.query(models.SavedAffirmation).filter(
        models.SavedAffirmation.id == affirmation_id,
        models.SavedAffirmation.user_id == user_id
    ).first()
    if not aff:
        raise HTTPException(status_code=404, detail="Affirmation not found")
    db.delete(aff)
    db.commit()
    return {"status": "success"}

@app.get("/api/affirmations/{user_id}/search")
def search_saved_affirmations(user_id: int, q: str = "", db: Session = Depends(get_db)):
    """Search saved affirmations by text."""
    query = db.query(models.SavedAffirmation).filter(
        models.SavedAffirmation.user_id == user_id
    )
    if q:
        query = query.filter(models.SavedAffirmation.text.contains(q))
    results = query.order_by(models.SavedAffirmation.created_at.desc()).all()
    return [{"id": a.id, "text": a.text, "created_at": a.created_at.isoformat()} for a in results]


# ── SYSTEM AUDIT LOGS ──────────────────────────────────────────────────
@app.get("/api/admin/system-logs")
def get_system_logs(db: Session = Depends(get_db)):
    logs = db.query(models.AdminAuditLog).order_by(models.AdminAuditLog.timestamp.desc()).limit(200).all()
    return [
        {
            "id": l.id,
            "actor": l.actor_admin_email,
            "action": l.action_type,
            "target": l.target_email,
            "timestamp": l.timestamp.isoformat()
        }
        for l in logs
    ]


# ── AI TRANSPARENCY ENDPOINT ──────────────────────────────────────────
@app.get("/api/ai/decisions/{session_id}")
def get_ai_decisions(session_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """Responsible AI: View AI decision log for a session."""
    decisions = db.query(models.AIDecisionLog).filter(
        models.AIDecisionLog.session_id == session_id
    ).order_by(models.AIDecisionLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": d.id,
            "ml_intent": d.ml_intent,
            "ml_confidence": d.ml_confidence,
            "semantic_intent": d.semantic_intent,
            "semantic_confidence": d.semantic_confidence,
            "fused_intent": d.fused_intent,
            "emotion": d.emotion_detected,
            "risk_scores": {
                "rule": d.risk_rule_score,
                "ml": d.risk_ml_score,
                "semantic": d.risk_semantic_score,
                "dl": d.risk_dl_score,
            },
            "final_risk_level": d.final_risk_level,
            "action": d.action_taken,
            "timestamp": d.timestamp.isoformat(),
        }
        for d in decisions
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
