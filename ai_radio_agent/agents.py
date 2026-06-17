from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from ai_radio_agent.json_utils import extract_json, write_json
from ai_radio_agent.providers import LLMProvider
from ai_radio_agent.schemas import SCHEMA_BY_AGENT


LOGGER = logging.getLogger("ai_radio_agent")


AGENT_ORDER = [
    "user_episode_input",
    "moment_profile_agent",
    "user_preference_agent",
    "memory_agent",
    "recommendation_agent",
    "timely_context_agent",
    "episode_brief_agent",
    "segment_planner_agent",
    "topic_planner",
    "broadcast_context_agent",
    "research_agent",
    "fact_check_agent",
    "script_outliner",
    "dialogue_planner_agent",
    "dual_host_dialogue_writer",
    "persona_agent",
    "quality_evaluator",
    "tts_export",
]


AGENT_OUTPUTS = {
    "user_episode_input": "00_user_episode_input.json",
    "moment_profile_agent": "00_moment_profile.json",
    "episode_brief_agent": "episode_brief.json",
    "segment_planner_agent": "segment_plan.json",
    "user_preference_agent": "00_user_preference.json",
    "memory_agent": "00_memory_state.json",
    "recommendation_agent": "00_recommendation.json",
    "topic_planner": "01_topic_plan.json",
    "broadcast_context_agent": "02_broadcast_context.json",
    "timely_context_agent": "02_timely_context.json",
    "research_agent": "03_research_brief.json",
    "fact_check_agent": "04_fact_check.json",
    "script_outliner": "05_script_outline.json",
    "dialogue_planner_agent": "06_dialogue_plan.json",
    "dual_host_dialogue_writer": "07_dialogue_script.json",
    "persona_agent": "08_persona_script.json",
    "quality_evaluator": "09_quality_eval.json",
    "tts_export": "10_tts_export.json",
}


AGENT_GUIDANCE = {
    "moment_profile_agent": (
        "Select and restate the editorial moment profile from the provided moment profile config. "
        "The key decision is the content operation: breakfast means continue, lunch means compress, "
        "and dinner means transform. Preserve the style rules, research policy, content logic, "
        "listener state, and intended output feeling."
    ),
    "timely_context_agent": (
        "Decide whether freshness is needed for this episode. For breakfast, usually do not turn the "
        "episode into news; continue the remembered thread unless factual verification is needed. "
        "For lunch, use timely context only when it helps relevance compression, and provide two or "
        "three source-backed updates when available. For dinner, avoid new heavy information by default "
        "and use reflective synthesis. Never turn the output into a generic news roundup."
    ),
    "dialogue_planner_agent": (
        "Plan a conversation, not alternating mini-essays. Host A must include at least one lived reaction "
        "from the listener's point of view, not only questions. Host B must use at least one concrete metaphor. "
        "The plan must include one specific remembered detail from the previous listening session. "
        "Create real response, tension, clarification, and emotional or experiential movement across turns. "
        "Follow the selected moment profile: continue for breakfast, compress for lunch, transform for dinner."
    ),
    "dual_host_dialogue_writer": (
        "Write short, speakable turns. Host A should sometimes react from lived experience before asking. "
        "Host B should answer Host A directly and include at least one concrete metaphor. "
        "Include one specific remembered detail from yesterday's listening session in listener-facing language. "
        "Avoid product-demo wording and avoid naming internal agents. Use softer phrases such as 'maybe we can "
        "think of it this way' or 'let's stay with that for a moment' instead of always giving hard conclusions."
    ),
    "persona_agent": (
        "Polish the script for natural radio. Preserve the two host personas, add conversational texture, "
        "and make sure Host A has a lived reaction, Host B has a concrete metaphor, and the episode includes "
        "one specific remembered detail from the previous listening session. Keep labels and delivery notes out "
        "of the spoken lines. The sound should be calm but not sleepy, personal but not creepy, thoughtful but "
        "not academic, warm but not sentimental, and clear without over-explaining."
    ),
    "quality_evaluator": (
        "Evaluate dialogue_liveliness_score from 1 to 10. Ask: does the dialogue contain real response, "
        "tension, clarification, and emotional or experiential movement? Also check whether Host A expresses "
        "a lived reaction, Host B uses a concrete metaphor, and one specific remembered detail appears. "
        "Evaluate moment_fit_score against the selected moment profile. For breakfast, check continuity, "
        "one-thread focus, and gentle start. For lunch, check compression, why-now relevance, source discipline, "
        "and avoidance of generic news. For dinner, check story or future image, low semantic density, and soft closure."
    ),
}


def run_agent(
    *,
    agent_name: str,
    provider: LLMProvider,
    context: dict[str, Any],
    output_dir: Path,
    max_attempts: int = 2,
) -> BaseModel:
    schema = SCHEMA_BY_AGENT[agent_name]
    prompt = build_prompt(agent_name=agent_name, schema=schema, context=context)

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        raw = provider.complete(agent_name=agent_name, prompt=prompt, schema=schema)
        try:
            parsed = extract_json(raw)
            result = schema.model_validate(parsed)
            write_json(output_dir / AGENT_OUTPUTS[agent_name], result.model_dump())
            return result
        except (ValueError, ValidationError) as exc:
            last_error = exc
            LOGGER.warning(
                "%s failed on attempt %s/%s: %s",
                agent_name,
                attempt,
                max_attempts,
                exc,
            )
            save_failed_output(output_dir, agent_name, attempt, raw, exc)
            prompt = add_retry_instruction(prompt, exc)

    raise RuntimeError(f"{agent_name} failed after {max_attempts} attempts: {last_error}") from last_error


def build_prompt(*, agent_name: str, schema: type[BaseModel], context: dict[str, Any]) -> str:
    extra_guidance = AGENT_GUIDANCE.get(agent_name, "Follow the agent responsibility implied by your name.")
    return (
        f"You are the {agent_name.replace('_', ' ')} in an AI radio production pipeline.\n"
        "Use the upstream context to produce the next artifact.\n"
        "For user-facing dialogue or TTS text, write natural radio content for a listener. "
        "Do not make hosts read internal agent names, JSON artifact names, or production instructions aloud.\n"
        "Host A is a warm observer who represents lived listener experience and asks natural questions. "
        "Host B is a calm explainer who uses everyday language, avoids jargon, and responds directly to Host A.\n"
        "Follow the selected moment profile and audio identity from upstream context. "
        "Do not sound like a generic tech news anchor, productivity coach, marketing narrator, overly cheerful podcast host, or therapist.\n"
        f"Agent-specific guidance: {extra_guidance}\n"
        "Return only valid JSON. Do not include markdown, commentary, or extra keys.\n\n"
        f"Required JSON schema:\n{schema.model_json_schema()}\n\n"
        f"Upstream context:\n{context}\n"
    )


def add_retry_instruction(prompt: str, error: Exception) -> str:
    return (
        prompt
        + "\n\nThe previous response failed JSON parsing or schema validation. "
        + f"Fix the issue and return only valid JSON. Error: {error}\n"
    )


def save_failed_output(
    output_dir: Path, agent_name: str, attempt: int, raw: str, error: Exception
) -> None:
    debug_dir = output_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = debug_dir / f"{timestamp}_{agent_name}_attempt_{attempt}.txt"
    path.write_text(f"ERROR:\n{error}\n\nRAW OUTPUT:\n{raw}\n", encoding="utf-8")
