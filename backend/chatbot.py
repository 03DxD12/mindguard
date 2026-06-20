from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import random

# Layer 1: Understanding Layer (Model)
print("Loading sentence transformer model... this may take a moment.")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("Model loaded.")

INTENTS = [
    "stress",
    "anxiety",
    "sadness",
    "crisis",
    "casual"
]

# Layer 2: Response Layer (Curated empathy)
RESPONSES = {
    "stress": [
        "I'm here with you. Do you want to talk about what's overwhelming you?",
        "That sounds heavy. What's been stressing you the most lately?"
    ],
    "anxiety": [
        "That sounds difficult. Want to tell me what's making you anxious?",
        "Anxiety can feel very isolating, but I'm here. Take your time."
    ],
    "sadness": [
        "I'm really sorry you're feeling this way. You don't have to go through it alone.",
        "It's okay to feel sad. I'm here to listen to whatever is on your mind."
    ],
    "casual": [
        "I'm here. What's on your mind?",
        "How is everything going today?"
    ],
    "crisis": [
        "Please let someone know you're hurting."
    ]
}

# Risk Scoring Mapping
RISK_SCORES = {
    "casual": 0,
    "stress": 1,
    "anxiety": 1,
    "sadness": 2,
    "crisis": 3
}

# Layer 3: Safety Layer (Non-negotiable)
CRISIS_KEYWORDS = ["suicide", "kill myself", "hurt myself", "end my life", "want to die", "worthless"]

def detect_crisis(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in CRISIS_KEYWORDS)

def get_chat_response(user_input: str):
    # Safety Override First
    if detect_crisis(user_input):
        return {
            "reply": "You're not alone. Please contact a trusted person or a professional immediately. You deserve support.",
            "intent": "crisis",
            "risk_level": 3
        }
    
    # 1. Compute Embeddings
    embeddings = model.encode([user_input] + INTENTS)
    
    # 2. Similarity
    similarities = cosine_similarity([embeddings[0]], embeddings[1:])[0]
    best_match_index = similarities.argmax()
    
    intent = INTENTS[best_match_index]
    
    # 3. Response Generation
    reply = random.choice(RESPONSES[intent])
    risk_level = RISK_SCORES.get(intent, 0)
    
    return {
        "reply": reply,
        "intent": intent,
        "risk_level": risk_level
    }
