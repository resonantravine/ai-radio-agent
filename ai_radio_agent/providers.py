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
        "user_profile": "A commuter interested in AI products, startups, and practical product logic.",
        "memory_context": "Yesterday the listener heard an episode about AI startups and kept thinking about long-term memory.",
        "duration_minutes": 2,
    },
    "episode_brief_agent": {
        "title": "Why do some AI hosts sound like they really understand you?",
        "listener_promise": "A short commute-friendly conversation explaining why AI radio can feel personal without exposing the internal pipeline.",
        "user_facing_topic": "An AI host feels like it understands you when it can continue yesterday's question in today's context.",
        "internal_pipeline_note": "Host scripts are generated internal artifacts for quality control, persona consistency, TTS segmentation, and audio rendering. The end user only provides topic, profile or memory context, and duration.",
        "target_duration_minutes": 2,
    },
    "segment_planner_agent": {
        "episode_duration_minutes": 2,
        "segments": [
            {
                "name": "Opening subway scenario",
                "target_duration_sec": 35,
                "goal": "Set up the 8 AM subway listening context and yesterday's AI startup memory.",
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
        "episode_theme": "Why do some AI hosts sound like they really understand you?",
        "why_this_fits": "It turns memory and personalization into a listener-facing radio topic about commute-time AI audio.",
        "candidate_topics": ["AI hosts", "long-term memory", "commute context", "personalized explanation", "controllable memory boundaries"],
    },
    "topic_planner": {
        "title": "Why do some AI hosts sound like they really understand you?",
        "angle": "Use a morning subway scene to explain how AI radio connects listening history, preferences, follow-up questions, and current context.",
        "segments": ["Morning subway opening", "Continue yesterday's AI startup question", "Recommendation versus long-term memory", "Memory boundaries: controllable, explainable, and deletable"],
        "target_takeaway": "A good AI host does not push more content. It reduces the listener's filtering cost and continues in the way they like to understand things.",
    },
    "broadcast_context_agent": {
        "time": "8:00 AM",
        "scene": "The listener is on the subway during a morning commute.",
        "previous_memory": "Yesterday the listener heard an episode about AI startups.",
        "today_continuation": "Instead of generic tech news, today's episode continues the listener's previous question: why are AI companies competing for long-term memory?",
        "listener_mood": "half-awake, curious, wants something useful but not too heavy",
        "opening_frame": "Good morning, welcome back. This one is for the subway: what does it actually mean for an AI host to understand you?",
    },
    "research_agent": {
        "key_points": [
            "A personalized AI radio experience should connect listening history, preferences, follow-up questions, and current context.",
            "Behavioral recommendation predicts what a user might click next; long-term memory helps continue an unfinished question over time.",
            "Good memory should be controllable, explainable, and easy to turn off.",
        ],
        "examples": ["The listener heard about AI startups yesterday; today the host continues with why AI companies care about memory."],
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
        "intro": "Open like a morning commute radio segment, then ask what it means for an AI host to really understand a listener.",
        "beats": [
            "Host A sets the subway scene and asks whether knowing the listener is more than a natural voice.",
            "Host B explains that good AI radio can continue yesterday's question instead of serving generic tech news.",
            "Host A challenges whether this is just a recommendation algorithm.",
            "Host B distinguishes short-term behavior prediction from long-term memory in everyday language.",
            "Host A asks the boundary question: what if it remembers too much?",
            "Host B explains controllable, explainable, easy-to-turn-off memory.",
        ],
        "transition_notes": ["Use quick responses for back-and-forth, longer pauses only after questions or section turns."],
        "outro": "End with the idea that the next AI audio experience should feel prepared for the listener, not just generated.",
    },
    "dialogue_planner_agent": {
        "episode_title": "Why do some AI hosts sound like they really understand you?",
        "turns": [
            {"speaker": "Host A", "conversational_function": "open with the subway scene and yesterday's memory", "emotional_tone": "warm, close, like starting the day with the listener", "responds_to": "broadcast context", "turn_type": "example"},
            {"speaker": "Host B", "conversational_function": "explain why continuity makes the host feel understanding", "emotional_tone": "calm and explanatory", "responds_to": "Host A commute scene", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "check whether understanding is deeper than topic labels", "emotional_tone": "lightly questioning", "responds_to": "Host B continuity point", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "explain understanding style instead of labels", "emotional_tone": "plain and grounded", "responds_to": "Host A label question", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "raise the ordinary recommendation challenge", "emotional_tone": "friendly skeptical", "responds_to": "Host B deeper understanding claim", "turn_type": "challenge"},
            {"speaker": "Host B", "conversational_function": "separate behavior recommendation from continuous memory", "emotional_tone": "patient explainer", "responds_to": "recommendation challenge", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "summarize the continuity idea in listener language", "emotional_tone": "recognizing the point", "responds_to": "Host B distinction", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "explain reduced filtering cost and morning context", "emotional_tone": "useful and warm", "responds_to": "Host A continuity summary", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "ask the discomfort boundary question", "emotional_tone": "thoughtful concern", "responds_to": "memory value", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "answer with controllable, explainable, deletable memory", "emotional_tone": "reassuring and careful", "responds_to": "boundary concern", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "turn the answer into a memorable phrase", "emotional_tone": "softly reflective", "responds_to": "Host B boundary answer", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "state the central ending insight", "emotional_tone": "settled and memorable", "responds_to": "Host A phrase", "turn_type": "ending"},
            {"speaker": "Host A", "conversational_function": "close with a light commuter-friendly takeaway", "emotional_tone": "gentle closing", "responds_to": "Host B ending insight", "turn_type": "ending"}
        ],
    },
    "dual_host_dialogue_writer": {
        "title": "Why do some AI hosts sound like they really understand you?",
        "lines": [
            {"host": "Host A", "line": "It is eight in the morning. You are on the subway, headphones on. Yesterday you listened to an episode about AI startups, and one phrase kept coming up: long-term memory. Today, when you open your AI radio, it does not hand you generic tech news. It continues yesterday's question: why are AI companies competing over long-term memory?"},
            {"host": "Host B", "line": "That moment matters. An AI host sounds like it understands you not just because the voice is natural, but because it knows where you left off yesterday and what you might still be thinking about today."},
            {"host": "Host A", "line": "So it is not as simple as knowing that I like tech news?"},
            {"host": "Host B", "line": "Right. That is only a label. A deeper kind of understanding is knowing how you like to enter a question. Maybe you do not want every AI headline. You care about why a product makes sense, what user need it answers, and how it differs from an ordinary tool."},
            {"host": "Host A", "line": "Let me ask the listener's question: isn't that just a regular recommendation algorithm? I clicked something, so it keeps pushing more of the same."},
            {"host": "Host B", "line": "A little, but not quite. Recommendation is often about behavior records: what you clicked, how long you stayed, what you skipped. Long-term memory is more like preserving a continuous line of thought: why you cared, where you last followed up, and how you prefer something to be explained."},
            {"host": "Host A", "line": "So a good AI host does not meet me from scratch every morning. It can move yesterday's conversation forward."},
            {"host": "Host B", "line": "Exactly. It is not just generating more content. It is reducing your filtering cost. On a morning commute, you do not want to explain again what you want to hear. It should already know that today's episode needs to be light, clear, but not shallow."},
            {"host": "Host A", "line": "But if it remembers too much, doesn't that start to feel uncomfortable?"},
            {"host": "Host B", "line": "It can. That is why good memory should never feel like secretly remembering everything. It should be controllable, explainable, and deletable. You should know why it recommended something, and you should decide what should not be remembered."},
            {"host": "Host A", "line": "So understanding you is not a kind of mystery. It is a kind of restraint."},
            {"host": "Host B", "line": "Yes. The next generation of AI hosts may not be defined by how human the voice sounds, but by whether it can catch the question you had not finished yesterday, at the right moment."},
            {"host": "Host A", "line": "Before the subway doors open, maybe that is today's line to keep: sounding like it understands you is not about talking all the time. It is about knowing where to continue."},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Warm observer who represents the listener's lived commute experience and asks natural questions.",
        "host_b_persona": "Calm explainer who explains product logic in everyday language and avoids jargon.",
        "style_rules": ["Sound like two hosts talking to a commuter", "Avoid internal agent names", "Use concrete scenes and callbacks", "Keep explanations plain and human"],
        "revised_lines": [
            {"host": "Host A", "line": "It is eight in the morning. You are on the subway, headphones on. Yesterday you listened to an episode about AI startups, and one phrase kept coming up: long-term memory. Today, when you open your AI radio, it does not hand you generic tech news. It continues yesterday's question: why are AI companies competing over long-term memory?"},
            {"host": "Host B", "line": "That moment matters. An AI host sounds like it understands you not just because the voice is natural, but because it knows where you left off yesterday and what you might still be thinking about today."},
            {"host": "Host A", "line": "So it is not as simple as knowing that I like tech news?"},
            {"host": "Host B", "line": "Right. That is only a label. A deeper kind of understanding is knowing how you like to enter a question. Maybe you do not want every AI headline. You care about why a product makes sense, what user need it answers, and how it differs from an ordinary tool."},
            {"host": "Host A", "line": "Let me ask the listener's question: isn't that just a regular recommendation algorithm? I clicked something, so it keeps pushing more of the same."},
            {"host": "Host B", "line": "A little, but not quite. Recommendation is often about behavior records: what you clicked, how long you stayed, what you skipped. Long-term memory is more like preserving a continuous line of thought: why you cared, where you last followed up, and how you prefer something to be explained."},
            {"host": "Host A", "line": "So a good AI host does not meet me from scratch every morning. It can move yesterday's conversation forward."},
            {"host": "Host B", "line": "Exactly. It is not just generating more content. It is reducing your filtering cost. On a morning commute, you do not want to explain again what you want to hear. It should already know that today's episode needs to be light, clear, but not shallow."},
            {"host": "Host A", "line": "But if it remembers too much, doesn't that start to feel uncomfortable?"},
            {"host": "Host B", "line": "It can. That is why good memory should never feel like secretly remembering everything. It should be controllable, explainable, and deletable. You should know why it recommended something, and you should decide what should not be remembered."},
            {"host": "Host A", "line": "So understanding you is not a kind of mystery. It is a kind of restraint."},
            {"host": "Host B", "line": "Yes. The next generation of AI hosts may not be defined by how human the voice sounds, but by whether it can catch the question you had not finished yesterday, at the right moment."},
            {"host": "Host A", "line": "Before the subway doors open, maybe that is today's line to keep: sounding like it understands you is not about talking all the time. It is about knowing where to continue."},
        ],
    },
    "quality_evaluator": {
        "score": 9,
        "strengths": ["Concrete commute scene", "Natural interruption", "Boundary question", "Clear user value"],
        "improvements": ["Future versions can add live user follow-up interaction"],
        "ready_for_tts": True,
    },
    "tts_export": {
        "episode_title": "Why do some AI hosts sound like they really understand you?",
        "tts_text": "It is eight in the morning. You are on the subway, headphones on. Yesterday you listened to an episode about AI startups, and one phrase kept coming up: long-term memory. Today, when you open your AI radio, it does not hand you generic tech news. It continues yesterday's question: why are AI companies competing over long-term memory?\n\nThat moment matters. An AI host sounds like it understands you not just because the voice is natural, but because it knows where you left off yesterday and what you might still be thinking about today.\n\nSo it is not as simple as knowing that I like tech news?\n\nRight. That is only a label. A deeper kind of understanding is knowing how you like to enter a question. Maybe you do not want every AI headline. You care about why a product makes sense, what user need it answers, and how it differs from an ordinary tool.\n\nLet me ask the listener's question: isn't that just a regular recommendation algorithm? I clicked something, so it keeps pushing more of the same.\n\nA little, but not quite. Recommendation is often about behavior records: what you clicked, how long you stayed, what you skipped. Long-term memory is more like preserving a continuous line of thought: why you cared, where you last followed up, and how you prefer something to be explained.\n\nSo a good AI host does not meet me from scratch every morning. It can move yesterday's conversation forward.\n\nExactly. It is not just generating more content. It is reducing your filtering cost. On a morning commute, you do not want to explain again what you want to hear. It should already know that today's episode needs to be light, clear, but not shallow.\n\nBut if it remembers too much, doesn't that start to feel uncomfortable?\n\nIt can. That is why good memory should never feel like secretly remembering everything. It should be controllable, explainable, and deletable. You should know why it recommended something, and you should decide what should not be remembered.\n\nSo understanding you is not a kind of mystery. It is a kind of restraint.\n\nYes. The next generation of AI hosts may not be defined by how human the voice sounds, but by whether it can catch the question you had not finished yesterday, at the right moment.\n\nBefore the subway doors open, maybe that is today's line to keep: sounding like it understands you is not about talking all the time. It is about knowing where to continue.",
        "voice_notes": ["Host A should sound warm, observant, and close to the listener.", "Host B should sound calm, grounded, and explanatory without sounding like a lecture."],
    },
}
