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
        "episode_theme": "为什么有些 AI 主播听起来像真的懂你？",
        "why_this_fits": "It turns memory and personalization into a listener-facing radio topic about commute-time AI audio.",
        "candidate_topics": ["AI 主播", "长期记忆", "通勤场景", "个性化解释", "可控的记忆边界"],
    },
    "topic_planner": {
        "title": "为什么有些 AI 主播听起来像真的懂你？",
        "angle": "Use a morning subway scene to explain how AI radio connects listening history, preferences, follow-up questions, and current context.",
        "segments": ["早上地铁里的开场", "接着昨天 AI 创业话题继续讲", "普通推荐和长期记忆的区别", "记忆边界：可控、可解释、可关闭"],
        "target_takeaway": "好的 AI 主播不是推更多内容，而是减少听众的筛选成本，并用听众喜欢的方式继续解释世界。",
    },
    "broadcast_context_agent": {
        "time": "8:00 AM",
        "scene": "The listener is on the subway during a morning commute.",
        "previous_memory": "Yesterday the listener heard an episode about AI startups.",
        "today_continuation": "Instead of generic tech news, today's episode continues the listener's previous question: why are AI companies competing for long-term memory?",
        "listener_mood": "half-awake, curious, wants something useful but not too heavy",
        "opening_frame": "早上好，欢迎回来。今天这段适合在地铁上听：一个 AI 主播，到底怎样才算真的懂你？",
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
        "episode_title": "为什么有些 AI 主播听起来像真的懂你？",
        "turns": [
            {"speaker": "Host A", "conversational_function": "open the morning commute scene", "emotional_tone": "warm, close, lightly sleepy", "responds_to": "broadcast opening", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "answer with the core difference between voice and continuity", "emotional_tone": "calm and concise", "responds_to": "Host A opening question", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "make the idea concrete through yesterday's episode", "emotional_tone": "curious recognition", "responds_to": "Host B continuity point", "turn_type": "example"},
            {"speaker": "Host B", "conversational_function": "explain continuation instead of generic news", "emotional_tone": "plainspoken explainer", "responds_to": "yesterday memory example", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "challenge with the ordinary recommendation question", "emotional_tone": "skeptical but friendly", "responds_to": "personalization claim", "turn_type": "challenge"},
            {"speaker": "Host B", "conversational_function": "distinguish behavioral recommendation from long-term memory", "emotional_tone": "patient and grounded", "responds_to": "recommendation challenge", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "reflect the phrase listening style back", "emotional_tone": "interested", "responds_to": "memory distinction", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "give a mini case about skipping macro news and finishing AI voice content", "emotional_tone": "concrete and useful", "responds_to": "listening style callback", "turn_type": "example"},
            {"speaker": "Host A", "conversational_function": "connect the example to reduced filtering cost", "emotional_tone": "relieved", "responds_to": "mini case", "turn_type": "clarification"},
            {"speaker": "Host B", "conversational_function": "explain user value in everyday terms", "emotional_tone": "warm explainer", "responds_to": "filtering cost point", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "ask the boundary question about discomfort", "emotional_tone": "thoughtful concern", "responds_to": "memory value", "turn_type": "question"},
            {"speaker": "Host B", "conversational_function": "answer with controllable, explainable, easy-to-turn-off memory", "emotional_tone": "reassuring", "responds_to": "boundary concern", "turn_type": "clarification"},
            {"speaker": "Host A", "conversational_function": "bring it back to the subway listener", "emotional_tone": "intimate and practical", "responds_to": "memory boundary answer", "turn_type": "callback"},
            {"speaker": "Host B", "conversational_function": "close with the episode's central takeaway", "emotional_tone": "settled and memorable", "responds_to": "subway callback", "turn_type": "ending"}
        ],
    },
    "dual_host_dialogue_writer": {
        "title": "为什么有些 AI 主播听起来像真的懂你？",
        "lines": [
            {"host": "Host A", "line": "早上好，欢迎回来。今天这段，适合在地铁上听。我们聊一个有点微妙的问题：一个 AI 主播，到底怎样才算真的懂你？"},
            {"host": "Host B", "line": "我觉得不只是声音自然。更关键的是，它能不能接住你昨天还没想完的问题。"},
            {"host": "Host A", "line": "比如昨天我刚听完一期 AI 创业节目，里面一直在讲公司为什么都在争长期记忆。今天我打开电台，它没有给我一段泛泛的科技新闻。"},
            {"host": "Host B", "line": "对，它像是在接着昨天的问题继续讲。不是从零开始，也不是把热门新闻重新洗一遍。"},
            {"host": "Host A", "line": "那我替听众问一句：这不就是普通推荐算法吗？"},
            {"host": "Host B", "line": "有点像，但不完全一样。普通推荐更像看你刚刚点了什么，然后猜下一个你会点什么。长期记忆更像记住你为什么会关心这件事。"},
            {"host": "Host A", "line": "所以它记住的不是我的标签，而是我理解问题的方式。"},
            {"host": "Host B", "line": "对。比如你连续三天跳过宏观新闻，却听完了所有关于 AI voice 的内容。它不该只说，你喜欢 AI。它应该知道，你真正关心的是声音产品怎么形成陪伴感。"},
            {"host": "Host A", "line": "这样听起来，价值不是推更多内容，而是减少我的筛选成本。"},
            {"host": "Host B", "line": "没错。早上八点在地铁上，你可能不想重新选择二十条资讯。你只是想听到一个刚好接得上的解释。"},
            {"host": "Host A", "line": "可是，如果它记得太多，会不会让人不舒服？"},
            {"host": "Host B", "line": "会。所以好的记忆一定要可控、可解释，也要容易关掉。你应该知道它记住了什么，也能决定哪些不要继续用。"},
            {"host": "Host A", "line": "这样它才不像在偷偷观察你，而像一个有分寸的主播。"},
            {"host": "Host B", "line": "所以，下一代 AI 音频最重要的可能不是声音有多像人，而是它能不能逐渐学会用你喜欢的方式，陪你理解世界。"},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Warm observer who represents the listener's lived commute experience and asks natural questions.",
        "host_b_persona": "Calm explainer who explains product logic in everyday language and avoids jargon.",
        "style_rules": ["Sound like two hosts talking to a commuter", "Avoid internal agent names", "Use concrete scenes and callbacks", "Keep explanations plain and human"],
        "revised_lines": [
            {"host": "Host A", "line": "早上好，欢迎回来。今天这段，适合在地铁上听。我们聊一个有点微妙的问题：一个 AI 主播，到底怎样才算真的懂你？"},
            {"host": "Host B", "line": "我觉得不只是声音自然。更关键的是，它能不能接住你昨天还没想完的问题。"},
            {"host": "Host A", "line": "比如昨天我刚听完一期 AI 创业节目，里面一直在讲公司为什么都在争长期记忆。今天我打开电台，它没有给我一段泛泛的科技新闻。"},
            {"host": "Host B", "line": "对，它像是在接着昨天的问题继续讲。不是从零开始，也不是把热门新闻重新洗一遍。"},
            {"host": "Host A", "line": "那我替听众问一句：这不就是普通推荐算法吗？"},
            {"host": "Host B", "line": "有点像，但不完全一样。普通推荐更像看你刚刚点了什么，然后猜下一个你会点什么。长期记忆更像记住你为什么会关心这件事。"},
            {"host": "Host A", "line": "所以它记住的不是我的标签，而是我理解问题的方式。"},
            {"host": "Host B", "line": "对。比如你连续三天跳过宏观新闻，却听完了所有关于 AI voice 的内容。它不该只说，你喜欢 AI。它应该知道，你真正关心的是声音产品怎么形成陪伴感。"},
            {"host": "Host A", "line": "这样听起来，价值不是推更多内容，而是减少我的筛选成本。"},
            {"host": "Host B", "line": "没错。早上八点在地铁上，你可能不想重新选择二十条资讯。你只是想听到一个刚好接得上的解释。"},
            {"host": "Host A", "line": "可是，如果它记得太多，会不会让人不舒服？"},
            {"host": "Host B", "line": "会。所以好的记忆一定要可控、可解释，也要容易关掉。你应该知道它记住了什么，也能决定哪些不要继续用。"},
            {"host": "Host A", "line": "这样它才不像在偷偷观察你，而像一个有分寸的主播。"},
            {"host": "Host B", "line": "所以，下一代 AI 音频最重要的可能不是声音有多像人，而是它能不能逐渐学会用你喜欢的方式，陪你理解世界。"},
        ],
    },
    "quality_evaluator": {
        "score": 9,
        "strengths": ["Concrete commute scene", "Natural interruption", "Boundary question", "Clear user value"],
        "improvements": ["Future versions can add live user follow-up interaction"],
        "ready_for_tts": True,
    },
    "tts_export": {
        "episode_title": "为什么有些 AI 主播听起来像真的懂你？",
        "tts_text": "早上好，欢迎回来。今天这段，适合在地铁上听。我们聊一个有点微妙的问题：一个 AI 主播，到底怎样才算真的懂你？\n\n我觉得不只是声音自然。更关键的是，它能不能接住你昨天还没想完的问题。\n\n比如昨天我刚听完一期 AI 创业节目，里面一直在讲公司为什么都在争长期记忆。今天我打开电台，它没有给我一段泛泛的科技新闻。\n\n对，它像是在接着昨天的问题继续讲。不是从零开始，也不是把热门新闻重新洗一遍。\n\n那我替听众问一句：这不就是普通推荐算法吗？\n\n有点像，但不完全一样。普通推荐更像看你刚刚点了什么，然后猜下一个你会点什么。长期记忆更像记住你为什么会关心这件事。\n\n所以它记住的不是我的标签，而是我理解问题的方式。\n\n对。比如你连续三天跳过宏观新闻，却听完了所有关于 AI voice 的内容。它不该只说，你喜欢 AI。它应该知道，你真正关心的是声音产品怎么形成陪伴感。\n\n这样听起来，价值不是推更多内容，而是减少我的筛选成本。\n\n没错。早上八点在地铁上，你可能不想重新选择二十条资讯。你只是想听到一个刚好接得上的解释。\n\n可是，如果它记得太多，会不会让人不舒服？\n\n会。所以好的记忆一定要可控、可解释，也要容易关掉。你应该知道它记住了什么，也能决定哪些不要继续用。\n\n这样它才不像在偷偷观察你，而像一个有分寸的主播。\n\n所以，下一代 AI 音频最重要的可能不是声音有多像人，而是它能不能逐渐学会用你喜欢的方式，陪你理解世界。",
        "voice_notes": ["Host A should sound warm, observant, and close to the listener.", "Host B should sound calm, grounded, and explanatory without sounding like a lecture."],
    },
}
