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
        "title": "为什么有些 AI 主播听起来像真的懂你？",
        "lines": [
            {"host": "Host A", "line": "早上八点，你在地铁上，耳机刚戴好。昨天你听了一期 AI 创业的节目，里面一直提到一个词：长期记忆。今天你再打开 AI 电台，它没有给你推一条泛泛的科技新闻，而是接着昨天那个问题往下讲：为什么 AI 公司都在争长期记忆？"},
            {"host": "Host B", "line": "这个瞬间其实很关键。一个 AI 主播听起来像懂你，不只是因为它声音自然，而是因为它知道你昨天听到了哪里，今天可能还在想什么。"},
            {"host": "Host A", "line": "所以它懂的不是我喜欢科技新闻这么简单？"},
            {"host": "Host B", "line": "对。那只是标签。更深一点的理解是：你喜欢怎样进入一个问题。比如你不是想听所有 AI 新闻，你更关心一个产品为什么成立，背后的用户需求是什么，以及它和普通工具有什么区别。"},
            {"host": "Host A", "line": "那我替听众问一句：这不就是普通推荐算法吗？我点过什么，它就继续推什么。"},
            {"host": "Host B", "line": "有点像，但不完全一样。普通推荐更像看行为记录：你点了什么、停留多久、跳过了什么。长期记忆更像保存一条连续的思路：你为什么关心这个问题，你上次追问到哪里，你更喜欢被怎样解释。"},
            {"host": "Host A", "line": "也就是说，好的 AI 主播不是每天重新认识我一次，而是能接着昨天的对话往前走。"},
            {"host": "Host B", "line": "对。它不只是生成更多内容，而是减少你的筛选成本。早上通勤的时候，你不需要重新告诉它我想听什么。它已经知道，今天这段内容最好轻一点、清楚一点，但不要太浅。"},
            {"host": "Host A", "line": "可是，如果它记得太多，会不会让人有点不舒服？"},
            {"host": "Host B", "line": "会。所以真正好的记忆不应该是偷偷记住一切，而应该是可控的、可解释的、可以被删除的。你应该知道它为什么推荐这段内容，也能决定哪些东西不要被记住。"},
            {"host": "Host A", "line": "这样听起来，懂你不是一种神秘感，而是一种分寸感。"},
            {"host": "Host B", "line": "是的。未来的 AI 主播，最重要的可能不是声音多像真人，而是它能不能在合适的时候，接住你昨天还没想完的问题。"},
            {"host": "Host A", "line": "地铁到站之前，这也许就是今天最值得记住的一句话：真正像懂你，不是一直说，而是知道从哪里继续。"},
        ],
    },
    "persona_agent": {
        "host_a_persona": "Warm observer who represents the listener's lived commute experience and asks natural questions.",
        "host_b_persona": "Calm explainer who explains product logic in everyday language and avoids jargon.",
        "style_rules": ["Sound like two hosts talking to a commuter", "Avoid internal agent names", "Use concrete scenes and callbacks", "Keep explanations plain and human"],
        "revised_lines": [
            {"host": "Host A", "line": "早上八点，你在地铁上，耳机刚戴好。昨天你听了一期 AI 创业的节目，里面一直提到一个词：长期记忆。今天你再打开 AI 电台，它没有给你推一条泛泛的科技新闻，而是接着昨天那个问题往下讲：为什么 AI 公司都在争长期记忆？"},
            {"host": "Host B", "line": "这个瞬间其实很关键。一个 AI 主播听起来像懂你，不只是因为它声音自然，而是因为它知道你昨天听到了哪里，今天可能还在想什么。"},
            {"host": "Host A", "line": "所以它懂的不是我喜欢科技新闻这么简单？"},
            {"host": "Host B", "line": "对。那只是标签。更深一点的理解是：你喜欢怎样进入一个问题。比如你不是想听所有 AI 新闻，你更关心一个产品为什么成立，背后的用户需求是什么，以及它和普通工具有什么区别。"},
            {"host": "Host A", "line": "那我替听众问一句：这不就是普通推荐算法吗？我点过什么，它就继续推什么。"},
            {"host": "Host B", "line": "有点像，但不完全一样。普通推荐更像看行为记录：你点了什么、停留多久、跳过了什么。长期记忆更像保存一条连续的思路：你为什么关心这个问题，你上次追问到哪里，你更喜欢被怎样解释。"},
            {"host": "Host A", "line": "也就是说，好的 AI 主播不是每天重新认识我一次，而是能接着昨天的对话往前走。"},
            {"host": "Host B", "line": "对。它不只是生成更多内容，而是减少你的筛选成本。早上通勤的时候，你不需要重新告诉它我想听什么。它已经知道，今天这段内容最好轻一点、清楚一点，但不要太浅。"},
            {"host": "Host A", "line": "可是，如果它记得太多，会不会让人有点不舒服？"},
            {"host": "Host B", "line": "会。所以真正好的记忆不应该是偷偷记住一切，而应该是可控的、可解释的、可以被删除的。你应该知道它为什么推荐这段内容，也能决定哪些东西不要被记住。"},
            {"host": "Host A", "line": "这样听起来，懂你不是一种神秘感，而是一种分寸感。"},
            {"host": "Host B", "line": "是的。未来的 AI 主播，最重要的可能不是声音多像真人，而是它能不能在合适的时候，接住你昨天还没想完的问题。"},
            {"host": "Host A", "line": "地铁到站之前，这也许就是今天最值得记住的一句话：真正像懂你，不是一直说，而是知道从哪里继续。"},
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
        "tts_text": "早上八点，你在地铁上，耳机刚戴好。昨天你听了一期 AI 创业的节目，里面一直提到一个词：长期记忆。今天你再打开 AI 电台，它没有给你推一条泛泛的科技新闻，而是接着昨天那个问题往下讲：为什么 AI 公司都在争长期记忆？\n\n这个瞬间其实很关键。一个 AI 主播听起来像懂你，不只是因为它声音自然，而是因为它知道你昨天听到了哪里，今天可能还在想什么。\n\n所以它懂的不是我喜欢科技新闻这么简单？\n\n对。那只是标签。更深一点的理解是：你喜欢怎样进入一个问题。比如你不是想听所有 AI 新闻，你更关心一个产品为什么成立，背后的用户需求是什么，以及它和普通工具有什么区别。\n\n那我替听众问一句：这不就是普通推荐算法吗？我点过什么，它就继续推什么。\n\n有点像，但不完全一样。普通推荐更像看行为记录：你点了什么、停留多久、跳过了什么。长期记忆更像保存一条连续的思路：你为什么关心这个问题，你上次追问到哪里，你更喜欢被怎样解释。\n\n也就是说，好的 AI 主播不是每天重新认识我一次，而是能接着昨天的对话往前走。\n\n对。它不只是生成更多内容，而是减少你的筛选成本。早上通勤的时候，你不需要重新告诉它我想听什么。它已经知道，今天这段内容最好轻一点、清楚一点，但不要太浅。\n\n可是，如果它记得太多，会不会让人有点不舒服？\n\n会。所以真正好的记忆不应该是偷偷记住一切，而应该是可控的、可解释的、可以被删除的。你应该知道它为什么推荐这段内容，也能决定哪些东西不要被记住。\n\n这样听起来，懂你不是一种神秘感，而是一种分寸感。\n\n是的。未来的 AI 主播，最重要的可能不是声音多像真人，而是它能不能在合适的时候，接住你昨天还没想完的问题。\n\n地铁到站之前，这也许就是今天最值得记住的一句话：真正像懂你，不是一直说，而是知道从哪里继续。",
        "voice_notes": ["Host A should sound warm, observant, and close to the listener.", "Host B should sound calm, grounded, and explanatory without sounding like a lecture."],
    },
}
