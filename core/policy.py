"""
Policy helper for autonomous execution boundaries.

This module defines lightweight approval gating for actions that should
require founder review (money/brand/legal by default).
"""

from dataclasses import dataclass
from typing import Iterable, Set

from core.config import get_settings


DEFAULT_SCOPE = {"money", "brand", "legal"}


def _normalize_scope(scope: Iterable[str]) -> Set[str]:
    return {item.strip().lower() for item in scope if item and item.strip()}


@dataclass(frozen=True)
class ApprovalPolicy:
    """Represents approval categories that require manual intervention."""

    required_scope: Set[str]

    @classmethod
    def from_settings(cls) -> "ApprovalPolicy":
        settings = get_settings()
        configured = settings.automation.approval_scope.split(",")
        normalized = _normalize_scope(configured)
        return cls(required_scope=normalized or set(DEFAULT_SCOPE))

    def requires_manual_approval(self, action_scope: str) -> bool:
        """Return True when action scope is configured as approval-required."""
        if not action_scope:
            return False
        return action_scope.strip().lower() in self.required_scope

