"""
MindGuard Semantic Intelligence Module
=======================================
Provides sentence-transformer embeddings, emotion anchor matching,
and cosine-similarity helpers for the main AI pipeline.
"""

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
import hashlib
import os
import re

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

# ─── Layer 1: Semantic Understanding Model ─────────────────────────────────
class LocalSemanticFallback:
    """Small deterministic embedding fallback when MiniLM is unavailable."""

    dimension = 384

    def encode(self, texts, show_progress_bar=False):
        if isinstance(texts, str):
            texts = [texts]
        return np.array([self._encode_one(text) for text in texts], dtype=np.float32)

    def _encode_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
        tokens = re.findall(r"[a-z0-9_']+", normalized)
        features = tokens + [normalized[i:i + 3] for i in range(max(len(normalized) - 2, 0))]

        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector


def load_semantic_model():
    if SentenceTransformer is None:
        logger.warning("sentence-transformers import failed; using local semantic fallback.")
        return LocalSemanticFallback()

    use_local_minilm = os.getenv("MINGUARD_USE_LOCAL_MINILM", "false").lower() == "true"
    if not use_local_minilm:
        logger.info("Using temporary local semantic fallback. Set MINGUARD_USE_LOCAL_MINILM=true to load MiniLM.")
        return LocalSemanticFallback()

    try:
        logger.info("Loading sentence transformer model (all-MiniLM-L6-v2)...")
        allow_download = os.getenv("MINGUARD_ALLOW_MODEL_DOWNLOAD", "false").lower() == "true"
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            local_files_only=not allow_download,
        )
        logger.info("Sentence transformer model loaded successfully.")
        return model
    except Exception as exc:
        logger.warning("MiniLM model unavailable; using local semantic fallback: %s", exc)
        return LocalSemanticFallback()


semantic_model = load_semantic_model()

# ─── Emotion Anchor Embeddings ─────────────────────────────────────────────
# Pre-computed embeddings for 35+ emotional states used for semantic matching.
# When a user message arrives, we compare its embedding against these anchors
# to detect emotional state even without explicit keywords.

EMOTION_ANCHORS = {
    # Level 0 — Normal / Positive
    "happy": "I feel happy and content with my life right now",
    "motivated": "I am feeling motivated and ready to achieve my goals",
    "relaxed": "I feel calm and relaxed, everything is peaceful",
    "grateful": "I am grateful for the good things in my life",
    "hopeful": "I feel hopeful about the future and what is ahead",
    "confident": "I feel confident and strong in myself",

    # Level 1 — Mild Distress
    "stressed": "I am feeling stressed and pressured by everything",
    "frustrated": "I am frustrated and annoyed by my situation",
    "anxious": "I feel anxious and worried about things",
    "nervous": "I am nervous and uneasy about what might happen",
    "irritable": "I feel irritable and easily upset today",
    "restless": "I feel restless and cannot settle down",
    "academic_pressure": "I am overwhelmed by school work and deadlines",

    # Level 2 — Moderate Distress
    "sad": "I feel sad and down, nothing makes me happy anymore",
    "lonely": "I feel completely alone and isolated from everyone",
    "exhausted": "I am emotionally and physically exhausted and drained",
    "overwhelmed": "I feel overwhelmed and cannot handle everything anymore",
    "burnout": "I am burned out and have no energy or motivation left",
    "worthless": "I feel worthless and not good enough for anything",
    "grief": "I am grieving and the pain of loss is unbearable",
    "insecure": "I feel insecure and hate everything about myself",
    "numb": "I feel numb and empty inside, nothing matters",
    "trapped": "I feel trapped with no way out of my situation",

    # Level 3 — High Risk / Crisis
    "hopeless": "I have lost all hope and see no reason to continue",
    "suicidal": "I want to end my life and stop all this pain",
    "self_harm": "I want to hurt myself to make the pain stop",
    "despair": "I am in complete despair and cannot go on",
    "giving_up": "I have given up on everything and everyone",
    "abandoned": "Everyone has abandoned me and I am completely alone",
    "crisis_overwhelm": "I cannot take this anymore I just want everything to stop",
}

# Risk level mapping for each anchor
ANCHOR_RISK_LEVELS = {
    "happy": 0, "motivated": 0, "relaxed": 0, "grateful": 0, "hopeful": 0, "confident": 0,
    "stressed": 1, "frustrated": 1, "anxious": 1, "nervous": 1, "irritable": 1,
    "restless": 1, "academic_pressure": 1,
    "sad": 2, "lonely": 2, "exhausted": 2, "overwhelmed": 2, "burnout": 2,
    "worthless": 2, "grief": 2, "insecure": 2, "numb": 2, "trapped": 2,
    "hopeless": 3, "suicidal": 3, "self_harm": 3, "despair": 3,
    "giving_up": 3, "abandoned": 3, "crisis_overwhelm": 3,
}

# Pre-compute anchor embeddings at startup
_anchor_texts = list(EMOTION_ANCHORS.values())
_anchor_keys = list(EMOTION_ANCHORS.keys())
_anchor_embeddings = semantic_model.encode(_anchor_texts, show_progress_bar=False)

# ─── Intent Anchor Embeddings ──────────────────────────────────────────────
# Used for semantic intent classification alongside TF-IDF

INTENT_ANCHORS = {
    "academic_stress": [
        "I am stressed about my exams and grades",
        "My thesis is overwhelming me, I cannot finish it",
        "Too many assignments and deadlines to handle",
        "I am failing my subjects and feel terrible",
    ],
    "relationship_issues": [
        "My partner and I broke up and I am devastated",
        "I am having problems in my romantic relationship",
        "Trust issues with my boyfriend or girlfriend",
    ],
    "family_conflict": [
        "My parents fight all the time and I am scared",
        "There is tension and conflict in my family",
        "My family does not understand me at all",
    ],
    "financial_stress": [
        "I cannot pay my tuition and I am worried about money",
        "Financial problems are making it hard to focus on school",
    ],
    "loneliness": [
        "I feel alone and have no real friends",
        "Nobody talks to me and I feel invisible",
        "I eat alone and feel isolated from everyone",
    ],
    "burnout": [
        "I am completely burned out and exhausted",
        "I have no energy or motivation left for anything",
        "I have been working so hard and I feel empty inside",
    ],
    "general_anxiety": [
        "I have panic attacks and constant worry",
        "I am always anxious even when nothing is wrong",
        "My anxiety is through the roof and I cannot sleep",
    ],
    "depression_grief": [
        "I lost someone I love and cannot move on",
        "Everything feels dark and hopeless",
        "I have not left my bed in days, everything is heavy",
    ],
    "self_esteem": [
        "I hate how I look and feel ugly and worthless",
        "I am not good enough for anything or anyone",
        "Everyone is better and smarter than me",
    ],
    "career_anxiety": [
        "I do not know what to do with my life after college",
        "I am scared I will not find a job after graduation",
    ],
    "bullying": [
        "People are spreading rumors about me at school",
        "I am being bullied and harassed by classmates",
        "Cyberbullying is affecting my mental health",
    ],
    "health_anxiety": [
        "I am constantly worried I have a serious illness",
        "Every little pain makes me think the worst",
    ],
    "general_chat": [
        "Hello how are you today",
        "I just wanted to talk to someone",
        "What can you do for me",
    ],
    "seeking_support": [
        "I need help and guidance from someone",
        "I want to seek professional help for my problems",
        "Where can I reach out for support",
    ],
}

# Pre-compute intent anchor embeddings
_intent_anchor_embeddings = {}
for intent, texts in INTENT_ANCHORS.items():
    _intent_anchor_embeddings[intent] = semantic_model.encode(texts, show_progress_bar=False)


# ─── Public API Functions ──────────────────────────────────────────────────

def encode_text(text: str) -> np.ndarray:
    """Encode a single text into a semantic embedding vector."""
    return semantic_model.encode([text], show_progress_bar=False)[0]


def encode_texts(texts: list) -> np.ndarray:
    """Encode a batch of texts into semantic embedding vectors."""
    return semantic_model.encode(texts, show_progress_bar=False)


def get_emotion_match(text: str, top_k: int = 3) -> list:
    """
    Match user text against emotion anchors.
    Returns top-k matches with (emotion, similarity, risk_level).
    """
    text_emb = encode_text(text).reshape(1, -1)
    sims = cosine_similarity(text_emb, _anchor_embeddings)[0]
    top_indices = sims.argsort()[::-1][:top_k]
    return [
        {
            "emotion": _anchor_keys[i],
            "similarity": round(float(sims[i]), 4),
            "risk_level": ANCHOR_RISK_LEVELS[_anchor_keys[i]],
        }
        for i in top_indices
    ]


def get_semantic_intent(text: str) -> dict:
    """
    Classify intent using semantic similarity against intent anchors.
    Returns {"intent": str, "confidence": float, "scores": dict}.
    """
    text_emb = encode_text(text).reshape(1, -1)
    intent_scores = {}
    for intent, anchor_embs in _intent_anchor_embeddings.items():
        sims = cosine_similarity(text_emb, anchor_embs)[0]
        intent_scores[intent] = float(sims.max())

    best_intent = max(intent_scores, key=intent_scores.get)
    return {
        "intent": best_intent,
        "confidence": round(intent_scores[best_intent], 4),
        "scores": {k: round(v, 4) for k, v in sorted(intent_scores.items(), key=lambda x: -x[1])[:5]},
    }


def get_semantic_risk_score(text: str) -> dict:
    """
    Compute a semantic risk score by analyzing emotion anchor matches.
    Returns {"score": float 0-1, "level": int 0-3, "top_emotions": list}.
    """
    matches = get_emotion_match(text, top_k=5)
    # Weighted risk score: higher similarity to high-risk anchors = higher score
    weighted_score = 0.0
    total_weight = 0.0
    for m in matches:
        weight = m["similarity"]
        risk_contribution = m["risk_level"] / 3.0  # Normalize to 0-1
        weighted_score += weight * risk_contribution
        total_weight += weight

    risk_score = weighted_score / max(total_weight, 0.001)

    # Map to risk level
    if risk_score >= 0.65:
        level = 3
    elif risk_score >= 0.45:
        level = 2
    elif risk_score >= 0.25:
        level = 1
    else:
        level = 0

    return {
        "score": round(risk_score, 4),
        "level": level,
        "top_emotions": matches[:3],
    }


def compute_embedding_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    return float(cosine_similarity(emb1.reshape(1, -1), emb2.reshape(1, -1))[0][0])


def analyze_text_themes(texts: list) -> dict:
    """
    Analyze a batch of texts (e.g. journal entries) to detect dominant themes.
    Returns {"themes": list of (theme, score), "risk_indicators": list}.
    """
    if not texts:
        return {"themes": [], "risk_indicators": []}

    embeddings = encode_texts(texts)
    avg_embedding = embeddings.mean(axis=0).reshape(1, -1)

    # Match average against intent anchors
    intent_scores = {}
    for intent, anchor_embs in _intent_anchor_embeddings.items():
        sims = cosine_similarity(avg_embedding, anchor_embs)[0]
        intent_scores[intent] = float(sims.max())

    # Match against emotion anchors
    emotion_sims = cosine_similarity(avg_embedding, _anchor_embeddings)[0]
    top_emotion_indices = emotion_sims.argsort()[::-1][:5]
    top_emotions = [
        {"emotion": _anchor_keys[i], "similarity": round(float(emotion_sims[i]), 4)}
        for i in top_emotion_indices
    ]

    # Sort themes by score
    sorted_themes = sorted(intent_scores.items(), key=lambda x: -x[1])[:5]

    # Detect risk indicators
    risk_indicators = []
    for i in top_emotion_indices[:3]:
        if ANCHOR_RISK_LEVELS[_anchor_keys[i]] >= 2:
            risk_indicators.append(_anchor_keys[i])

    return {
        "themes": [(t, round(s, 4)) for t, s in sorted_themes],
        "dominant_emotions": top_emotions,
        "risk_indicators": risk_indicators,
    }
