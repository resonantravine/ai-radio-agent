from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        """Return a raw model response. The pipeline validates it against schema."""


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        data = MOCK_RESPONSES[agent_name]
        return json.dumps(data, ensure_ascii=False)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install OpenAI support with: pip install -e '.[openai]'") from exc

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("LLM_MODEL", "gpt-4.1-mini")

    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "Return only JSON matching the requested schema. No markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": True,
                }
            },
        )
        return response.output_text


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model: str | None = None) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("Install Gemini support with: pip install -e '.[gemini]'") from exc

        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.types = types
        self.model = model or os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")

    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                system_instruction="Return only JSON matching the requested schema. No markdown.",
                response_mime_type="application/json",
            ),
        )
        return response.text or ""


def get_provider(provider_name: str | None = None) -> LLMProvider:
    selected = (provider_name or os.getenv("LLM_PROVIDER", "mock")).lower()
    if selected == "mock":
        return MockProvider()
    if selected == "openai":
        return OpenAIProvider()
    if selected == "gemini":
        return GeminiProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER={selected!r}. Use mock, openai, or gemini.")


MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "user_preference_agent": {
        "listener_name": "Marta",
        "preferred_topics": ["AI audio tools", "creative workflows", "agent evaluation"],
        "tone": "smart, warm, practical",
        "episode_length_minutes": 8,
        "avoid_topics": ["investment advice", "medical claims"],
    },
    "memory_agent": {
        "listener_summary": "A builder exploring audio-first AI agent portfolios.",
        "known_preferences": ["clear demos", "concrete workflows", "beginner-friendly code"],
        "recent_episode_memory": ["Liked a prior episode about prompt evaluation loops."],
    },
    "recommendation_agent": {
        "episode_theme": "Why personalized AI radio feels less random and more useful",
        "why_this_fits": "It turns the technical pipeline into a listener-friendly story about better audio recommendations.",
        "candidate_topics": ["listening habits", "personalized explanations", "AI radio hosts", "daily commute content"],
    },
    "topic_planner": {
        "title": "When AI Radio Starts To Know Your Taste",
        "angle": "Discuss how personalized AI audio can feel more like a thoughtful host than a random feed.",
        "segments": ["The shift from random content to remembered taste", "Why context matters", "How good explanations feel personal", "The line between helpful and intrusive"],
        "target_takeaway": "The future of AI radio is not just generated speech; it is relevant, well-timed explanation.",
    },
    "research_agent": {
        "key_points": [
            "Memory improves personalization when it is explicit and reviewable.",
            "Fact checking should happen before a script reaches voice generation.",
            "Dialogue format makes the final TTS handoff easier to inspect.",
        ],
        "examples": ["A two-host explainer can contrast builder and listener perspectives."],
        "open_questions": ["Which TTS provider best fits the target voice style?"],
        "sources_to_check": ["Provider docs", "product pricing pages", "job description requirements"],
    },
    "fact_check_agent": {
        "status": "pass",
        "verified_claims": ["The pipeline separates planning, research, writing, and evaluation."],
        "risky_claims": [],
        "revision_notes": ["Avoid provider pricing claims unless checked on the day of use."],
    },
    "script_outliner": {
        "intro": "Open with the idea that AI radio is becoming less random and more aware of listener taste.",
        "beats": [
            "Host A notices that AI hosts can learn what kind of content feels relevant.",
            "Host B gives a commute example about AI products and business technology.",
            "Both hosts discuss how personalization should improve explanations, not become creepy.",
        ],
        "transition_notes": ["Keep the rhythm conversational and curious."],
        "outro": "Close with the idea that the best AI radio feels like it prepared for this listener today.",
    },
    "dual_host_dialogue_writer": {
        "title": "When AI Radio Starts To Know Your Taste",
        "lines": [
            {"host": "Host A", "line": "Have you noticed that some AI hosts are starting to feel less random?"},
            {"host": "Host B", "line": "Yes. The good ones sound like they know what kind of day you are having."},
            {"host": "Host A", "line": "Exactly. If you always listen to AI products and business technology on your commute, the next episode should not be generic tech news."},
            {"host": "Host B", "line": "It should understand that you care about the product logic behind the story, not just the headline."},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Curious technical producer who explains the system clearly.",
        "host_b_persona": "Friendly listener advocate who asks practical questions.",
        "style_rules": ["Keep lines short", "Avoid hype", "Sound like a natural radio conversation for curious listeners"],
        "revised_lines": [
            {"host": "Host A", "line": "Have you noticed that some AI hosts are starting to feel less random?"},
            {"host": "Host B", "line": "Yes. The good ones sound like they know what kind of day you are having."},
            {"host": "Host A", "line": "If you listen to AI products and business technology on your commute, the next episode should not be generic tech news."},
            {"host": "Host B", "line": "It should know you care about the product logic behind the story, not just the headline."},
            {"host": "Host A", "line": "That is where personalization gets interesting. The voice is only the surface."},
            {"host": "Host B", "line": "The real value is that it remembers your listening habits, your questions, and the way you like things explained."},
            {"host": "Host A", "line": "And when it works, it feels less like a feed and more like a host who prepared for you."},
            {"host": "Host B", "line": "That is the kind of AI radio I would actually come back to tomorrow."},
        ],
    },
    "quality_evaluator": {
        "score": 9,
        "strengths": ["Clear pipeline", "Good portfolio mapping", "TTS-ready dialogue"],
        "improvements": ["Add real web research in a future version"],
        "ready_for_tts": True,
    },
    "tts_export": {
        "episode_title": "When AI Radio Starts To Know Your Taste",
        "tts_text": "Have you noticed that some AI hosts are starting to feel less random?\n\nYes. The good ones sound like they know what kind of day you are having.\n\nIf you listen to AI products and business technology on your commute, the next episode should not be generic tech news.\n\nIt should know you care about the product logic behind the story, not just the headline.\n\nThat is where personalization gets interesting. The voice is only the surface.\n\nThe real value is that it remembers your listening habits, your questions, and the way you like things explained.\n\nAnd when it works, it feels less like a feed and more like a host who prepared for you.\n\nThat is the kind of AI radio I would actually come back to tomorrow.",
        "voice_notes": ["Use a warm explainer voice for Host A", "Use an inquisitive co-host voice for Host B"],
    },
}
