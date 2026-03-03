"""Crovly SDK type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VerifyResponse:
    """Result of a captcha token verification.

    Attributes:
        success: Whether the token was valid and verification passed.
        score: Risk score from 0.0 (bot) to 1.0 (human).
        ip: The IP address that solved the challenge.
        solved_at: Unix timestamp in milliseconds when the challenge was solved.
    """

    success: bool
    score: float
    ip: str
    solved_at: int

    def is_human(self, threshold: float = 0.5) -> bool:
        """Check if the verification indicates a human.

        Args:
            threshold: Minimum score to consider human. Default: 0.5

        Returns:
            True if the token was valid and the score meets the threshold.
        """
        return self.success and self.score >= threshold
