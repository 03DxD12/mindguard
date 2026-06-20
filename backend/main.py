from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from collections import defaultdict, deque
import re
import random
import logging
import json
import os
import datetime
import unicodedata
import numpy as np
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
from collections import defaultdict, deque

# ── Database Imports ───────────────────────────────────────────────────────
from sqlalchemy.orm import Session
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

app = FastAPI(title="MindGuard Hybrid AI Chatbot (ML + Neural Net)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# DATA MODELS
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

# ---- Profile & Auth Schemas ----
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

class LoginRequest(BaseModel): # Added LoginRequest
    email: str
    password: str

    reasoning: Optional[Dict] = None

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
# Catches common misspellings before crisis detection
# =============================================================================
KNOWN_CRISIS_TERMS = [
    "suicide", "kill myself", "magpapakamatay", "overdose",
    "laslas", "end my life", "hurt myself", "wala na akong rason",
    "gusto ko mamatay", "ayoko na mabuhay", "tired of being alive",
    "everyone would be better without me", "i dont want to exist",
]

def fuzzy_preprocess(text: str) -> str:
    """
    Disabled RapidFuzz due to massive false-positive mapping of long strings.
    Returns standard normalized text for Regex checking.
    """
    return normalize_text(text)

# =============================================================================
# STEP 3 — LAYER 1: HARDENED CRISIS DETECTION (HIGHEST PRIORITY)
# =============================================================================
# Direct suicidal intent
DIRECT_SUICIDE = [
    r"\bmagpapakamatay\b", r"\bkill\s+myself\b", r"\bend\s+my\s+life\b",
    r"\bwant\s+to\s+die\b", r"\bgusto\s+ko\s+mamatay\b",
    r"\bayoko\s+na\s+mabuhay\b", r"\bsuicide\b", r"\bpag-alay\s+ng\s+buhay\b",
]
# Self-harm methods/tools
METHOD_REQUEST = [
    r"\boverdose\b", r"\blaslas\b", r"\bhurt\s+myself\b",
    r"\bsaktan\s+sarili\b", r"\bpaano\s+mamatay\b",
    r"\bhow\s+to\s+kill\b", r"\bpills\b.*\bdie\b",
]
# High-risk hopelessness
HOPELESSNESS = [
    r"\bwala\s+na\s+akong\s+rason\b", r"\bno\s+reason\s+to\s+live\b",
    r"\bwala\s+na\b.*\bpag\-asa\b", r"\bno\s+hope\b",
    r"\bmawala\s+na\s+lang\b", r"\bpagod\s+na\s+ako\s+mabuhay\b",
]
# Indirect but high-risk phrases
INDIRECT_HIGH_RISK = [
    r"\beveryone\s+would\s+be\s+better\s+without\s+me\b",
    r"\bi\s+don.?t\s+want\s+to\s+exist\b",
    r"\btired\s+of\s+being\s+alive\b",
    r"\bi\s+can.?t\s+do\s+this\s+anymore\b",
    r"\blahat\s+mas\s+magiging\s+okay\s+kung\s+wala\s+ako\b",
    r"\bit.?s\s+peaceful\s+when\s+everything\s+stops\b",
    r"\bi\s+just\s+want\s+it\s+to\s+stop\b",
]
# Explicit timeline / plan signals → immediate escalation
PLAN_SIGNALS = [
    r"\btonight\b.*\b(die|kill|end)\b",
    r"\btomorrow\b.*\b(last|final|goodbye)\b",
    r"\bna\s+may\s+plano\s+na\s+ako\b",
    r"\bi\s+have\s+a\s+plan\b",
    r"\bna\s+nag\s*-\s*attempt\b",
    r"\btried\s+before\b",
]
# Anti-dependence triggers
DEPENDENCE_PHRASES = [
    r"\byou.?re\s+the\s+only\s+one\s+i\s+have\b",
    r"\bdon.?t\s+leave\s+me\b",
    r"\bi\s+only\s+trust\s+you\b",
    r"\bwala\s+na\s+akong\s+ibang\s+tatanungin\b",
]
# Sarcasm/context reducers — lower false positives
FALSE_POSITIVE_CONTEXT = [
    r"\bexam\b.*\bdie\b", r"\bdie\s+laughing\b",
    r"\bi\s+want\s+to\s+die\s+from\s+(laughter|laughing|embarrassment)\b",
    r"\bkill\s+it\b",  # "kill it on stage"
]

ALL_CRISIS_PATTERNS = DIRECT_SUICIDE + METHOD_REQUEST + HOPELESSNESS + INDIRECT_HIGH_RISK

def crisis_detection(text: str) -> Optional[dict]:
    """
    HARD OVERRIDE. Returns crisis dict immediately if ANY pattern matches.
    Returns None if no crisis detected.
    """
    preprocessed = fuzzy_preprocess(text)

    # Check false positive context first (reduce noise)
    for pat in FALSE_POSITIVE_CONTEXT:
        if re.search(pat, preprocessed, re.IGNORECASE):
            return None  # Context says it's NOT a real crisis

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
    # VADER compound score
    scores = sia.polarity_scores(text)
    compound = scores["compound"]

    # Negative keyword density
    words = normalized.split()
    neg_hits = sum(1 for w in words if w in NEGATIVE_INTENSITY_WORDS)
    neg_density = neg_hits / max(len(words), 1)

    # CAPS ratio (raw text) — screaming / distress indicator
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
# STEP 5 — LAYER 3: SESSION ESCALATION MONITOR
# =============================================================================
# In-memory session store (per session_id)
_sessions: Dict[str, dict] = defaultdict(lambda: {
    "theme_counts": defaultdict(int),
    "distress_history": deque(maxlen=10),
    "used_responses": set(),
    "turn": 0,
})

def monitor_escalation(session_id: str, intent: str, intensity: str) -> dict:
    """Track themes and distress history. Returns escalation flags."""
    session = _sessions[session_id]
    session["theme_counts"][intent] += 1
    session["distress_history"].append(intensity)
    session["turn"] += 1

    theme_repeat = session["theme_counts"][intent] >= 3
    # Detect worsening trend in last 3 turns
    recent = list(session["distress_history"])[-3:]
    intensity_map = {"low": 0, "moderate": 1, "high": 2}
    worsening = (
        len(recent) == 3
        and intensity_map.get(recent[2], 0) > intensity_map.get(recent[0], 0)
    )

    return {
        "theme_repeat": theme_repeat,
        "worsening": worsening,
        "escalate": theme_repeat or worsening,
        "turn": session["turn"],
    }

def get_used_responses(session_id: str) -> set:
    return _sessions[session_id]["used_responses"]

def mark_response_used(session_id: str, response_key: str):
    _sessions[session_id]["used_responses"].add(response_key)

# =============================================================================
# STEP 6 — LAYER 4: ML INTENT CLASSIFIER (Scikit-Learn)
# TF-IDF + Logistic Regression trained on seed data
# =============================================================================
TRAINING_DATA = [
    # academic_stress
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

    # relationship_issues
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

    # family_conflict
    ("My parents fight all the time and I'm scared", "family_conflict"),
    ("Nagagalit lagi ang nanay ko sa akin", "family_conflict"),
    ("I feel like my family doesn't understand me", "family_conflict"),
    ("My dad is very strict and I can't breathe", "family_conflict"),
    ("I feel alone even when I'm at home", "family_conflict"),
    ("Palagi kaming nag-aaway ng tatay ko", "family_conflict"),
    ("My parents are separating and I don't know how to cope", "family_conflict"),
    ("Gulo sa bahay, ayaw ko na umuwi", "family_conflict"),

    # financial_stress
    ("I can't pay my tuition this semester", "financial_stress"),
    ("Wala na kaming pera, baka mag-stop out na ako", "financial_stress"),
    ("I'm worried about money and I can't focus", "financial_stress"),
    ("My scholarship got canceled and I don't know what to do", "financial_stress"),
    ("I have to work part time just to pay for college", "financial_stress"),
    ("Baon sa utang ang pamilya namin", "financial_stress"),
    ("Financial emergency, zero balance", "financial_stress"),

    # loneliness
    ("I feel like I have no real friends", "loneliness"),
    ("Nobody talks to me in class", "loneliness"),
    ("Parang wala akong kaibigan dito sa school", "loneliness"),
    ("I eat alone every day and it hurts", "loneliness"),
    ("I feel invisible to everyone around me", "loneliness"),
    ("I moved to a new city and I don't know anyone", "loneliness"),
    ("Outcast sa classroom, walang kumakausap", "loneliness"),

    # burnout
    ("I'm so tired of everything, I can't keep going", "burnout"),
    ("I've been grinding for months and I feel empty", "burnout"),
    ("Pagod na pagod na ako, wala na akong energy", "burnout"),
    ("I don't feel motivated to do anything anymore", "burnout"),
    ("I used to love studying but now I hate it", "burnout"),
    ("I feel like I'm running on empty", "burnout"),
    ("Burnout na yata ako, drain na drain", "burnout"),

    # general_anxiety
    ("I have panic attacks before class", "general_anxiety"),
    ("I'm always worried even when nothing is wrong", "general_anxiety"),
    ("Palagi akong nag-aalala tungkol sa lahat", "general_anxiety"),
    ("My heart races when I have to present in class", "general_anxiety"),
    ("I can't sleep because I overthink everything", "general_anxiety"),
    ("Anxious about the future", "general_anxiety"),

    # depression_grief
    ("I lost someone I love and I can't move on", "depression_grief"),
    ("Namamatayan ako ng mahal sa buhay", "depression_grief"),
    ("Everything feels dark and hopeless", "depression_grief"),
    ("I haven't left my bed in days", "depression_grief"),
    ("The grief is too heavy, I miss them so much", "depression_grief"),
    ("Walang katapusang lungkot, parang walang liwanag", "depression_grief"),

    # self_esteem
    ("I hate how I look, I feel so ugly", "self_esteem"),
    ("I am not good enough for anything", "self_esteem"),
    ("Mababa ang tingin ko sa sarili ko", "self_esteem"),
    ("Everyone else is smarter and better than me", "self_esteem"),
    ("I feel like a total failure", "self_esteem"),
    ("Insecure ako sa lahat ng kasama ko", "self_esteem"),

    # career_anxiety
    ("I don't know what to do with my life after college", "career_anxiety"),
    ("What if I don't get a job after graduation?", "career_anxiety"),
    ("Takot ako sa future, baka maging tambay lang ako", "career_anxiety"),
    ("Is this the right course for me?", "career_anxiety"),
    ("I feel pressured about my career path", "career_anxiety"),
    ("Hindi ko alam kung anong landas ang tatahakin", "career_anxiety"),

    # bullying
    ("People are spread rumors about me at school", "bullying"),
    ("Binubully ako ng mga kaklase ko", "bullying"),
    ("I'm being harassed online", "bullying"),
    ("Cyberbullying is taking a toll on my mental health", "bullying"),
    ("They make fun of me every day", "bullying"),
    ("Pinagtutulungan nila ako, ayaw ko na pumasok", "bullying"),

    # health_anxiety
    ("I'm constantly worried I have a serious illness", "health_anxiety"),
    ("Takot ako na baka may sakit akong malala", "health_anxiety"),
    ("I keep checking my symptoms online and it scares me", "health_anxiety"),
    ("My health is failing and I'm terrified", "health_anxiety"),
    ("Every little pain makes me think the worst", "health_anxiety"),
    ("Hypochondriac na yata ako sa sobrang kaba sa sakit", "health_anxiety"),

    # general_chat
    ("Hello how are you", "general_chat"),
    ("I just wanted to talk to someone", "general_chat"),
    ("Kumusta ka", "general_chat"),
    ("What can you do", "general_chat"),
    ("I'm okay I just wanted to check in", "general_chat"),
    ("Can we just talk", "general_chat"),

    # seeking_support
    ("I need help, can you guide me?", "seeking_support"),
    ("Tulong po, kailangan ko ng makakausap", "seeking_support"),
    ("I want to seek professional help", "seeking_support"),
    ("Saans ba pwedeng mag-reach out?", "seeking_support"),
    ("Please support me through this", "seeking_support"),
]

X_train = [t[0] for t in TRAINING_DATA]
y_train = [t[1] for t in TRAINING_DATA]

# Refined Pipeline using LinearSVC (SVM) for better high-dimensional text performance
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
# STEP 7 — SEMI-SUPERVISED LOGGING (Backend only, never shown to user)
# =============================================================================
LOG_FILE = os.path.join(os.path.dirname(__file__), "low_confidence_log.jsonl")

def log_low_confidence(text: str, intent: str, confidence: float, intensity: str):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "text_hash": hash(text),  # Anonymized
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
# STEP 9 — RESPONSE TEMPLATE ENGINE
# Intent-specific + intensity-adaptive templates
# =============================================================================
# =============================================================================
# STEP 9 — DYNAMIC RESPONSE ASSEMBLER (FRAGMENT-BASED)
# =============================================================================

DYNAMIC_FRAGMENTS = {
    "validation": {
        "en": [
            "I hear you, and it's completely valid to feel this way.",
            "That sounds like a lot to carry. Thank you for sharing it with me.",
            "I'm listening, and I want you to know your feelings matter.",
            "It takes courage to be this open about what you're going through.",
            "I can sense how much this is weighing on you right now.",
        ],
        "tl": [
            "Naririnig kita, at valid na valid ang nararamdaman mo.",
            "Ang bigat niyan, salamat sa pagbabahagi mo sa akin.",
            "Nakikinig ako, at gusto kong malaman mo na mahalaga ang nararamdaman mo.",
            "Kailangan ng lakas ng loob para maging ganito ka-open sa pinagdadaanan mo.",
            "Ramdam ko ang bigat ng dinadala mo ngayon.",
        ],
        "taglish": [
            "I hear you, and valid na valid ang nararamdaman mo.",
            "That sounds heavy, salamat sa pagbabahagi nito sa akin.",
            "I'm listening, and I want you to know na important ang feelings mo.",
            "It takes courage to be this open about what you're going through.",
            "I can sense na medyo mabigat ang pinagdadaanan mo right now.",
        ]
    },
    "reflection": {
        "academic_stress": {
            "en": ["School pressure can feel truly overwhelming, especially with everything on your plate.", "The weight of academic expectations is a heavy thing to balance."],
            "tl": ["Mabigat talaga ang pressure sa school, lalo na sa dami ng kailangang gawin.", "Hindi biro ang bigat ng expectations sa pag-aaral."],
            "taglish": ["Ang bigat talaga ng pressure sa school, especially with everything on your plate.", "Hindi biro ang bigat ng academic expectations na kailangang i-balance."],
        },
        "relationship_issues": {
            "en": ["Relationship pain is deeply personal and can feel very isolating.", "It's hard when things with the people we care about aren't going well."],
            "tl": ["Ang sakit sa puso kapag may problema sa mga taong mahalaga sa atin.", "Mahirap talaga kapag hindi okay ang sitwasyon sa relasyon."],
            "taglish": ["Ang hirap talaga kapag may issues sa relationship with the people we care about.", "Relationship pain is deeply personal at minsan ay nakaka-isolate."],
        },
        "family_conflict": {
            "en": ["Family tension is such a difficult burden to navigate.", "It's tough when home doesn't feel like the peaceful place it should be."],
            "tl": ["Ang hirap harapin ng tensyon sa loob mismo ng pamilya.", "Mahirap kapag ang tahanan ay hindi nagbibigay ng kapayapaan."],
            "taglish": ["Minsan ang hirap i-navigate ng family tension, it's a difficult burden.", "It's tough kapag ang home ay hindi nagbibigay ng peace of mind."],
        },
        "financial_stress": {
            "en": ["Financial worries can steal your focus and create so much uncertainty.", "Worrying about money while trying to study is an immense burden."],
            "tl": ["Nakakaubos ng lakas ang isipin ang gastusin habang nag-aaral.", "Ang problema sa pera ay parang ulan na walang tigil minsan."],
            "taglish": ["Nakaka-drain iisipin ang financial problems while trying to focus sa studies.", "Financial worries can really create so much uncertainty sa school life."],
        },
        "burnout": {
            "en": ["Burnout is real, and it's a signal that you've been pushing yourself too hard.", "That feeling of being completely drained is your mind and body asking for rest."],
            "tl": ["Totoo ang burnout, at senyales ito na kailangan mo nang mag-slow down.", "Ang pagka-ubos ng lakas ay paraan ng katawan mo para humingi ng pahinga."],
            "taglish": ["Real ang burnout, and it’s a signal na push ka na nang push sa limit mo.", "That feeling of being drained is your body’s way of asking for rest."],
        },
        "general_anxiety": {
            "en": ["Anxiety can make the world feel much louder and more uncertain than it really is.", "That feeling of constant worry is incredibly draining."],
            "tl": ["Pinapalaki talaga ng anxiety ang mga kaba at pag-aalinlangan natin.", "Nakakaubos ng lakas ang palagiang pag-aalala."],
            "taglish": ["Anxiety can make things feel super uncertain and overwhelming.", "That feeling of constant worry is really draining, physically at mentally."],
        },
        "loneliness": {
            "en": ["Loneliness can feel like a cold shadow, even when people are around.", "It's painful to feel like you're facing things all by yourself."],
            "tl": ["Napakahirap ng pakiramdam na mag-isa, kahit may ibang tao pa sa paligid.", "Ang sakit maramdaman na parang wala kang kasama sa laban."],
            "taglish": ["Loneliness can feel like a cold shadow, kahit marami pang tao sa paligid.", "Ang sakit talaga ng feeling na parang you're facing everything all alone."],
        },
        "depression_grief": {
            "en": ["The weight of loss and sadness is something no one should have to carry alone.", "Grief is a heavy path, and it's okay to feel completely lost in it for a while."],
            "tl": ["Ang bigat ng pangungulila at lungkot ay hindi biro.", "Dugo't pawis ang kailangan para malampasan ang ganitong klaseng lumbay."],
            "taglish": ["The weight of loss and sadness is something na hindi mo dapat i-carry mag-isa.", "Grief is a heavy path, at okay lang na ma-feel na nawawala ka for a while."],
        },
        "self_esteem": {
            "en": ["It's hard when your inner voice is your harshest critic.", "Struggling with self-worth can make every small challenge feel like a mountain."],
            "tl": ["Mahirap kapag ang sarili nating isip ang pinaka-malupit nating kaaway.", "Ang kawalan ng tiwala sa sarili ay parang tanikala sa ating pag-unlad."],
            "taglish": ["Ang hirap kapag ang inner voice mo is your harshest critic.", "Struggling with self-worth can make every challenge feel like a mountain."],
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
        ],
        "tl": [
            "Gusto mo bang huminga muna tayo nang malalim? Makakatulong ito para kumalma.",
            "Nasubukan mo na bang isulat ang lahat ng nasa isip mo? Nakakagaan din ito ng loob.",
            "Okay lang na dahan-dahan ang pag-usad. Ano ang pinakamaliit na hakbang na kaya mong gawin ngayon?",
            "Tandaan na hindi mo kailangang ayusin ang lahat ngayon din. Ang pagpahinga ay bahagi rin ng pag-unlad.",
        ],
        "taglish": [
            "Gusto mo bang i-try ang 4-7-8 breathing together? It might help you calm down.",
            "Have you tried writing down your thoughts? Minsan nakakatulong ang ma-release ang nasa isip.",
            "Okay lang na mag-start small. What feels like the smallest thing na pwede mong gawin ngayon?",
            "Remember na hindi mo kailangang i-figure out lahat right now. Resting is progress too.",
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
        ],
        "tl": [
            "Nandito lang ako para sa iyo.",
            "Nakikinig ako. Ituloy mo lang kung handa ka na.",
            "Hindi ka nag-iisa sa labang ito.",
            "Pwede pa nating pag-usapan ito kung gusto mo.",
        ],
        "taglish": [
            "Nandito lang ako if you need someone to talk to.",
            "Nakikinig ako, kaya ituloy mo lang whenever you're ready.",
            "You're not alone in this fight, nandito ako.",
            "We can talk more about this if you want.",
        ]
    }
}

GROUNDING_TECHNIQUES = {
    "en": [
        "Try this: name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste. This can help ground you in the present moment.",
        "Let's try a breathing exercise: breathe in for 4 counts, hold for 4, breathe out for 6. Repeat this 3 times.",
        "It might help to get a glass of water and take a short walk, even just around the room.",
    ],
    "tl": [
        "Subukan natin ito: pangalanan mo ang 5 bagay na nakikita mo, 4 na nararamdaman, 3 na naririnig, 2 na naaaamoy, at 1 na nalalasahan. Makakatulong ito.",
        "Subukan nating huminga: huminga ng 4 beses, pigilan ng 4, ilabas ng 6. Ulitin ng 3 beses.",
        "Pwede kang kumuha ng tubig at maglakad sandali, kahit sa paligid lang ng kwarto.",
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
# STEP 10 — RESPONSE GENERATOR
# =============================================================================
def pick_fragment(pool: list, used: set) -> str:
    """Pick a fragment not yet used, or reset if all used."""
    available = [f for f in pool if f not in used]
    if not available:
        available = pool
    choice = random.choice(available)
    used.add(choice)
    return choice

def generate_response(
    intent: str,
    confidence: float,
    intensity: str,
    lang: str,
    escalation: dict,
    session_id: str,
    is_first_turn: bool,
) -> dict:
    used = get_used_responses(session_id)
    # Support en, tl, taglish
    lang_key = lang if lang in ["en", "tl", "taglish"] else "tl"
    prefix = TRANSPARENCY[lang_key] if is_first_turn else ""

    # 1. Validation (Mandatory first step - 1-2 phrases)
    val = pick_fragment(DYNAMIC_FRAGMENTS["validation"][lang_key], used)
    
    # 2. Supportive Presence ("Nandito ako para makinig")
    pres = DYNAMIC_FRAGMENTS["presence"][lang_key]
    
    # 3. Reflection (Recognize distress)
    intent_pool = DYNAMIC_FRAGMENTS["reflection"].get(intent, DYNAMIC_FRAGMENTS["reflection"]["other"])[lang_key]
    ref = pick_fragment(intent_pool, used)
    
    # 4. Gentle Exploration
    exploration_en = "Would you like to tell me more about it?"
    exploration_tl = "Gusto mo bang magkwento pa?"
    exploration_taglish = "Gusto mo bang magkwento pa about it?"
    exp = exploration_en if lang_key == "en" else exploration_taglish if lang_key == "taglish" else exploration_tl
    
    # 5. Guidance (Optional coping step)
    sug = pick_fragment(DYNAMIC_FRAGMENTS["suggestion"][lang_key], used)
    cls = pick_fragment(DYNAMIC_FRAGMENTS["closing"][lang_key], used)

    # Assemble based on intensity
    if intensity == "high":
        grounding = random.choice(GROUNDING_TECHNIQUES.get(lang_key, GROUNDING_TECHNIQUES["tl"]))
        # Higher intensity: Validation -> Reflection -> Grounding -> Presence -> Exploration
        final_text = f"{prefix}{val} {ref} {grounding} {pres} {exp}"
        action = "high_distress_grounding"
    elif confidence < 0.7:
        # Low confidence: Validation -> Presence -> Clarification
        clarifier = " Can you tell me a bit more about what's on your mind?" if lang_key == "en" else " Maaari mo bang ikwento pa ang nasa isip mo?"
        final_text = f"{prefix}{val} {pres} {clarifier}"
        action = "clarification"
    else:
        # Standard: Validation -> Reflection -> Presence -> Suggestion -> Closing
        final_text = f"{prefix}{val} {ref} {pres} {sug} {cls}"
        action = intent

    # Add escalation bump if needed (Ka-PEER Yu / Guidance Office)
    if escalation["escalate"]:
        final_text += ESCALATION_BUMP[lang_key]

    # Ensure length < 100 words
    words = final_text.split()
    if len(words) > 95:
        final_text = " ".join(words[:95]) + "..."

    # INTERNAL THOUGHT: Does this empower, protect, and respect the LSPU student? Yes.
    return {
        "response": final_text,
        "action": action,
    }


# =============================================================================
# MAIN ENGINE — ORCHESTRATOR
# =============================================================================
# =============================================================================
class MentalHealthEngine:
    def __init__(self):
        logger.info("Initializing MindGuard Hybrid ML System V10 (Scikit + TF)...")
        self._initialize_models()

    def _initialize_models(self):
        # --- 1. Vectorization (TF-IDF) & 2. Intent Classification (Logistic Regression / SVM) ---
        self.vectorizer = TfidfVectorizer(max_features=5000)
        
        # Expanded Supervised Dataset (Hybrid Bootstrap for all 14 categories)
        intent_texts = [
            "hello", "hi there", "hey",
            "im so stressed about finals", "deadlines are killing me",
            "my heart is broken", "relationship problems",
            "gulo sa bahay", "trouble with family",
            "tuition problems", "baon sa utang",
            "lonely at school", "no one to talk to",
            "drain na drain na ako", "excessive burnout",
            "panic attack", "anxiety through the roof",
            "missing them so much", "deep grief and loss",
            "feeling ugly and worthless", "low self esteem issues",
            "fear of the future", "career anxiety path",
            "they are rumor-spreading", "school bullying and harassment",
            "scared of serious illness", "health anxiety check",
            "kumusta ka", "just checking in",
            "need guidance please", "looking for professional help",
            "i want to die", "crisis emergency line"
        ]
        intent_labels = [
            "greeting", "greeting", "greeting",
            "academic_stress", "academic_stress",
            "relationship_issues", "relationship_issues",
            "family_conflict", "family_conflict",
            "financial_stress", "financial_stress",
            "loneliness", "loneliness",
            "burnout", "burnout",
            "general_anxiety", "general_anxiety",
            "depression_grief", "depression_grief",
            "self_esteem", "self_esteem",
            "career_anxiety", "career_anxiety",
            "bullying", "bullying",
            "health_anxiety", "health_anxiety",
            "general_chat", "general_chat",
            "seeking_support", "seeking_support",
            "crisis", "crisis"
        ]
        
        X_tfidf = self.vectorizer.fit_transform(intent_texts)
        
        # Linear SVM for Intent Recognition (Fast & High Accuracy for Classification)
        self.intent_classifier = LinearSVC(C=1.0, dual="auto")
        self.intent_classifier.fit(X_tfidf, intent_labels)

        # --- 3. Mood / Sentiment Detection (Logistic Regression) ---
        mood_map = {
            "greeting": "Okay", "academic_stress": "Stressed", "relationship_issues": "Sad",
            "family_conflict": "Angry", "financial_stress": "Stressed", "loneliness": "Sad",
            "burnout": "Stressed", "general_anxiety": "Anxious", "depression_grief": "Sad",
            "self_esteem": "Insecure", "career_anxiety": "Anxious", "bullying": "Sad",
            "health_anxiety": "Anxious", "general_chat": "Okay", "seeking_support": "Okay",
            "crisis": "Crisis"
        }
        mood_labels = [mood_map[l] for l in intent_labels]
        self.mood_classifier = LogisticRegression(max_iter=1000)
        self.mood_classifier.fit(X_tfidf, mood_labels)

        # --- 4. Risk Detection Model (Critical) ---
        # Binary: 1 = Crisis/High Risk, 0 = Standard
        risk_labels = [1 if l == "crisis" else 0 for l in intent_labels]
        self.risk_classifier = LogisticRegression(max_iter=1000)
        self.risk_classifier.fit(X_tfidf, risk_labels)

        # --- 5. Unsupervised Learning (Intent Discovery - KMeans) ---
        self.clustering_model = KMeans(n_clusters=6, random_state=42, n_init='auto')
        self.clustering_model.fit(X_tfidf)

        # --- 6. Semi-Supervised Learning (Self-Training) ---
        base_lr = LogisticRegression(max_iter=1000)
        self.semi_supervised = Self_Training = SelfTrainingClassifier(base_lr, threshold=0.8)
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
        
        # Severity weights (Mock for Contextual NLU)
        severity_map = {
            "greeting": 0.1, "academic_stress": 0.5, "crisis": 1.0, "depression_grief": 0.8,
            "bullying": 0.7, "self_esteem": 0.6
        }
        y_lstm = np.array([severity_map.get(l, 0.4) for l in intent_labels])

        self.lstm_model = Sequential([
            Embedding(input_dim=5000, output_dim=32, input_length=self.max_len),
            LSTM(32, return_sequences=False),
            Dense(16, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        self.lstm_model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        self.lstm_model.fit(X_pad, y_lstm, epochs=1, verbose=0)
        logger.info("Hybrid ML Architecture (Scikit + LSTM) Loaded Successfully!")

    def process(self, req: ChatRequest, db: Session) -> dict:
        text = req.message
        lang = lang_det.detect(text)
        lang_key = lang # Now supports "en", "tl", "taglish"
        is_first_turn = req.turn == 0

        # -- Database: Get or Create Session --
        db_session = db.query(models.ChatSession).filter(models.ChatSession.session_id == req.session_id).first()
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
        user_msg = models.MessageLog(session_id=db_session.session_id, sender="user", text=text)
        db.add(user_msg)

        # ── ML PIPELINE EXECUTION ───────────────────────────────────────────
        
        # 1. Vectorization
        vec_input = self.vectorizer.transform([text])
        
        # 2. Intent Classification (LinearSVC)
        ml_intent = self.intent_classifier.predict(vec_input)[0]
        ml_confidence = 0.85 

        # 3. Mood Detection
        ml_mood = self.mood_classifier.predict(vec_input)[0]

        # 4. Risk Detection
        ml_risk_flag = self.risk_classifier.predict(vec_input)[0] == 1
        
        # 5. LSTM Contextual Risk Scoring (Severity)
        seq = self.tokenizer.texts_to_sequences([text])
        pad_seq = pad_sequences(seq, maxlen=self.max_len)
        lstm_score = float(self.lstm_model.predict(pad_seq, verbose=0)[0][0])
        
        # Layer 1 Hard-coded Regex Crisis fallback (Highest priority overrides ML)
        crisis = crisis_detection(text)
        
        if crisis or (ml_risk_flag and ml_intent == "crisis"):
            level = crisis["level"] if crisis else "CRISIS"
            logger.critical(f"⚠️ CRISIS [{level}] | Session: {req.session_id}")
            
            # Map to LSPU Crisis Levels: standard (Soft), plan, or high_risk
            if level == "CRISIS_PLAN":
                response_type = "plan"
            elif lstm_score > 0.8:
                response_type = "high_risk"
            else:
                response_type = "standard" # Soft Crisis
                
            reply_text = CRISIS_RESPONSES[lang_key][response_type]

            # DB Update
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
            bot_msg = models.MessageLog(session_id=db_session.session_id, sender="bot", text=reply_text)
            
            db.add(new_alert)
            db.add(bot_msg)
            db.commit()

            return {
                "response": reply_text,
                "action": f"crisis_{response_type}",
                "sentiment": ml_mood,
                "reasoning": {"crisis": True, "level": response_type, "lstm_severity": lstm_score},
            }

        # 6. Intent Discovery (KMeans) - Analytics
        cluster_id = int(self.clustering_model.predict(vec_input)[0])

        # 7. Rule-based intensity & escalation
        intensity = emotional_intensity(text)
        escalation = monitor_escalation(req.session_id, ml_intent, intensity)
        
        # Fallback intent mapping if ML failed to generalize
        if len(text.split()) < 2 and ml_intent not in ["greeting", "crisis"]:
            ml_intent, ml_confidence = classify_intent(text)

        # ── RESPONSE GENERATION ────────────────────────────────────
        result = generate_response(
            ml_intent, ml_confidence, intensity, lang, escalation, req.session_id, is_first_turn
        )

        # ── ADMIN DATA UPDATE (SQLITE) ──────────────────────────────────────
        current_risk_level = 1 if lstm_score > 0.6 else 0
        if intensity == "high":
            current_risk_level = max(current_risk_level, 2)
        elif intensity == "moderate" or escalation["escalate"]:
            current_risk_level = max(current_risk_level, 1)

        db_session.highest_risk_level = max(db_session.highest_risk_level, current_risk_level)
        db_session.latest_mood = ml_mood
        db_session.action_taken = result["action"]
        db_session.total_turns += 1
        db_session.last_updated = datetime.datetime.utcnow()

        if current_risk_level >= 2 or escalation["escalate"] or lstm_score > 0.8:
            new_alert = models.AlertLog(
                session_id=db_session.session_id,
                risk_level=current_risk_level,
                action_taken=result["action"],
                latest_mood=db_session.latest_mood
            )
            db.add(new_alert)
        
        bot_msg = models.MessageLog(session_id=db_session.session_id, sender="bot", text=result["response"])
        db.add(bot_msg)
        db.commit()

        return {
            "response": result["response"],
            "action": result["action"],
            "sentiment": ml_mood,
            "reasoning": {
                "ml_intent": ml_intent,
                "ml_mood": ml_mood,
                "cluster_id": cluster_id,
                "lstm_severity_score": round(lstm_score, 3),
            },
        }

engine_app = MentalHealthEngine()

# =============================================================================
# API ENDPOINTS
# =============================================================================
@app.get("/")
def home():
    return {"status": "MindGuard Hybrid Engine V10 Ready"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = engine_app.process(req, db)
        return ChatResponse(
            response=result["response"],
            sentiment="neutral",
            action=result.get("action", "none"),
            reasoning=result.get("reasoning"),
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
            "last_interaction": s.last_updated.isoformat()
        }
        for s in sessions
    ]

# -----------------------------------------------------------------------------
# PROFILE / PASSWORD MANAGEMENT
# -----------------------------------------------------------------------------
@app.put("/api/profile/{user_id}")
def update_profile(user_id: int, req: UpdateProfileRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first() # Changed User to models.User
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
        
    # Return user details for frontend context
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
    user = db.query(models.User).filter(models.User.id == user_id).first() # Changed User to models.User
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Verify current password
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password updated successfully"}

# -----------------------------------------------------------------------------
# ADMIN CRUD: MANAGE STUDENTS
# -----------------------------------------------------------------------------
@app.post("/api/admin/students")
def create_student(req: CreateStudentRequest, db: Session = Depends(get_db)):
    # Check if email exists
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_student = User(
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
    student = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    student.fullname = req.fullname
    student.email = req.email
    student.program = req.program
    db.commit()
    return {"status": "success", "message": "Student updated successfully"}

@app.delete("/api/admin/students/{user_id}")
def delete_student(user_id: int, db: Session = Depends(get_db)):
    student = db.query(User).filter(User.id == user_id, User.role == "student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    db.delete(student) # Cascade to sessions/messages
    db.commit()
    return {"status": "success", "message": "Student deleted successfully"}

# -----------------------------------------------------------------------------
# ADMIN CRUD: MANAGE ADMINS (With Primary Restriction)
# -----------------------------------------------------------------------------
@app.get("/api/admin/admins")
def get_admins(db: Session = Depends(get_db)):
    admins = db.query(User).filter(User.role == "admin").all()
    return [
        {
            "id": a.id,
            "fullname": a.fullname,
            "email": a.email,
            "role_title": a.program, # Using 'program' field to store Guidence vs Peer
            "is_primary": a.is_primary_admin
        }
        for a in admins
    ]

@app.post("/api/admin/admins")
def create_admin(req: CreateAdminRequest, requester_email: str, db: Session = Depends(get_db)):
    # 1. Enforce Primary Admin Rule
    requester = db.query(User).filter(User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can create new administrators.")
        
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_admin = User(
        email=req.email,
        password_hash=hash_password(req.password),
        fullname=req.fullname,
        program=req.role, # Mapping generic Guidence/Peer title here
        role="admin",
        is_primary_admin=False
    )
    db.add(new_admin)
    
    # 2. Fire Audit Log
    audit = AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="CREATED_ADMIN",
        target_email=req.email
    )
    db.add(audit)
    db.commit()
    
    return {"status": "success", "message": f"Admin {req.email} successfully created."}

@app.put("/api/admin/admins/{user_id}")
def update_admin(user_id: int, req: UpdateAdminRequest, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(User).filter(User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can edit other administrators.")
        
    admin = db.query(User).filter(User.id == user_id, User.role == "admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    admin.fullname = req.fullname
    admin.email = req.email
    admin.program = req.role
    
    db.commit()
    return {"status": "success"}

@app.delete("/api/admin/admins/{user_id}")
def delete_admin(user_id: int, requester_email: str, db: Session = Depends(get_db)):
    requester = db.query(User).filter(User.email == requester_email).first()
    if not requester or not requester.is_primary_admin:
        raise HTTPException(status_code=403, detail="Only the Primary Admin can delete administrators.")
        
    admin = db.query(User).filter(User.id == user_id, User.role == "admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    if admin.is_primary_admin:
        raise HTTPException(status_code=400, detail="Cannot delete the Primary Admin.")
        
    db.delete(admin)
    
    # Log Deletion
    audit = AdminAuditLog(
        actor_admin_email=requester_email,
        action_type="DELETED_ADMIN",
        target_email=admin.email
    )
    db.add(audit)
    db.commit()
    return {"status": "success"}

# -----------------------------------------------------------------------------
# EXISTING DASHBOARD ANALYTICS
# -----------------------------------------------------------------------------
@app.get("/api/admin/summary")
def get_admin_summary(db: Session = Depends(get_db)):
    active = db.query(models.ChatSession).count()
    
    # Calculate conversations today
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
    moods = {"Happy": 0, "Okay": 0, "Stressed": 0, "Sad": 0, "Crisis": 0}
    
    for s in sessions:
        m = s.latest_mood.capitalize()
        # Fallback mappings just in case
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

@app.get("/api/admin/alerts")
def get_admin_alerts(db: Session = Depends(get_db)):
    alerts = db.query(models.AlertLog).order_by(models.AlertLog.timestamp.desc()).all()
    out = []
    for a in alerts:
        out.append({
            "session_id": a.session_id,
            "risk_level": a.risk_level,
            "mood": a.latest_mood or "Unknown",
            "action": a.action_taken,
            "timestamp": a.timestamp.isoformat(),
            "is_reviewed": a.is_reviewed
        })
    return out


# =============================================================================
# STAFF MANAGEMENT (Admin only)
# =============================================================================
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

# =============================================================================
# SAVED AFFIRMATIONS (Student / User)
# =============================================================================
@app.get("/api/affirmations/{user_id}")
def get_saved_affirmations(user_id: int, db: Session = Depends(get_db)):
    affirmations = db.query(models.SavedAffirmation).filter(
        models.SavedAffirmation.user_id == user_id
    ).order_by(models.SavedAffirmation.created_at.desc()).all()
    return [{"id": a.id, "text": a.text, "created_at": a.created_at.isoformat()} for a in affirmations]

@app.post("/api/affirmations/{user_id}")
def save_affirmation(user_id: int, req: SaveAffirmationRequest, db: Session = Depends(get_db)):
    # Prevent duplicate saves
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

# =============================================================================
# SYSTEM AUDIT LOGS (Admin only)
# =============================================================================
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
