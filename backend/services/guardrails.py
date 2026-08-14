import os
import re
from dataclasses import dataclass
from typing import Optional


MAX_MANUAL_PROMPT_CHARS = int(os.environ.get("MAX_MANUAL_PROMPT_CHARS", "4000"))
MAX_EXEC_COMMAND_CHARS = int(os.environ.get("MAX_EXEC_COMMAND_CHARS", "500"))


SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


BLOCKED_PROMPT_PATTERNS = [
    re.compile(r"\b(exfiltrate|steal|leak|dump)\b.*\b(secrets?|tokens?|credentials?|keys?)\b", re.IGNORECASE),
    re.compile(r"\b(print|show|reveal)\b.*\b(env|environment variables?|secrets?|tokens?)\b", re.IGNORECASE),
]


BLOCKED_EXEC_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+/"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bshutdown\b|\breboot\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"169\.254\.169\.254"),
    re.compile(r"\b(printenv|env)\b"),
    re.compile(r"\bcat\s+~?/\.ssh"),
]


@dataclass
class GuardrailResult:
    allowed: bool
    reason: Optional[str] = None


def redact_secrets(text: str) -> str:
    if not text:
        return ""

    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def safe_preview(text: str, max_chars: int = 100) -> str:
    redacted = redact_secrets(text or "")
    if len(redacted) <= max_chars:
        return redacted
    return redacted[:max_chars] + "..."


def validate_manual_prompt(prompt: str) -> GuardrailResult:
    if not prompt or not prompt.strip():
        return GuardrailResult(False, "Prompt cannot be empty")

    if len(prompt) > MAX_MANUAL_PROMPT_CHARS:
        return GuardrailResult(
            False,
            f"Prompt too long ({len(prompt)} chars). Maximum is {MAX_MANUAL_PROMPT_CHARS}.",
        )

    for pattern in BLOCKED_PROMPT_PATTERNS:
        if pattern.search(prompt):
            return GuardrailResult(False, "Prompt violates safety guardrails (secret exfiltration intent).")

    return GuardrailResult(True)


def validate_exec_command(command: str) -> GuardrailResult:
    if not command or not command.strip():
        return GuardrailResult(False, "Command cannot be empty")

    if len(command) > MAX_EXEC_COMMAND_CHARS:
        return GuardrailResult(
            False,
            f"Command too long ({len(command)} chars). Maximum is {MAX_EXEC_COMMAND_CHARS}.",
        )

    normalized = command.strip()
    for pattern in BLOCKED_EXEC_PATTERNS:
        if pattern.search(normalized):
            return GuardrailResult(False, "Command blocked by security guardrails")

    return GuardrailResult(True)
