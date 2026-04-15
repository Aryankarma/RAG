import json
import logging
from typing import Any, Dict, List, Optional

import cohere

from app.config import COHERE_API_KEY
from app.tools.registry import (
    TOOL_DEFINITIONS_TEXT,
    execute_tool,
    parse_tool_calls,
    safe_step_summary,
)
from app.utils.cohere_llm import cohere_generate_text

co = cohere.Client(COHERE_API_KEY)

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


def _preview(text: str, n: int = 100) -> str:
    t = text.replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"

SYSTEM = """You are a concise assistant for startup founders. They upload company documents (decks, policies, contracts, metrics). You can search that knowledge and optionally send email when asked.
Be accurate: when using retrieved context, stick to what it says. If context is missing, say so.
"""


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    if not text or not text.strip():
        return None
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    start = s.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(s, start)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def run_agent(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    JSON tool loop: model returns {final:...} or {tools:[...]} until final or max iterations.
    history items: {"role": "user"|"assistant", "content": "..."}
    """
    history = history or []
    steps: List[Dict[str, Any]] = []

    logger.info(
        "[agent] start | history_turns=%s | message=%r",
        len(history),
        _preview(message, 160),
    )

    lines: List[str] = []
    for h in history:
        role = h.get("role", "user")
        content = (h.get("content") or "").strip()
        if not content:
            continue
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    lines.append(f"User: {message.strip()}")

    conv = "\n".join(lines)
    tool_results_block = ""

    for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
        status = f"iteration {iteration}/{MAX_TOOL_ITERATIONS}"
        logger.info("[agent] %s | phase=llm | status=calling Cohere (tool-calling JSON)", status)

        prompt = (
            f"{SYSTEM}\n\n{TOOL_DEFINITIONS_TEXT}\n\n"
            f"Conversation:\n{conv}{tool_results_block}\n\n"
            "Respond with JSON only, as specified above."
        )
        raw = cohere_generate_text(
            co,
            prompt,
            model="command-r-plus-08-2024",
            max_tokens=1500,
            temperature=0.15,
        )
        logger.info(
            "[agent] %s | phase=llm | status=done | response_chars=%s",
            status,
            len(raw or ""),
        )

        parsed = _try_parse_json(raw)
        if parsed is None:
            logger.warning(
                "[agent] %s | phase=parse | status=invalid JSON, attempting repair",
                status,
            )
            repair = cohere_generate_text(
                co,
                "Output ONLY valid JSON with either a 'final' string or a 'tools' array. No markdown.\n\n"
                f"Broken output:\n{raw[:4000]}",
                model="command-r-plus-08-2024",
                max_tokens=800,
                temperature=0.0,
            )
            parsed = _try_parse_json(repair)

        if parsed is None:
            logger.error("[agent] %s | phase=parse | status=failed | returning raw fallback", status)
            return {
                "answer": raw.strip() or "Could not parse tool response.",
                "steps": steps,
                "parse_error": True,
            }

        logger.info("[agent] %s | phase=parse | status=ok", status)

        final_text, tool_calls = parse_tool_calls(parsed)
        if final_text is not None:
            logger.info(
                "[agent] %s | phase=done | status=final answer | chars=%s",
                status,
                len(final_text.strip()),
            )
            return {"answer": final_text.strip(), "steps": steps}

        if not tool_calls:
            logger.warning("[agent] %s | phase=resolve | status=no tools and no final", status)
            return {
                "answer": "I could not determine the next step. Please rephrase your request.",
                "steps": steps,
            }

        logger.info(
            "[agent] %s | phase=tools | status=executing | count=%s",
            status,
            len(tool_calls),
        )

        batch_results: List[Dict[str, Any]] = []
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = call.get("name")
            arguments = call.get("arguments")
            if not name or not isinstance(arguments, dict):
                continue
            logger.info(
                "[agent] %s | tool=%s | args=%s",
                status,
                name,
                _preview(json.dumps(arguments, default=str), 200),
            )
            result = execute_tool(str(name), arguments)
            steps.append(safe_step_summary(str(name), arguments, result))
            batch_results.append({"name": name, "result": result})
            ok = result.get("ok")
            logger.info(
                "[agent] %s | tool=%s | status=finished | ok=%s | summary=%s",
                status,
                name,
                ok,
                _preview(str(result.get("message", "")), 120),
            )

        tool_results_block = (
            "\n\nTool results (use this to answer; reply next with JSON {\"final\": \"...\"} only):\n"
            + json.dumps(batch_results, indent=2, default=str)
        )

    logger.warning("[agent] stopped | status=max iterations (%s)", MAX_TOOL_ITERATIONS)
    return {
        "answer": "Maximum tool-calling steps reached. Please simplify your request.",
        "steps": steps,
    }
