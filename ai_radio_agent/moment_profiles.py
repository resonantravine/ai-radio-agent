from __future__ import annotations

from typing import Any, Literal

MomentKey = Literal["breakfast", "lunch", "dinner"]


MOMENT_PROFILES: dict[MomentKey, dict[str, Any]] = {
    "breakfast": {
        "moment": "breakfast",
        "format_name": "Yoli's Morning Coffee",
        "core_operation": "continue",
        "content_role": "continue yesterday's unfinished question and offer one useful thread",
        "listener_state": "half-awake, beginning the day",
        "output_feeling": "gentle continuity",
        "time": "8:00 AM",
        "scene": "the listener is in a quiet kitchen preparing breakfast",
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
        "audio_identity": (
            "A soft personal morning radio ritual for breakfast at home: calm but not sleepy, "
            "personal but not creepy, thoughtful but not academic, warm but not sentimental, "
            "clear but not over-explaining."
        ),
    },
    "lunch": {
        "moment": "lunch",
        "format_name": "Yoli's Midday Brief",
        "core_operation": "compress",
        "content_role": "compress timely or relevant updates and explain why they matter now",
        "listener_state": "busy, between tasks",
        "output_feeling": "useful clarity",
        "time": "12:30 PM",
        "scene": "the listener is taking a short walk or lunch break with earbuds in",
        "style_rules": [
            "Start quickly, but not anxiously.",
            "Use current context only when it helps the topic.",
            "Explain why this matters now.",
            "Prefer two or three verified points over broad commentary.",
            "Keep turns shorter than breakfast.",
            "End with one practical framing question for the afternoon.",
            "Avoid doom-scrolling, hot takes, and generic trend summaries.",
        ],
        "content_logic": "fresh context -> relevance filter -> compressed explanation -> why now -> afternoon takeaway",
        "research_policy": "Run timely context search when freshness is relevant. Require source-backed claims.",
        "semantic_density": "medium",
        "audio_identity": (
            "A clear, useful midday brief: brisk but not anxious, relevant but not newsy, "
            "compressed enough for a short break."
        ),
    },
    "dinner": {
        "moment": "dinner",
        "format_name": "Yoli's Evening Reset",
        "core_operation": "transform",
        "content_role": "turn the day's idea into a story, future image, or reflective closure",
        "listener_state": "low-energy, ending the day",
        "output_feeling": "soft closure",
        "time": "7:30 PM",
        "scene": "the listener is cooking, doing dishes, or winding down with earbuds in",
        "style_rules": [
            "Do not introduce heavy new information.",
            "Use one story, scene, or imagined future moment.",
            "Let the concept become sensory and human.",
            "Slow down the explanation.",
            "Create closure rather than urgency.",
            "End with a question that can stay with the listener, not a task.",
            "Avoid therapy tone, sentimentality, and abstract essay language.",
        ],
        "content_logic": "day's thread -> small story -> future image -> reflective question -> soft closure",
        "research_policy": "Do not run news search by default. Use existing memory and reflective synthesis.",
        "semantic_density": "low",
        "audio_identity": (
            "A slower evening reset: reflective, sensory, story-shaped, and designed to let an idea settle."
        ),
    },
}


def get_moment_profile(moment: str) -> dict[str, Any]:
    normalized = moment.lower()
    if normalized not in MOMENT_PROFILES:
        valid = ", ".join(MOMENT_PROFILES)
        raise ValueError(f"Unsupported moment={moment!r}. Use one of: {valid}.")
    return MOMENT_PROFILES[normalized]  # type: ignore[index]
