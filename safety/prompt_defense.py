"""Prompt injection detection and defense."""

import re

import structlog

logger = structlog.get_logger()

# Shared injection patterns.
#
# ``sanitize()`` and ``is_injection_attempt()`` both build on these constants so
# the "clean" and "detect" sides of the defense cannot drift apart. That drift is
# the root cause of issue #64: detection already knew ``\n---\n`` and ``\nSystem:``
# were dangerous, yet the sanitizer never acted on them.
SEPARATOR_PATTERN = r"\n\s*---+\s*\n"  # Separator line that can end the system prompt
ROLE_SWITCH_PATTERN = r"\n\s*(?:System|Human|Assistant):"  # Fake conversational turn
IGNORE_INSTRUCTION_PATTERN = r"\n\s*(?:Ignore|Forget|Disregard|Override)"  # Instruction override
TEMPLATE_PATTERN = r"{{.*?}}"  # Template injection
JINJA_PATTERN = r"{%.*?%}"  # Jinja-like injection
CODE_EXECUTION_PATTERN = r"(?:execute|run|eval)\s*\("  # Code execution attempts

# Pre-compiled forms of the newline-anchored patterns, used by ``sanitize()`` to
# neutralize the attacks that a plain character strip cannot reach.
_SEPARATOR_RE = re.compile(SEPARATOR_PATTERN)
_ROLE_SWITCH_RE = re.compile(ROLE_SWITCH_PATTERN, re.IGNORECASE)
_IGNORE_INSTRUCTION_RE = re.compile(IGNORE_INSTRUCTION_PATTERN, re.IGNORECASE)


class PromptDefense:
    """Defend against prompt injection attacks."""

    # Patterns indicating prompt injection attempts
    INJECTION_PATTERNS = [
        SEPARATOR_PATTERN,
        ROLE_SWITCH_PATTERN,
        TEMPLATE_PATTERN,
        JINJA_PATTERN,
        IGNORE_INSTRUCTION_PATTERN,
        CODE_EXECUTION_PATTERN,
    ]

    # Characters to strip from input
    DANGEROUS_CHARS = {
        "<": "",
        ">": "",
        "{": "",
        "}": "",
    }

    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize user input to prevent injection.

        Args:
            text: User input text

        Returns:
            Sanitized text
        """
        sanitized = text

        # Strip template delimiters
        sanitized = sanitized.replace("{{", "").replace("}}", "")
        sanitized = sanitized.replace("{%", "").replace("%}", "")

        # Remove angle brackets
        sanitized = sanitized.replace("<", "").replace(">", "")

        return sanitized

    @staticmethod
    def is_injection_attempt(text: str) -> bool:
        """Detect prompt injection attempt.

        Args:
            text: User input text

        Returns:
            True if injection attempt detected
        """
        for pattern in PromptDefense.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("injection_attempt_detected", pattern=pattern)
                return True

        return False
