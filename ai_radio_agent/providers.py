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
    "user_episode_input": {
        "topic": "Why do some AI hosts sound like they really understand you?",
        "user_profile": "Yoli, a morning listener interested in AI products, startups, and practical product logic.",
        "memory_context": "Yesterday the listener heard an episode about AI startups where a founder described memory as the new onboarding layer for AI products.",
        "duration_minutes": 2,
    },
    "episode_brief_agent": {
        "title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "listener_promise": "A soft personal morning radio segment for breakfast at home that continues yesterday's unfinished AI startup question.",
        "user_facing_topic": "An AI host feels like it understands you when it can continue yesterday's question in today's context.",
        "internal_pipeline_note": "Host scripts are generated internal artifacts for quality control, persona consistency, TTS segmentation, and audio rendering. The end user only provides topic, profile or memory context, and duration.",
        "target_duration_minutes": 2,
    },
    "segment_planner_agent": {
        "episode_duration_minutes": 2,
        "segments": [
            {
                "name": "Opening breakfast ritual",
                "target_duration_sec": 35,
                "goal": "Set up the 8 AM kitchen breakfast context and yesterday's AI startup question.",
                "listener_value": "The listener immediately understands why this episode is personally relevant.",
            },
            {
                "name": "Memory versus recommendation",
                "target_duration_sec": 45,
                "goal": "Explain the difference between behavioral recommendation and long-term memory.",
                "listener_value": "The listener can describe why 'knowing me' is more than topic labels.",
            },
            {
                "name": "Boundary and closing takeaway",
                "target_duration_sec": 40,
                "goal": "Ask whether too much memory feels uncomfortable, then close with a controllable-memory principle.",
                "listener_value": "The listener leaves with a memorable line about knowing where to continue.",
            },
        ],
    },
    "user_preference_agent": {
        "listener_name": "Yoli",
        "preferred_topics": ["AI audio tools", "creative workflows", "agent evaluation"],
        "tone": "smart, warm, practical",
        "episode_length_minutes": 8,
        "avoid_topics": ["investment advice", "medical claims"],
    },
    "memory_agent": {
        "listener_summary": "A builder exploring audio-first AI agent portfolios.",
        "known_preferences": ["clear demos", "concrete workflows", "beginner-friendly code"],
        "recent_episode_memory": ["Yesterday's AI startup episode mentioned a founder calling memory the new onboarding layer for AI products."],
    },
    "recommendation_agent": {
        "episode_theme": "Why do some AI hosts sound like they really understand you?",
        "why_this_fits": "It turns memory and personalization into a listener-facing radio topic about a soft morning audio ritual.",
        "candidate_topics": ["AI hosts", "long-term memory", "breakfast context", "personalized explanation", "controllable memory boundaries"],
    },
    "topic_planner": {
        "title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "angle": "Use a soft morning coffee ritual and kitchen scene to explain how AI radio continues a listener's unfinished question.",
        "segments": ["Personal morning greeting", "Continue yesterday's AI startup detail about memory as onboarding", "Recommendation versus long-term memory", "Memory boundaries: controllable, explainable, and deletable"],
        "target_takeaway": "A good AI host does not push more content. It gently reduces the listener's filtering cost and knows where to continue.",
    },
    "broadcast_context_agent": {
        "time": "8:00 AM",
        "scene": "The listener is in a quiet kitchen preparing breakfast.",
        "previous_memory": "Yesterday the listener heard an episode about AI startups where a founder described memory as the new onboarding layer for AI products.",
        "today_continuation": "Instead of generic tech news, today's episode continues the listener's previous question: why are AI companies competing for long-term memory?",
        "listener_mood": "half-awake, curious, wants something useful but not too heavy",
        "opening_frame": "Good morning, Yoli. Your morning coffee is ready. Yesterday we left off with one question: why are AI companies competing for long-term memory?",
    },
    "research_agent": {
        "key_points": [
            "A personalized AI radio experience should connect listening history, preferences, follow-up questions, and current context.",
            "Behavioral recommendation predicts what a user might click next; long-term memory helps continue an unfinished question over time.",
            "Good memory should be controllable, explainable, and easy to turn off.",
        ],
        "examples": ["The listener heard a founder describe memory as the new onboarding layer for AI products; today the host continues with why AI companies care about memory."],
        "open_questions": ["How much memory feels helpful before it feels intrusive?"],
        "sources_to_check": ["Product memory settings", "recommendation system explanations", "AI audio product examples"],
    },
    "fact_check_agent": {
        "status": "pass",
        "verified_claims": ["The episode frames memory and recommendation as product concepts rather than making hard factual claims."],
        "risky_claims": [],
        "revision_notes": ["Keep claims general and user-experience focused; avoid naming specific companies unless researched."],
    },
    "script_outliner": {
        "intro": "Open with a soft personal morning greeting, then connect the quiet kitchen scene to yesterday's AI startup question.",
        "beats": [
            "Host A greets Yoli, sets the quiet kitchen scene, and names the remembered question from yesterday.",
            "Host B explains that good AI radio can continue yesterday's question instead of serving generic tech news.",
            "Host A names today's small question for the morning.",
            "Host A challenges whether this is just a recommendation algorithm.",
            "Host B distinguishes short-term behavior prediction from long-term memory in everyday language.",
            "Host A reflects the bookmark metaphor back in natural language.",
            "Host A asks the boundary question: what if it remembers too much?",
            "Host B explains controllable, explainable, easy-to-turn-off memory.",
        ],
        "transition_notes": ["Use quick responses for back-and-forth, longer pauses only after questions or section turns."],
        "outro": "End softly, like a morning thought before the coffee cools, without opening a new question.",
    },
    "dialogue_planner_agent": {
        "episode_title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "turns": [
            {"speaker": "Host A", "conversational_function": "open with a personal morning greeting", "emotional_tone": "soft, warm, like placing coffee beside the listener", "responds_to": "broadcast context", "turn_type": "example"},
            {"speaker": "Host A", "conversational_function": "set the quiet kitchen and breakfast scene", "emotional_tone": "slow and atmospheric", "responds_to": "morning greeting", "turn_type": "example"},
            {"speaker": "Host A", "conversational_function": "name yesterday's remembered question", "emotional_tone": "gentle continuity", "responds_to": "breakfast scene", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "gently explain why continuity can feel like understanding", "emotional_tone": "calm and unhurried", "responds_to": "Host A morning setup", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "name today's small question", "emotional_tone": "softly curious", "responds_to": "Host B continuity point", "turn_type": "question"},
            {"speaker": "Host A", "conversational_function": "check whether understanding is deeper than topic labels", "emotional_tone": "lightly questioning", "responds_to": "Host B continuity point", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "softly explain understanding style instead of labels", "emotional_tone": "plain, grounded, not lecture-like", "responds_to": "Host A label question", "turn_type": "clarification"},
            {"speaker": "Host B", "conversational_function": "complete the explanation with a softer product example", "emotional_tone": "plain and gentle", "responds_to": "Host B label distinction", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "raise the ordinary recommendation challenge", "emotional_tone": "friendly skeptical", "responds_to": "Host B deeper understanding claim", "turn_type": "challenge"},
            {"speaker": "Host B", "conversational_function": "separate behavior recommendation from continuous memory using a concrete metaphor", "emotional_tone": "patient explainer", "responds_to": "recommendation challenge", "turn_type": "clarification"},
            {"speaker": "Host B", "conversational_function": "extend the bookmark metaphor into memory value", "emotional_tone": "patient and concrete", "responds_to": "recommendation metaphor", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "reflect the bookmark metaphor back", "emotional_tone": "soft recognition", "responds_to": "Host B metaphor", "turn_type": "callback"},
            {"speaker": "Host A", "conversational_function": "express a lived breakfast-morning reaction", "emotional_tone": "recognizing the point from lived experience", "responds_to": "Host B distinction", "turn_type": "callback"},
            {"speaker": "Host A", "conversational_function": "summarize the continuity idea in morning language", "emotional_tone": "clear and personal", "responds_to": "Host A lived reaction", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "explain reduced filtering cost and morning context", "emotional_tone": "useful and warm", "responds_to": "Host A continuity summary", "turn_type": "clarification"},
            {"speaker": "Host B", "conversational_function": "make breakfast usefulness concrete", "emotional_tone": "soft and practical", "responds_to": "Host B quiet value", "turn_type": "example"},
            {"speaker": "Host A", "conversational_function": "ask the discomfort boundary question", "emotional_tone": "thoughtful concern", "responds_to": "memory value", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "answer with controllable, explainable, deletable memory", "emotional_tone": "reassuring and careful", "responds_to": "boundary concern", "turn_type": "clarification"},
            {"speaker": "Host B", "conversational_function": "clarify user control in simple language", "emotional_tone": "careful and reassuring", "responds_to": "Host B boundary answer", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "turn the answer into a memorable phrase", "emotional_tone": "softly reflective", "responds_to": "Host B boundary answer", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "state the central ending insight", "emotional_tone": "settled and memorable", "responds_to": "Host A phrase", "turn_type": "ending"},
            {"speaker": "Host A", "conversational_function": "close with a coffee-centered takeaway", "emotional_tone": "gentle closing", "responds_to": "Host B ending insight", "turn_type": "ending"},
            {"speaker": "Host A", "conversational_function": "land the final line", "emotional_tone": "quiet and complete", "responds_to": "Host A closing takeaway", "turn_type": "ending"}
        ],
    },
    "dual_host_dialogue_writer": {
        "title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "lines": [
            {"host": "Host A", "line": "Good morning, Yoli. Your morning coffee is ready."},
            {"host": "Host A", "line": "It is eight o'clock. The kitchen is still quiet. Water is warming, breakfast is slowly coming together, and the day has not fully opened yet."},
            {"host": "Host A", "line": "Yesterday's episode about AI startups left one small question on the table: why are so many AI companies suddenly competing for long-term memory?"},
            {"host": "Host B", "line": "Maybe we can think of it this way. An AI host does not feel personal only because the voice sounds natural. A smooth voice helps, of course. But the deeper feeling comes from continuity."},
            {"host": "Host A", "line": "So this morning, not another generic tech headline. Just one question to stay with for a few minutes: why do some AI hosts sound like they actually know where to continue?"},
            {"host": "Host A", "line": "I like that, but I am also a little unsure. Is this really more than knowing that I like tech news?"},
            {"host": "Host B", "line": "There is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question."},
            {"host": "Host B", "line": "Maybe you care less about every headline, and more about why a product begins to matter in someone's day."},
            {"host": "Host A", "line": "Let me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something yesterday, so today it gives me more of the same."},
            {"host": "Host B", "line": "A little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next."},
            {"host": "Host B", "line": "Long-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful."},
            {"host": "Host A", "line": "A bookmark inside a conversation. I like that."},
            {"host": "Host A", "line": "I feel that in the morning. Before the day gets noisy, I do not really want another feed to sort through."},
            {"host": "Host A", "line": "I want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning. It moves yesterday's conversation forward."},
            {"host": "Host B", "line": "Exactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing."},
            {"host": "Host B", "line": "While you are making breakfast, the show should not ask you to sort through ten headlines. It should offer one thread that is light enough to enter the day, but still worth thinking about."},
            {"host": "Host A", "line": "But if it remembers too much, doesn't that start to feel uncomfortable?"},
            {"host": "Host B", "line": "It can. So good memory should not feel like it is secretly collecting everything."},
            {"host": "Host B", "line": "It should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay."},
            {"host": "Host A", "line": "So understanding you is not a kind of mystery. It is a kind of restraint."},
            {"host": "Host B", "line": "Yes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday."},
            {"host": "Host A", "line": "Before the coffee cools, maybe that is today's first cup: sounding like it understands you is not about talking all the time."},
            {"host": "Host A", "line": "It is about knowing where to continue."},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Soft morning companion who represents Yoli's breakfast-at-home experience and asks natural questions.",
        "host_b_persona": "Calm thought organizer who explains product logic in everyday language and avoids jargon.",
        "style_rules": ["Sound like Yoli's personal morning radio, not a tech news show", "Avoid internal agent names", "Use concrete scenes and callbacks", "Keep explanations plain, soft, and human"],
        "revised_lines": [
            {"host": "Host A", "line": "Good morning, Yoli. Your morning coffee is ready."},
            {"host": "Host A", "line": "It is eight o'clock. The kitchen is still quiet. Water is warming, breakfast is slowly coming together, and the day has not fully opened yet."},
            {"host": "Host A", "line": "Yesterday's episode about AI startups left one small question on the table: why are so many AI companies suddenly competing for long-term memory?"},
            {"host": "Host B", "line": "Maybe we can think of it this way. An AI host does not feel personal only because the voice sounds natural. A smooth voice helps, of course. But the deeper feeling comes from continuity."},
            {"host": "Host A", "line": "So this morning, not another generic tech headline. Just one question to stay with for a few minutes: why do some AI hosts sound like they actually know where to continue?"},
            {"host": "Host A", "line": "I like that, but I am also a little unsure. Is this really more than knowing that I like tech news?"},
            {"host": "Host B", "line": "There is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question."},
            {"host": "Host B", "line": "Maybe you care less about every headline, and more about why a product begins to matter in someone's day."},
            {"host": "Host A", "line": "Let me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something yesterday, so today it gives me more of the same."},
            {"host": "Host B", "line": "A little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next."},
            {"host": "Host B", "line": "Long-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful."},
            {"host": "Host A", "line": "A bookmark inside a conversation. I like that."},
            {"host": "Host A", "line": "I feel that in the morning. Before the day gets noisy, I do not really want another feed to sort through."},
            {"host": "Host A", "line": "I want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning. It moves yesterday's conversation forward."},
            {"host": "Host B", "line": "Exactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing."},
            {"host": "Host B", "line": "While you are making breakfast, the show should not ask you to sort through ten headlines. It should offer one thread that is light enough to enter the day, but still worth thinking about."},
            {"host": "Host A", "line": "But if it remembers too much, doesn't that start to feel uncomfortable?"},
            {"host": "Host B", "line": "It can. So good memory should not feel like it is secretly collecting everything."},
            {"host": "Host B", "line": "It should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay."},
            {"host": "Host A", "line": "So understanding you is not a kind of mystery. It is a kind of restraint."},
            {"host": "Host B", "line": "Yes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday."},
            {"host": "Host A", "line": "Before the coffee cools, maybe that is today's first cup: sounding like it understands you is not about talking all the time."},
            {"host": "Host A", "line": "It is about knowing where to continue."},
        ],
    },
    "quality_evaluator": {
        "score": 9,
        "dialogue_liveliness_score": 9,
        "strengths": ["Soft personal morning greeting", "Specific remembered detail", "Host A lived reaction", "Host B metaphor", "Boundary question"],
        "improvements": ["Future versions can add live user follow-up interaction and even shorter spontaneous turns"],
        "ready_for_tts": True,
    },
    "tts_export": {
        "episode_title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "tts_text": "Good morning, Yoli. Your morning coffee is ready.\n\nIt is eight o'clock. The kitchen is still quiet. Water is warming, breakfast is slowly coming together, and the day has not fully opened yet.\n\nYesterday's episode about AI startups left one small question on the table: why are so many AI companies suddenly competing for long-term memory?\n\nMaybe we can think of it this way. An AI host does not feel personal only because the voice sounds natural. A smooth voice helps, of course. But the deeper feeling comes from continuity.\n\nSo this morning, not another generic tech headline. Just one question to stay with for a few minutes: why do some AI hosts sound like they actually know where to continue?\n\nI like that, but I am also a little unsure. Is this really more than knowing that I like tech news?\n\nThere is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question.\n\nMaybe you care less about every headline, and more about why a product begins to matter in someone's day.\n\nLet me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something yesterday, so today it gives me more of the same.\n\nA little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next.\n\nLong-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful.\n\nA bookmark inside a conversation. I like that.\n\nI feel that in the morning. Before the day gets noisy, I do not really want another feed to sort through.\n\nI want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning. It moves yesterday's conversation forward.\n\nExactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing.\n\nWhile you are making breakfast, the show should not ask you to sort through ten headlines. It should offer one thread that is light enough to enter the day, but still worth thinking about.\n\nBut if it remembers too much, doesn't that start to feel uncomfortable?\n\nIt can. So good memory should not feel like it is secretly collecting everything.\n\nIt should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay.\n\nSo understanding you is not a kind of mystery. It is a kind of restraint.\n\nYes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday.\n\nBefore the coffee cools, maybe that is today's first cup: sounding like it understands you is not about talking all the time.\n\nIt is about knowing where to continue.",
        "voice_notes": ["Host A should sound soft, observant, and close to Yoli without becoming overly intimate.", "Host B should sound calm, grounded, and clear without sounding like a lecturer."],
    },
}
