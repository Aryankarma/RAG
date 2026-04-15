import logging
import smtplib
import socket
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any, Dict

from app.config import (
    EMAIL_ALLOWLIST_DOMAINS,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    EMAIL_SEND_ENABLED,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from app.tools.schemas import SendEmailArgs

logger = logging.getLogger(__name__)


def _recipient_allowed(to_addr: str) -> bool:
    if not EMAIL_ALLOWLIST_DOMAINS:
        return True
    at = to_addr.rfind("@")
    if at < 0:
        return False
    domain = to_addr[at + 1 :].lower()
    return any(domain == d or domain.endswith("." + d) for d in EMAIL_ALLOWLIST_DOMAINS)


def run_send_email(args: SendEmailArgs) -> Dict[str, Any]:
    logger.info(
        "[tools] send_email | phase=start | to=%s | confirm=%s | subject=%s",
        args.to,
        args.confirm,
        (args.subject or "")[:80],
    )
    draft = {
        "to": args.to,
        "subject": args.subject,
        "body": args.body,
    }
    if not args.confirm and not EMAIL_SEND_ENABLED:
        logger.info("[tools] send_email | phase=done | status=draft only (confirm=false)")
        return {
            "ok": True,
            "sent": False,
            "message": "Draft prepared. Set confirm=true to send (or set EMAIL_SEND_ENABLED=true on the server).",
            "draft": draft,
        }

    if not _recipient_allowed(str(args.to)):
        logger.warning("[tools] send_email | phase=blocked | status=recipient not allowlisted")
        return {
            "ok": False,
            "sent": False,
            "message": f"Recipient domain is not allowed. Configure EMAIL_ALLOWLIST_DOMAINS if needed.",
            "draft": draft,
        }

    missing = [
        name
        for name, val in [
            ("SMTP_HOST", SMTP_HOST),
            ("SMTP_USER", SMTP_USER),
            ("SMTP_PASSWORD", SMTP_PASSWORD),
            ("EMAIL_FROM", EMAIL_FROM),
        ]
        if not val
    ]
    if missing:
        logger.error("[tools] send_email | phase=blocked | status=missing env: %s", missing)
        return {
            "ok": False,
            "sent": False,
            "message": f"SMTP not configured: missing {', '.join(missing)}.",
            "draft": draft,
        }

    msg = EmailMessage()
    msg["Subject"] = args.subject
    msg["From"] = (
        formataddr((EMAIL_FROM_NAME, EMAIL_FROM)) if EMAIL_FROM_NAME else EMAIL_FROM
    )
    msg["To"] = str(args.to)
    msg.set_content(args.body)

    try:
        logger.info(
            "[tools] send_email | phase=smtp | status=connecting | host=%s port=%s",
            SMTP_HOST,
            SMTP_PORT,
        )
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    except socket.gaierror as e:
        # Windows: [Errno 11001] getaddrinfo failed — hostname does not resolve (DNS).
        logger.exception("[tools] send_email | phase=smtp | status=DNS failure: %s", e)
        return {
            "ok": False,
            "sent": False,
            "message": (
                f"Could not resolve SMTP server hostname {SMTP_HOST!r} (DNS error: {e!s}). "
                "Set SMTP_HOST to your provider's real server (e.g. smtp.gmail.com, smtp.office365.com). "
                "Remove placeholders like smtp.example.com, check spelling, and verify your network."
            ),
            "draft": draft,
        }
    except OSError as e:
        logger.exception("[tools] send_email | phase=smtp | status=connection error: %s", e)
        return {
            "ok": False,
            "sent": False,
            "message": f"SMTP connection error: {e!s}",
            "draft": draft,
        }
    except smtplib.SMTPException as e:
        logger.exception("[tools] send_email | phase=smtp | status=SMTP protocol/login error: %s", e)
        return {
            "ok": False,
            "sent": False,
            "message": f"SMTP send failed (login or protocol): {e!s}",
            "draft": draft,
        }

    logger.info("[tools] send_email | phase=done | status=sent")
    return {
        "ok": True,
        "sent": True,
        "message": "Email sent.",
        "draft": draft,
    }
