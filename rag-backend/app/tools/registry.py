from typing import Any, Dict, List, Tuple

from app.tools.schemas import SearchCompanyKbArgs, SendEmailArgs
from app.tools.search_company_kb import run_search_company_kb
from app.tools.send_email_smtp import run_send_email

TOOL_DEFINITIONS_TEXT = """
You may call tools by returning ONLY a JSON object (no markdown, no other text) with this shape:
{"tools":[{"name":"<tool_name>","arguments":{...}}]}

Or, when you have a final answer for the user (no more tools needed), return ONLY:
{"final":"<your reply>"}

Available tools:

1) search_company_kb
   arguments: {"query": string (required), "top_k": number optional, default 5, max 20}
   Use this to retrieve text from the user's uploaded company documents before answering factual questions.

2) send_email
   arguments: {"to": string email, "subject": string, "body": string, "confirm": boolean}
   Use when the user wants to send email. If confirm is false, only a draft is returned unless the server enables sending.
   Always draft professional emails unless the user asks otherwise.

Rules:
- Prefer search_company_kb when the question may be answered from uploaded documents.
- For email: include a clear subject and body; set confirm true only if the user explicitly asked to send.
- Return valid JSON only.
""".strip()


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "search_company_kb":
        args = SearchCompanyKbArgs.model_validate(arguments)
        return run_search_company_kb(args.query, top_k=args.top_k)
    if name == "send_email":
        args = SendEmailArgs.model_validate(arguments)
        return run_send_email(args)
    return {"ok": False, "message": f"Unknown tool: {name}"}


def safe_step_summary(name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Safe subset for API / UI (no secrets, minimal body exposure)."""
    safe_args: Dict[str, Any] = {}
    if name == "search_company_kb":
        safe_args["query"] = str(arguments.get("query", ""))[:200]
        safe_args["top_k"] = arguments.get("top_k", 5)
    elif name == "send_email":
        to = str(arguments.get("to", ""))
        safe_args["to"] = to[:80]
        safe_args["subject"] = str(arguments.get("subject", ""))[:120]
        safe_args["confirm"] = bool(arguments.get("confirm"))
        body = str(arguments.get("body", ""))
        safe_args["body_preview"] = body[:160] + ("…" if len(body) > 160 else "")

    summary = result.get("message") or ("ok" if result.get("ok") else "failed")
    if name == "send_email" and result.get("sent"):
        summary = "Email sent."
    elif name == "search_company_kb" and result.get("ok"):
        summary = result.get("message", "Retrieved chunks.")

    return {"tool": name, "arguments": safe_args, "result_summary": summary}


def parse_tool_calls(payload: Dict[str, Any]) -> Tuple[str | None, List[Dict[str, Any]]]:
    """Returns (final_text, tool_calls) where exactly one should be used."""
    if "final" in payload and payload["final"] is not None:
        return (str(payload["final"]), [])
    if "tools" in payload and isinstance(payload["tools"], list):
        return (None, payload["tools"])
    return (None, [])
