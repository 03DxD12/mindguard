# backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50), default="student") # "student" or "admin"
    is_primary_admin = Column(Boolean, default=False)
    fullname = Column(String(255), nullable=True)
    student_id = Column(String(50), nullable=True)
    program = Column(String(255), nullable=True)
    trusted_contacts = Column(String(255), nullable=True) # JSON string of up to 3 contacts
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("ChatSession", back_populates="user")
    mood_logs = relationship("MoodLog", back_populates="user", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True, index=True) # E.g., "stud-A100"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Linked to a persistent user
    start_time = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    latest_mood = Column(String(50), default="Okay")
    highest_risk_level = Column(Integer, default=0)
    total_turns = Column(Integer, default=0)
    action_taken = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("MessageLog", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("AlertLog", back_populates="session", cascade="all, delete-orphan")


class MessageLog(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.session_id"))
    sender = Column(String(50)) # "user" or "bot"
    text = Column(String(2000))
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class AlertLog(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("sessions.session_id"))
    risk_level = Column(Integer)
    action_taken = Column(String(255), nullable=True)
    latest_mood = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_reviewed = Column(Boolean, default=False)

    session = relationship("ChatSession", back_populates="alerts")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_admin_email = Column(String(255), index=True)
    action_type = Column(String(100))
    target_email = Column(String(255), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class SavedAffirmation(Base):
    __tablename__ = "saved_affirmations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# ─── NEW MODELS ────────────────────────────────────────────────────────────

class MoodLog(Base):
    """Server-side mood tracking — replaces localStorage-only approach."""
    __tablename__ = "mood_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mood = Column(String(50), nullable=False)       # Great, Good, Okay, Down, Crisis
    value = Column(Integer, nullable=False)           # 1=Crisis, 2=Down, 3=Okay, 4=Good, 5=Great
    note = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mood_logs")


class JournalEntry(Base):
    """Server-side journal entries with AI analysis metadata."""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    mood = Column(String(50), nullable=True)          # Emoji or label
    themes_json = Column(Text, nullable=True)         # JSON array of detected themes
    risk_indicators = Column(Text, nullable=True)     # JSON array of risk signals
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="journal_entries")


class DailyAffirmationHistory(Base):
    """Tracks which affirmations have been shown to prevent repetition."""
    __tablename__ = "daily_affirmation_history"

    id = Column(Integer, primary_key=True, index=True)
    affirmation_text = Column(String(500), nullable=False)
    mood_category = Column(String(50), nullable=True)
    shown_date = Column(DateTime, default=datetime.utcnow)


class AIDecisionLog(Base):
    """Responsible AI — logs all AI predictions and escalations."""
    __tablename__ = "ai_decision_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_message_hash = Column(String(64), nullable=True)  # Anonymized
    ml_intent = Column(String(100), nullable=True)
    ml_confidence = Column(Float, nullable=True)
    semantic_intent = Column(String(100), nullable=True)
    semantic_confidence = Column(Float, nullable=True)
    fused_intent = Column(String(100), nullable=True)
    emotion_detected = Column(String(100), nullable=True)
    risk_rule_score = Column(Integer, nullable=True)
    risk_ml_score = Column(Float, nullable=True)
    risk_semantic_score = Column(Float, nullable=True)
    risk_dl_score = Column(Float, nullable=True)
    final_risk_level = Column(Integer, nullable=True)
    action_taken = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
