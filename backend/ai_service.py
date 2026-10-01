"""
MindGuard AI provider abstraction.

The local MindGuard engine remains the safety and risk authority. Optional
hosted providers can improve wording for non-crisis responses, then the system
falls back to the local response when the provider is missing or unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are MindGuard, a supportive mental health companion for university students.
Be warm, natural, concise, and culturally sensitive to English, Filipino, and Taglish.
Be transparent that you are an AI companion, not a therapist or emergency service.
Support the user's autonomy, dignity, privacy, and consent. Do not diagnose, shame, judge,
pressure, make promises of constant availability, or encourage harmful behavior.
If the user appears unsafe, encourage immediate trusted-person, professional, or emergency support.
Ask one meaningful follow-up question when appropriate. Keep the reply under 95 words."""


@dataclass
class AIContext:
    message: str
    history: List[str]
    local_response: str
    sentiment: str
    action: str
    reasoning: Dict[str, Any]
    mood: str = "Okay"


@dataclass
class AIServiceResult:
    response: str
    provider: str
    used_fallback: bool
    error: Optional[str] = None


class BaseAIProvider:
    name = "base"

    def is_configured(self) -> bool:
        return False

    def generate(self, context: AIContext) -> str:
        raise NotImplementedError


class LocalFallbackProvider(BaseAIProvider):
    name = "local"

    def is_configured(self) -> bool:
        return True

    def generate(self, context: AIContext) -> str:
        return context.local_response


class GitHubModelsProvider(BaseAIProvider):
    name = "github_models"

    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.model = os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1")
        self.endpoint = os.getenv(
            "GITHUB_MODELS_ENDPOINT",
            "https://models.github.ai/inference/chat/completions",
        )
        self.api_version = os.getenv("GITHUB_MODELS_API_VERSION", "2026-03-10")
        self.timeout = float(os.getenv("GITHUB_MODELS_TIMEOUT_SECONDS", "8"))

    def is_configured(self) -> bool:
        return bool(self.token)

    def generate(self, context: AIContext) -> str:
        if not self.token:
            raise RuntimeError("GITHUB_MODELS_TOKEN or GITHUB_TOKEN is not configured")

        messages = self._build_messages(context)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.45,
            "max_tokens": 220,
            "top_p": 0.9,
            "frequency_penalty": 0.35,
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": self.api_version,
            },
        )

        with urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            raise RuntimeError("GitHub Models returned an empty response")
        return content

    def _build_messages(self, context: AIContext) -> List[Dict[str, str]]:
        reasoning = context.reasoning or {}
        risk_level = reasoning.get("fused_risk_level", 0)
        emotion = reasoning.get("emotion") or "unknown"
        intent = reasoning.get("fused_intent") or reasoning.get("semantic_intent") or "general_chat"
        recent_history = [item for item in context.history[-8:] if item]

        user_context = {
            "current_mood": context.mood,
            "detected_sentiment": context.sentiment,
            "detected_intent": intent,
            "detected_emotion": emotion,
            "risk_level": risk_level,
            "local_safe_response": context.local_response,
            "recent_history": recent_history,
            "latest_user_message": context.message,
        }

        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Improve the local safe response using the context below. "
                    "Preserve the same safety posture and do not add diagnosis.\n\n"
                    f"{json.dumps(user_context, ensure_ascii=False)}"
                ),
            },
        ]


class AIService:
    def __init__(self, provider: Optional[BaseAIProvider] = None) -> None:
        self.provider = provider or GitHubModelsProvider()
        self.fallback = LocalFallbackProvider()

    def generate_response(self, context: AIContext) -> AIServiceResult:
        risk_level = int((context.reasoning or {}).get("fused_risk_level") or 0)
        if risk_level >= 3 or str(context.action).startswith("crisis_"):
            return AIServiceResult(
                response=context.local_response,
                provider=self.fallback.name,
                used_fallback=True,
            )

        if not self.provider.is_configured():
            return AIServiceResult(
                response=self.fallback.generate(context),
                provider=self.fallback.name,
                used_fallback=True,
                error="hosted_provider_not_configured",
            )

        try:
            response = self.provider.generate(context)
            return AIServiceResult(
                response=response,
                provider=self.provider.name,
                used_fallback=False,
            )
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, OSError) as exc:
            logger.warning("Hosted AI provider failed; using local fallback: %s", exc)
            return AIServiceResult(
                response=self.fallback.generate(context),
                provider=self.fallback.name,
                used_fallback=True,
                error=exc.__class__.__name__,
            )
