"""
Pluggable safety hook for Astrosp/Awesome-OSINT-List.

Wraps a model/pipeline call and enforces the compiled OPA policy in
policies/rules.rego before letting output through. Requires the `opa`
CLI on PATH (https://www.openpolicyagent.org/docs/latest/#running-opa) --
this wrapper shells out to `opa eval` rather than reimplementing Rego
evaluation in Python, so the policy file stays the single source of truth.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

POLICY_PATH = Path(__file__).parent.parent / "policies" / "rules.rego"
QUERY = "data.legalguard.astrosp_awesome_osint_list.allow"


class ComplianceBreach(Exception):
    """Raised when the OPA policy denies the given input."""


def check_compliance(input_payload: dict) -> bool:
    """Returns True if `input_payload` satisfies the compiled guardrail.

    Raises ComplianceBreach (not a bare bool) when it doesn't, so calling
    code can't accidentally ignore a False return value.
    """
    result = subprocess.run(
        ["opa", "eval", "--format=json", "--data", str(POLICY_PATH), "--stdin-input", QUERY],
        input=json.dumps(input_payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"opa eval failed: {result.stderr.strip()}")

    parsed = json.loads(result.stdout)
    allowed = bool(parsed["result"][0]["expressions"][0]["value"])
    if not allowed:
        raise ComplianceBreach(f"Denied by astrosp_awesome_osint_list guardrail for input: {input_payload}")
    return True


def guarded(fn):
    """Decorator: run check_compliance(kwargs) before calling fn(**kwargs)."""

    def wrapper(*args, **kwargs):
        check_compliance(kwargs)
        return fn(*args, **kwargs)

    return wrapper
