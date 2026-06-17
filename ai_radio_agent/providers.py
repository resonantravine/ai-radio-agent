from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from ai_radio_agent.moment_profiles import MOMENT_PROFILES


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        """Return a raw model response. The pipeline validates it against schema."""


class MockProvider(LLMProvider):
    name = "mock"

    def complete(self, *, agent_name: str, prompt: str, schema: type[BaseModel]) -> str:
        if agent_name == "user_episode_input":
            return json.dumps(_mock_user_episode_input(prompt), ensure_ascii=False)
        if agent_name == "moment_profile_agent":
            return json.dumps(_mock_moment_profile(prompt), ensure_ascii=False)
        if agent_name == "timely_context_agent":
            return json.dumps(_mock_timely_context(prompt), ensure_ascii=False)
        if agent_name == "episode_brief_agent":
            return json.dumps(_mock_episode_brief(prompt), ensure_ascii=False)
        if agent_name == "segment_planner_agent":
            response = _mock_segment_plan(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "topic_planner":
            response = _mock_topic_plan(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "broadcast_context_agent":
            response = _mock_broadcast_context(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "script_outliner":
            response = _mock_script_outline(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "dialogue_planner_agent":
            response = _mock_dialogue_plan(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "dual_host_dialogue_writer":
            response = _mock_dialogue_script(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "persona_agent":
            response = _mock_persona_notes(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
        if agent_name == "quality_evaluator":
            return json.dumps(_mock_quality_evaluation(prompt), ensure_ascii=False)
        if agent_name == "tts_export":
            response = _mock_tts_export(prompt)
            if response is not None:
                return json.dumps(response, ensure_ascii=False)
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
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.types.GenerateContentConfig(
                    system_instruction="Return only JSON matching the requested schema. No markdown.",
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            message = str(exc)
            if "FAILED_PRECONDITION" in message and "location is not supported" in message:
                raise RuntimeError(
                    "Gemini API request was rejected because the current user location is not supported "
                    "for Google Generative Language API use. Try mock mode, OpenAI mode, or a Gemini API "
                    "account/network location that is supported by Google."
                ) from exc
            raise
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


def _detect_moment(prompt: str) -> str:
    lowered = prompt.lower()
    for moment in ("breakfast", "lunch", "dinner"):
        if f'"moment": "{moment}"' in lowered or f"'moment': '{moment}'" in lowered:
            return moment
    return "breakfast"


def _mock_user_episode_input(prompt: str) -> dict[str, Any]:
    moment = _detect_moment(prompt)
    return {
        "topic": "Why do some AI hosts sound like they really understand you?",
        "user_profile": "Yoli, a listener interested in AI products, startups, and practical product logic.",
        "memory_context": "Yesterday the listener heard an episode about AI startups where a founder described memory as the new onboarding layer for AI products.",
        "duration_minutes": 2,
        "moment": moment,
    }


def _mock_moment_profile(prompt: str) -> dict[str, Any]:
    moment = _detect_moment(prompt)
    profile = MOMENT_PROFILES[moment]
    return {
        "moment": profile["moment"],
        "format_name": profile["format_name"],
        "core_operation": profile["core_operation"],
        "content_role": profile["content_role"],
        "listener_state": profile["listener_state"],
        "output_feeling": profile["output_feeling"],
        "style_rules": profile["style_rules"],
        "content_logic": profile["content_logic"],
        "research_policy": profile["research_policy"],
        "semantic_density": profile["semantic_density"],
    }


def _mock_timely_context(prompt: str) -> dict[str, Any]:
    moment = _detect_moment(prompt)
    if moment == "lunch":
        return {
            "freshness_required": True,
            "date": "2026-06-17",
            "topic": "Why do some AI hosts sound like they really understand you?",
            "verified_updates": [
                {
                    "claim": "Mock mode marks this as a placeholder update instead of live news.",
                    "source": "mock://timely-context",
                    "why_relevant": "It demonstrates that lunch episodes can require source-backed freshness without making unsourced claims.",
                }
            ],
            "do_not_claim": [
                "Do not present mock updates as real current news.",
                "Do not turn the brief into a generic trend roundup.",
            ],
            "briefing_angle": "For lunch, compress relevant updates into why this matters now.",
        }
    if moment == "dinner":
        return {
            "freshness_required": False,
            "date": "2026-06-17",
            "topic": "Why do some AI hosts sound like they really understand you?",
            "verified_updates": [],
            "do_not_claim": [
                "Do not introduce heavy new information at dinner.",
                "Do not create urgency or an afternoon task list.",
            ],
            "briefing_angle": "For dinner, transform the day's idea into a slower story or future image.",
        }
    return {
        "freshness_required": False,
        "date": "2026-06-17",
        "topic": "Why do some AI hosts sound like they really understand you?",
        "verified_updates": [],
        "do_not_claim": [
            "Do not imply this is breaking news.",
            "Do not claim industry-wide consensus without source-backed research.",
        ],
        "briefing_angle": "For breakfast, continue yesterday's memory question instead of turning the episode into a news brief.",
    }


def _mock_episode_brief(prompt: str) -> dict[str, Any]:
    moment = _detect_moment(prompt)
    profile = MOMENT_PROFILES[moment]
    return {
        "title": f"{profile['format_name']}: Why do some AI hosts sound like they really understand you?",
        "listener_promise": f"A {profile['output_feeling']} personal radio episode that uses the {profile['core_operation']} operation.",
        "user_facing_topic": "An AI host feels like it understands you when it can connect listening history, preferences, follow-up questions, and current context.",
        "internal_pipeline_note": "Host scripts are generated internal artifacts for quality control, persona consistency, TTS segmentation, and audio rendering. The end user only provides topic, profile or memory context, moment, and duration.",
        "target_duration_minutes": 2,
    }


def _mock_quality_evaluation(prompt: str) -> dict[str, Any]:
    moment = _detect_moment(prompt)
    profile = MOMENT_PROFILES[moment]
    freshness_score = 9 if moment == "lunch" else 8
    return {
        "score": 9,
        "dialogue_liveliness_score": 9,
        "moment_fit_score": 9,
        "content_operation": profile["core_operation"],
        "memory_use_score": 9,
        "freshness_relevance_score": freshness_score,
        "semantic_density": profile["semantic_density"],
        "risk_notes": [
            f"Keep this {moment} episode aligned with {profile['core_operation']} rather than drifting into a generic tech explainer."
        ],
        "strengths": ["Specific remembered detail", "Host A lived reaction", "Host B metaphor", "Moment-aware editorial logic"],
        "improvements": ["Future versions can generate separate polished mock scripts for lunch and dinner audio demos."],
        "ready_for_tts": True,
    }


LUNCH_LINES = [
    {"host": "Host A", "line": "It's Yoli's Midday Brief. Lunch is short, and your brain has too many tabs open."},
    {"host": "Host B", "line": "Let's close fourteen of them."},
    {"host": "Host A", "line": "Today, one stays open: why AI companies are racing toward long-term memory."},
    {"host": "Host A", "line": "It's midday, Yoli. Quick brief for the lunch walk: no fifteen-tab rabbit hole, I promise."},
    {"host": "Host B", "line": "A generous promise. Today's thread: why AI companies are suddenly obsessed with long-term memory."},
    {"host": "Host A", "line": "Right. Yesterday we heard that founder say memory is the new onboarding layer for AI products."},
    {"host": "Host B", "line": "And that line stuck because it means the first minute of using an AI product is changing."},
    {"host": "Host A", "line": "The first minute is underrated. That's usually when I'm either interested, or already annoyed."},
    {"host": "Host B", "line": "Exactly. Old onboarding says, tell me who you are. Memory says, I remember where we left off."},
    {"host": "Host A", "line": "That's the part I actually feel at lunch. I've got ten minutes, maybe half a sandwich, maybe one bar of signal. I don't want to re-explain my whole personality to a chatbot."},
    {"host": "Host B", "line": "That is the why now. AI tools are becoming more everyday: writing, search, notes, voice assistants, even personal radio. The more often we use them, the more annoying it feels when they start from zero."},
    {"host": "Host A", "line": "But wait. Isn't this just another recommendation system with a nicer haircut?"},
    {"host": "Host B", "line": "Close, but not quite."},
    {"host": "Host A", "line": "Okay, give me the lunch-walk version before the crosswalk changes."},
    {"host": "Host B", "line": "A recommendation system is like the lunch specials board. It says, people like you might want this."},
    {"host": "Host A", "line": "So, you clicked noodles once. Congratulations, you are noodle person forever."},
    {"host": "Host B", "line": "Exactly. Memory is different. Memory is someone remembering you only have ten minutes, you skipped coffee, and yesterday you were still thinking about one question."},
    {"host": "Host A", "line": "So recommendation guesses what I might pick."},
    {"host": "Host B", "line": "Yes. Memory helps the product understand what I'm trying to continue."},
    {"host": "Host A", "line": "That sounds useful. Also, a little too close to my business."},
    {"host": "Host B", "line": "That's the tradeoff. Good memory saves time. Bad memory starts quietly steering the room."},
    {"host": "Host A", "line": "So what happens if memory starts shaping too much of what I hear?"},
    {"host": "Host B", "line": "Then it needs brakes. You should be able to see what it remembered, edit it, pause it, or delete it."},
    {"host": "Host A", "line": "So not, trust me, I know you."},
    {"host": "Host B", "line": "Right. More like, here's what I'm using, and you can change it."},
    {"host": "Host A", "line": "So the race is not just who remembers more."},
    {"host": "Host B", "line": "It's who remembers with restraint."},
    {"host": "Host A", "line": "Honestly, that's a good line for people too."},
    {"host": "Host B", "line": "Very strong lunch wisdom. Almost suspiciously useful."},
    {"host": "Host A", "line": "So this afternoon, maybe the question is: what would you want an AI to remember because it helps you continue?"},
    {"host": "Host A", "line": "And what should it forget, so you still feel free?"},
    {"host": "Host B", "line": "So that's the useful line for the afternoon: not who remembers more, but who remembers with restraint."},
    {"host": "Host A", "line": "Take that one with you. And maybe close a few tabs before your next meeting."},
    {"host": "Host B", "line": "Emotionally, or literally."},
    {"host": "Host A", "line": "Both count."},
]


def _mock_segment_plan(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "episode_duration_minutes": 2,
        "segments": [
            {
                "name": "Midday framing",
                "target_duration_sec": 25,
                "goal": "Start quickly and connect yesterday's memory phrase to today's lunch brief.",
                "listener_value": "Yoli immediately knows why this brief matters now.",
            },
            {
                "name": "Why now",
                "target_duration_sec": 30,
                "goal": "Compress why long-term memory matters as AI tools become everyday companions.",
                "listener_value": "The listener gets a useful midday explanation without a long setup.",
            },
            {
                "name": "Recommendation versus memory",
                "target_duration_sec": 35,
                "goal": "Use a concrete lunch metaphor to separate recommendation from memory.",
                "listener_value": "The distinction becomes memorable and easy to repeat.",
            },
            {
                "name": "Boundary and afternoon takeaway",
                "target_duration_sec": 30,
                "goal": "Name the discomfort boundary and close with a practical afternoon question.",
                "listener_value": "The listener leaves with a clear frame: useful memory requires restraint.",
            },
        ],
    }


def _mock_topic_plan(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "title": "Yoli's Midday Brief: Why AI memory matters now",
        "angle": "Compress yesterday's AI startup memory thread into a short lunch-walk distinction between recommendation and long-term memory.",
        "segments": [
            "Quick midday opening",
            "Why memory matters now for everyday AI tools",
            "Lunch specials board metaphor for recommendation versus memory",
            "Visible, editable, pausable, deletable memory",
            "Afternoon framing question",
        ],
        "target_takeaway": "The race is not just who remembers more; it is who remembers with the most restraint.",
    }


def _mock_broadcast_context(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "time": "12:30 PM",
        "scene": "Yoli is busy, between tasks, wearing earbuds during lunch or a short walk.",
        "previous_memory": "Yesterday the listener heard an episode about AI startups where a founder described memory as the new onboarding layer for AI products.",
        "today_continuation": "Today's brief compresses that memory question into why AI companies are racing toward long-term memory now.",
        "listener_mood": "busy, practical, wants useful clarity without a long setup",
        "opening_frame": "It's midday, Yoli. Quick brief for the lunch walk.",
    }


def _mock_script_outline(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "intro": "Open quickly with midday energy and recall the phrase memory as the new onboarding layer.",
        "beats": [
            "Name the lunch brief topic: why AI companies are racing toward long-term memory.",
            "Connect the previous memory to today's why-now question.",
            "Give Host A a lived midday reaction: not wanting to explain herself again.",
            "Use the lunch specials board metaphor to separate recommendation from memory.",
            "Ask the boundary question about memory shaping too much of what the listener hears.",
            "Answer with visible, editable, pausable, deletable memory.",
            "Close with one practical afternoon framing question.",
        ],
        "transition_notes": ["Keep turns short and useful.", "Use slightly longer pauses after the challenge, boundary question, and final takeaway."],
        "outro": "Close cleanly with the Midday Brief identity and a light return to the afternoon.",
    }


def _mock_dialogue_plan(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    tones = {
        "Host A": "warm, practical, lightly brisk",
        "Host B": "calm, clear, concise",
    }
    return {
        "episode_title": "Yoli's Midday Brief: Why AI memory matters now",
        "turns": [
            {
                "speaker": line["host"],
                "conversational_function": _lunch_turn_function(index, line["line"]),
                "emotional_tone": tones[line["host"]],
                "responds_to": "previous turn or lunch moment context",
                "turn_type": _lunch_turn_type(index, line["line"], len(LUNCH_LINES)),
            }
            for index, line in enumerate(LUNCH_LINES)
        ],
    }


def _lunch_turn_type(index: int, line: str, total: int) -> str:
    if index >= total - 4:
        return "ending"
    if "isn't this just another recommendation" in line.lower():
        return "challenge"
    if "?" in line:
        return "question"
    if any(marker in line.lower() for marker in ["lunch specials board", "noodle person", "ten minutes"]):
        return "example"
    if any(marker in line.lower() for marker in ["yesterday", "where we left off", "that's the part", "race is not"]):
        return "callback"
    if index < 3:
        return "example"
    return "clarification"


def _lunch_turn_function(index: int, line: str) -> str:
    functions = [
        "open with a quick lunch-walk greeting",
        "name today's compressed thread",
        "recall the specific remembered detail from yesterday",
        "explain why the remembered phrase matters",
        "invite a plain-language explanation",
        "answer with the start-over problem",
        "express lived midday friction",
        "explain why memory matters now for everyday AI tools",
        "raise the recommendation challenge",
        "acknowledge the overlap without flattening the distinction",
        "ask for the compressed version",
        "introduce the lunch specials board metaphor",
        "prompt the memory side of the metaphor",
        "make memory concrete in the listener's day",
        "check understanding",
        "state the distinction",
        "name the usefulness and discomfort",
        "confirm the central tension",
        "explain the time-saving upside",
        "explain the shaping-risk downside",
        "ask the boundary question",
        "answer with user control",
        "summarize the race as restraint, not volume",
        "land the main takeaway",
        "reflect the takeaway",
        "give the afternoon framing question",
        "add the freedom-side question",
        "close the show identity",
        "return the listener to the afternoon",
    ]
    return functions[index] if index < len(functions) else line[:80]


def _mock_dialogue_script(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "title": "Yoli's Midday Brief: Why AI memory matters now",
        "lines": LUNCH_LINES,
    }


def _mock_persona_notes(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "host_a_persona": "Warm, practical lunch-walk companion who represents Yoli's lived midday friction.",
        "host_b_persona": "Calm, concise explainer who compresses product logic into everyday language.",
        "style_rules": [
            "Start quickly, but not anxiously.",
            "Keep turns shorter than breakfast.",
            "Explain why this matters now.",
            "Avoid generic tech news voice.",
            "Keep the recommendation-versus-memory distinction concrete.",
        ],
        "revised_lines": LUNCH_LINES,
    }


def _mock_tts_export(prompt: str) -> dict[str, Any] | None:
    if _detect_moment(prompt) != "lunch":
        return None
    return {
        "episode_title": "Yoli's Midday Brief: Why AI memory matters now",
        "tts_text": "\n\n".join(line["line"] for line in LUNCH_LINES),
        "voice_notes": [
            "Host A should sound warm, practical, and lightly brisk, like someone walking with the listener during lunch.",
            "Host B should sound calm, concise, and grounded, with no lecture tone.",
        ],
    }


MOCK_RESPONSES: dict[str, dict[str, Any]] = {
    "user_episode_input": {
        "topic": "Why do some AI hosts sound like they really understand you?",
        "user_profile": "Yoli, a morning listener interested in AI products, startups, and practical product logic.",
        "memory_context": "Yesterday the listener heard an episode about AI startups where a founder described memory as the new onboarding layer for AI products.",
        "duration_minutes": 2,
        "moment": "breakfast",
    },
    "moment_profile_agent": {
        "moment": "breakfast",
        "format_name": "Yoli's Morning Coffee",
        "core_operation": "continue",
        "content_role": "continue yesterday's unfinished question and offer one useful thread",
        "listener_state": "half-awake, beginning the day",
        "output_feeling": "gentle continuity",
        "style_rules": [
            "Begin gently. No hard headline opening.",
            "Use one remembered detail from the previous episode.",
            "Offer only one useful thread, not a list of topics.",
            "Keep semantic density low to medium.",
            "Make the listener feel: I do not need to start from zero today.",
            "Avoid news-anchor tone, productivity coaching, and over-explaining.",
        ],
        "content_logic": "memory -> small question -> one useful distinction -> soft takeaway",
        "research_policy": "Do not search unless the topic requires factual verification.",
        "semantic_density": "low_to_medium",
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
    "timely_context_agent": {
        "freshness_required": False,
        "date": "2026-06-17",
        "topic": "Why do some AI hosts sound like they really understand you?",
        "verified_updates": [],
        "do_not_claim": [
            "Do not imply this is breaking news.",
            "Do not claim industry-wide consensus without source-backed research.",
        ],
        "briefing_angle": "For breakfast, continue yesterday's memory question instead of turning the episode into a news brief.",
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
            {"host": "Host A", "line": "Good morning, Yoli."},
            {"host": "Host B", "line": "Good morning. I'm already in the kitchen."},
            {"host": "Host A", "line": "What does it feel like there this morning?"},
            {"host": "Host B", "line": "Warm, a little messy, and very alive. There's toast on the counter, coffee starting to bubble, and someone just opened the window. You can hear the street waking up outside."},
            {"host": "Host A", "line": "That sounds like exactly where we should begin."},
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
            {"host": "Host A", "line": "That feels like a good place to leave the morning."},
            {"host": "Host B", "line": "The coffee's still warm, the toast is almost gone, and the day is just getting started."},
            {"host": "Host A", "line": "Thanks for spending breakfast with us."},
            {"host": "Host B", "line": "We'll be here again soon."},
            {"host": "Host A", "line": "Until then, take it slow."},
            {"host": "Host A", "line": "This has been Breakfast. Thanks for listening."},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Soft morning companion who represents Yoli's breakfast-at-home experience and asks natural questions.",
        "host_b_persona": "Calm thought organizer who explains product logic in everyday language and avoids jargon.",
        "style_rules": ["Sound like Yoli's personal morning radio, not a tech news show", "Avoid internal agent names", "Use concrete scenes and callbacks", "Keep explanations plain, soft, and human"],
        "revised_lines": [
            {"host": "Host A", "line": "Good morning, Yoli."},
            {"host": "Host B", "line": "Good morning. I'm already in the kitchen."},
            {"host": "Host A", "line": "What does it feel like there this morning?"},
            {"host": "Host B", "line": "Warm, a little messy, and very alive. There's toast on the counter, coffee starting to bubble, and someone just opened the window. You can hear the street waking up outside."},
            {"host": "Host A", "line": "That sounds like exactly where we should begin."},
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
            {"host": "Host A", "line": "That feels like a good place to leave the morning."},
            {"host": "Host B", "line": "The coffee's still warm, the toast is almost gone, and the day is just getting started."},
            {"host": "Host A", "line": "Thanks for spending breakfast with us."},
            {"host": "Host B", "line": "We'll be here again soon."},
            {"host": "Host A", "line": "Until then, take it slow."},
            {"host": "Host A", "line": "This has been Breakfast. Thanks for listening."},
        ],
    },
    "quality_evaluator": {
        "score": 9,
        "dialogue_liveliness_score": 9,
        "moment_fit_score": 9,
        "content_operation": "continue",
        "memory_use_score": 9,
        "freshness_relevance_score": 8,
        "semantic_density": "low_to_medium",
        "risk_notes": ["Avoid sounding like a generic tech news brief; this breakfast moment should pick up yesterday's thread."],
        "strengths": ["Soft personal morning greeting", "Specific remembered detail", "Host A lived reaction", "Host B metaphor", "Boundary question"],
        "improvements": ["Future versions can add live user follow-up interaction and even shorter spontaneous turns"],
        "ready_for_tts": True,
    },
    "tts_export": {
        "episode_title": "Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?",
        "tts_text": "Good morning, Yoli.\n\nGood morning. I'm already in the kitchen.\n\nWhat does it feel like there this morning?\n\nWarm, a little messy, and very alive. There's toast on the counter, coffee starting to bubble, and someone just opened the window. You can hear the street waking up outside.\n\nThat sounds like exactly where we should begin.\n\nYesterday's episode about AI startups left one small question on the table: why are so many AI companies suddenly competing for long-term memory?\n\nMaybe we can think of it this way. An AI host does not feel personal only because the voice sounds natural. A smooth voice helps, of course. But the deeper feeling comes from continuity.\n\nSo this morning, not another generic tech headline. Just one question to stay with for a few minutes: why do some AI hosts sound like they actually know where to continue?\n\nI like that, but I am also a little unsure. Is this really more than knowing that I like tech news?\n\nThere is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question.\n\nMaybe you care less about every headline, and more about why a product begins to matter in someone's day.\n\nLet me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something yesterday, so today it gives me more of the same.\n\nA little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next.\n\nLong-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful.\n\nA bookmark inside a conversation. I like that.\n\nI feel that in the morning. Before the day gets noisy, I do not really want another feed to sort through.\n\nI want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning. It moves yesterday's conversation forward.\n\nExactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing.\n\nWhile you are making breakfast, the show should not ask you to sort through ten headlines. It should offer one thread that is light enough to enter the day, but still worth thinking about.\n\nBut if it remembers too much, doesn't that start to feel uncomfortable?\n\nIt can. So good memory should not feel like it is secretly collecting everything.\n\nIt should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay.\n\nSo understanding you is not a kind of mystery. It is a kind of restraint.\n\nYes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday.\n\nThat feels like a good place to leave the morning.\n\nThe coffee's still warm, the toast is almost gone, and the day is just getting started.\n\nThanks for spending breakfast with us.\n\nWe'll be here again soon.\n\nUntil then, take it slow.\n\nThis has been Breakfast. Thanks for listening.",
        "voice_notes": ["Host A should sound soft, observant, and close to Yoli without becoming overly intimate.", "Host B should sound calm, grounded, and clear without sounding like a lecturer."],
    },
}
