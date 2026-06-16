from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserPreference(StrictBaseModel):
    listener_name: str
    preferred_topics: list[str]
    tone: str
    episode_length_minutes: int = Field(ge=3, le=30)
    avoid_topics: list[str]


class MemoryProfile(StrictBaseModel):
    listener_summary: str
    known_preferences: list[str]
    recent_episode_memory: list[str]


class Recommendation(StrictBaseModel):
    episode_theme: str
    why_this_fits: str
    candidate_topics: list[str]


class TopicPlan(StrictBaseModel):
    title: str
    angle: str
    segments: list[str]
    target_takeaway: str


class ResearchBrief(StrictBaseModel):
    key_points: list[str]
    examples: list[str]
    open_questions: list[str]
    sources_to_check: list[str]


class FactCheckReport(StrictBaseModel):
    status: Literal["pass", "needs_review"]
    verified_claims: list[str]
    risky_claims: list[str]
    revision_notes: list[str]


class ScriptOutline(StrictBaseModel):
    intro: str
    beats: list[str]
    transition_notes: list[str]
    outro: str


class DialogueLine(StrictBaseModel):
    host: Literal["Host A", "Host B"]
    line: str


class DialogueScript(StrictBaseModel):
    title: str
    lines: list[DialogueLine]


class PersonaNotes(StrictBaseModel):
    host_a_persona: str
    host_b_persona: str
    style_rules: list[str]
    revised_lines: list[DialogueLine]


class QualityEvaluation(StrictBaseModel):
    score: int = Field(ge=1, le=10)
    strengths: list[str]
    improvements: list[str]
    ready_for_tts: bool


class TTSExport(StrictBaseModel):
    episode_title: str
    tts_text: str
    voice_notes: list[str]


SCHEMA_BY_AGENT: dict[str, type[BaseModel]] = {
    "user_preference_agent": UserPreference,
    "memory_agent": MemoryProfile,
    "recommendation_agent": Recommendation,
    "topic_planner": TopicPlan,
    "research_agent": ResearchBrief,
    "fact_check_agent": FactCheckReport,
    "script_outliner": ScriptOutline,
    "dual_host_dialogue_writer": DialogueScript,
    "persona_agent": PersonaNotes,
    "quality_evaluator": QualityEvaluation,
    "tts_export": TTSExport,
}
