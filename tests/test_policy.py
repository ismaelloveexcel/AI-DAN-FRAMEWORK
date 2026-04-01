"""
Tests for autonomous approval policy helper.
"""

import os

from core.config import reload_settings
from core.policy import ApprovalPolicy


def test_policy_uses_default_scope_when_empty():
    previous_scope = os.environ.get("APPROVAL_SCOPE")
    os.environ["APPROVAL_SCOPE"] = ""
    reload_settings()

    policy = ApprovalPolicy.from_settings()
    assert policy.requires_manual_approval("money")
    assert policy.requires_manual_approval("brand")
    assert policy.requires_manual_approval("legal")
    assert not policy.requires_manual_approval("research")

    if previous_scope is None:
        del os.environ["APPROVAL_SCOPE"]
    else:
        os.environ["APPROVAL_SCOPE"] = previous_scope
    reload_settings()


def test_policy_respects_configured_scope():
    previous_scope = os.environ.get("APPROVAL_SCOPE")
    os.environ["APPROVAL_SCOPE"] = "money, legal"
    reload_settings()

    policy = ApprovalPolicy.from_settings()
    assert policy.requires_manual_approval("money")
    assert policy.requires_manual_approval("legal")
    assert not policy.requires_manual_approval("brand")

    if previous_scope is None:
        del os.environ["APPROVAL_SCOPE"]
    else:
        os.environ["APPROVAL_SCOPE"] = previous_scope
    reload_settings()


def test_policy_empty_action_scope_is_not_blocked():
    policy = ApprovalPolicy.from_settings()
    assert not policy.requires_manual_approval("")
    assert not policy.requires_manual_approval("   ")
