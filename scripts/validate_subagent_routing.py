#!/usr/bin/env python3
"""Check cooperative routing claims against local Codex session metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from verify_subagent_session import THREAD_ID_RE, build_session_index, inspect_thread


HERE = Path(__file__).resolve().parent
DEFAULT_POLICY = HERE.parent / "references" / "routing-policy-v1.json"
SURFACES = {"internal-child", "standalone-support"}


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_object(path: Path) -> dict[str, Any]:
    # PowerShell 5.1 writes a UTF-8 BOM by default. Accept it while rejecting
    # duplicate keys instead of silently applying last-key-wins semantics.
    value = json.loads(
        path.read_text(encoding="utf-8-sig"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def object_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    if any(not is_nonempty_string(item) for item in value):
        raise ValueError(f"{label} must contain only non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} must not contain duplicates")
    return value


def has_evidence(value: object) -> bool:
    if is_nonempty_string(value):
        return True
    return (
        isinstance(value, list)
        and bool(value)
        and all(is_nonempty_string(item) for item in value)
    )


def validate_policy(policy: dict[str, Any]) -> None:
    version = policy.get("version")
    if type(version) is not int or version < 1:
        raise ValueError("policy.version must be a positive integer")
    if not is_nonempty_string(policy.get("policy_id")):
        raise ValueError("policy.policy_id must be a non-empty string")
    if policy.get("diagnostic_only") is not True:
        raise ValueError("policy.diagnostic_only must be true")

    roles = policy.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise ValueError("policy.roles must be a non-empty object")

    for role, spec in roles.items():
        if not is_nonempty_string(role) or not isinstance(spec, dict):
            raise ValueError("every policy role must have a non-empty name and object spec")
        if not is_nonempty_string(spec.get("model")):
            raise ValueError(f"policy role {role} has invalid model")
        if not is_nonempty_string(spec.get("reasoning")):
            raise ValueError(f"policy role {role} has invalid reasoning")
        sandbox = spec.get("sandbox")
        if sandbox is not None and not is_nonempty_string(sandbox):
            raise ValueError(f"policy role {role} has invalid sandbox")
        validate_string_list(
            spec.get("required_all_flags", []),
            f"policy.{role}.required_all_flags",
        )
        validate_string_list(
            spec.get("required_any_flags", []),
            f"policy.{role}.required_any_flags",
        )
        candidates = validate_string_list(
            spec.get("candidate_surfaces"),
            f"policy.{role}.candidate_surfaces",
        )
        if not candidates or not set(candidates) <= SURFACES:
            raise ValueError(f"policy role {role} has invalid candidate_surfaces")
        minimum_parts = spec.get("minimum_independent_parts")
        if minimum_parts is not None and (
            type(minimum_parts) is not int or minimum_parts < 1
        ):
            raise ValueError(f"policy role {role} has invalid minimum_independent_parts")

    high_risk_role = policy.get("high_risk_role")
    writer_role = policy.get("writer_role")
    if high_risk_role not in roles:
        raise ValueError("policy.high_risk_role must name a defined role")
    if writer_role not in roles:
        raise ValueError("policy.writer_role must name a defined role")


def validate_manifest(
    manifest: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    manifest_version = manifest.get("policy_version")
    if type(manifest_version) is not int or manifest_version != policy.get("version"):
        raise ValueError("policy version mismatch")
    dispatches = manifest.get("dispatches")
    if not isinstance(dispatches, list) or not dispatches:
        raise ValueError("manifest.dispatches must be a non-empty array")

    surface_capabilities = manifest.get("surface_capabilities")
    if not isinstance(surface_capabilities, dict):
        raise ValueError("manifest.surface_capabilities must be an object")
    capability_evidence = manifest.get("surface_capability_evidence")
    if not isinstance(capability_evidence, dict):
        raise ValueError("manifest.surface_capability_evidence must be an object")
    for surface in SURFACES:
        validate_string_list(
            surface_capabilities.get(surface, []),
            f"manifest.surface_capabilities.{surface}",
        )
        if not has_evidence(capability_evidence.get(surface)):
            raise ValueError(
                f"manifest.surface_capability_evidence.{surface} is required"
            )

    dispatch_ids: set[str] = set()
    child_ids: set[str] = set()
    markers: set[str] = set()
    writer_workspaces: set[str] = set()
    all_risk_flags: set[str] = set()
    covered_risk_flags: set[str] = set()
    high_risk_role = policy["high_risk_role"]
    writer_role = policy["writer_role"]
    high_risk_flags = set(
        policy["roles"][high_risk_role].get("required_any_flags", [])
    )

    for index, dispatch in enumerate(dispatches):
        label = f"manifest.dispatches[{index}]"
        if not isinstance(dispatch, dict):
            raise ValueError(f"{label} must be an object")
        if "require_agent_type" in dispatch:
            raise ValueError(f"{label}.require_agent_type is policy-controlled")

        dispatch_id = dispatch.get("dispatch_id")
        if not is_nonempty_string(dispatch_id):
            raise ValueError(f"{label}.dispatch_id must be a non-empty string")
        if dispatch_id in dispatch_ids:
            raise ValueError(f"duplicate dispatch_id: {dispatch_id}")
        dispatch_ids.add(dispatch_id)

        child_id = dispatch.get("child_thread_id")
        if not isinstance(child_id, str) or not THREAD_ID_RE.fullmatch(child_id):
            raise ValueError(f"{label}.child_thread_id must be a canonical thread UUID")
        if child_id in child_ids:
            raise ValueError(f"duplicate child_thread_id: {child_id}")
        child_ids.add(child_id)

        marker = dispatch.get("dispatch_marker")
        if not isinstance(marker, str) or len(marker.strip()) < 12:
            raise ValueError(f"{label}.dispatch_marker must contain at least 12 characters")
        if marker in markers:
            raise ValueError(f"duplicate dispatch_marker: {marker}")
        markers.add(marker)

        role = dispatch.get("role")
        if not is_nonempty_string(role):
            raise ValueError(f"{label}.role must be a non-empty string")
        surface = dispatch.get("surface")
        if surface not in SURFACES:
            raise ValueError(f"{label}.surface is invalid")
        if surface == "internal-child":
            parent_id = dispatch.get("parent_thread_id")
            if not isinstance(parent_id, str) or not THREAD_ID_RE.fullmatch(parent_id):
                raise ValueError(f"{label}.parent_thread_id must be a canonical thread UUID")
            if parent_id == child_id:
                raise ValueError(f"{label}.parent_thread_id must differ from child_thread_id")
        elif "parent_thread_id" in dispatch:
            raise ValueError(f"{label}.parent_thread_id is not allowed for standalone support")

        if not is_nonempty_string(dispatch.get("intended_model")):
            raise ValueError(f"{label}.intended_model must be a non-empty string")
        if not is_nonempty_string(dispatch.get("intended_reasoning")):
            raise ValueError(f"{label}.intended_reasoning must be a non-empty string")

        flags = validate_string_list(dispatch.get("flags"), f"{label}.flags")
        flag_evidence = dispatch.get("flag_evidence")
        if not isinstance(flag_evidence, dict):
            raise ValueError(f"{label}.flag_evidence must be an object")
        missing_evidence = [
            flag for flag in flags if not has_evidence(flag_evidence.get(flag))
        ]
        if missing_evidence:
            raise ValueError(f"{label} has flags without evidence: {missing_evidence}")

        flagged_risks = high_risk_flags & set(flags)
        all_risk_flags.update(flagged_risks)
        if role == high_risk_role:
            covered_risk_flags.update(flagged_risks)

        if role == writer_role:
            workspace_id = dispatch.get("workspace_id")
            if not is_nonempty_string(workspace_id):
                raise ValueError(f"{label}.workspace_id is required for writer")
            if workspace_id in writer_workspaces:
                raise ValueError(f"multiple writer dispatches share workspace_id: {workspace_id}")
            writer_workspaces.add(workspace_id)

        independent_parts = dispatch.get("independent_parts")
        if independent_parts is not None:
            if type(independent_parts) is not int or independent_parts < 1:
                raise ValueError(f"{label}.independent_parts must be a positive integer")
            evidence = validate_string_list(
                dispatch.get("independent_part_evidence"),
                f"{label}.independent_part_evidence",
            )
            if len(evidence) < independent_parts:
                raise ValueError(
                    f"{label}.independent_part_evidence has fewer items than independent_parts"
                )

    uncovered_risks = sorted(all_risk_flags - covered_risk_flags)
    if uncovered_risks:
        raise ValueError(
            "high-risk flags require a matching high-risk-reviewer dispatch: "
            f"{uncovered_risks}"
        )
    return dispatches


def empty_result(dispatch_id: str, role: object, failure: str) -> dict[str, Any]:
    return {
        "dispatch_id": dispatch_id,
        "role": role,
        "diagnostic_passed": False,
        "profile_consistency_passed": False,
        "attested_preconditions_passed": False,
        "session_identity_passed": False,
        "effective_model_match_passed": False,
        "sandbox_passed": False,
        "role_label_match": False,
        "custom_profile_proven": False,
        "caller_model_control_attested": False,
        "caller_role_control_attested": False,
        "caller_model_controls_consistent": False,
        "policy_failures": [failure],
        "identity_failures": [],
        "model_failures": [],
        "sandbox_failures": [],
        "expected": {},
        "actual": {},
    }


def validate_dispatch(
    dispatch: dict[str, Any],
    policy: dict[str, Any],
    codex_home: Path,
    session_index: dict[str, list[Path]] | None = None,
    surface_capabilities: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    dispatch_id = str(dispatch.get("dispatch_id", "<missing>"))
    role = dispatch.get("role")
    policy_failures: list[str] = []
    identity_failures: list[str] = []
    model_failures: list[str] = []
    sandbox_failures: list[str] = []
    roles = policy["roles"]
    if not isinstance(role, str) or role not in roles:
        return empty_result(dispatch_id, role, "unknown role")

    spec = roles[role]
    expected_model = spec["model"]
    expected_reasoning = spec["reasoning"]
    expected_sandbox = spec.get("sandbox")
    intended_model = dispatch.get("intended_model")
    intended_reasoning = dispatch.get("intended_reasoning")
    intended_sandbox = dispatch.get("intended_sandbox")
    raw_flags = dispatch.get("flags")
    flags = set(raw_flags) if isinstance(raw_flags, list) else set()

    check(is_nonempty_string(intended_model), "missing intended_model", policy_failures)
    check(is_nonempty_string(intended_reasoning), "missing intended_reasoning", policy_failures)
    check(intended_model == expected_model, "intended model violates policy", policy_failures)
    check(
        intended_reasoning == expected_reasoning,
        "intended reasoning violates policy",
        policy_failures,
    )
    if expected_sandbox is not None:
        check(
            intended_sandbox == expected_sandbox,
            "intended sandbox violates policy",
            policy_failures,
        )

    required_all = set(spec.get("required_all_flags", []))
    missing_all = sorted(required_all - flags)
    check(not missing_all, f"missing required flags: {missing_all}", policy_failures)

    required_any = set(spec.get("required_any_flags", []))
    if required_any:
        check(
            bool(required_any & flags),
            f"none of required-any flags present: {sorted(required_any)}",
            policy_failures,
        )

    flag_evidence = dispatch.get("flag_evidence")
    if not isinstance(flag_evidence, dict):
        policy_failures.append("flag_evidence must be an object")
    else:
        missing_evidence = sorted(
            flag for flag in flags if not has_evidence(flag_evidence.get(flag))
        )
        check(
            not missing_evidence,
            f"flags without evidence: {missing_evidence}",
            policy_failures,
        )

    surface = dispatch.get("surface")
    check(
        surface in spec["candidate_surfaces"],
        f"surface is not a candidate for workload: {surface}",
        policy_failures,
    )

    minimum_parts = spec.get("minimum_independent_parts")
    if type(minimum_parts) is int:
        independent_parts = dispatch.get("independent_parts")
        check(
            type(independent_parts) is int and independent_parts >= minimum_parts,
            f"independent_parts must be >= {minimum_parts}",
            policy_failures,
        )
        part_evidence = dispatch.get("independent_part_evidence")
        check(
            isinstance(part_evidence, list)
            and type(independent_parts) is int
            and len(part_evidence) >= independent_parts
            and all(is_nonempty_string(item) for item in part_evidence),
            "independent_part_evidence is incomplete",
            policy_failures,
        )

    child_thread_id = dispatch.get("child_thread_id")
    marker = dispatch.get("dispatch_marker")
    actual = inspect_thread(
        codex_home,
        child_thread_id if isinstance(child_thread_id, str) else "",
        marker if isinstance(marker, str) else None,
        session_index,
    )
    check(actual["thread_id_valid"] is True, "child_thread_id is not canonical", identity_failures)
    check(actual["file_count"] == 1, "child session record is missing or ambiguous", identity_failures)
    check(
        actual["session_ids"] == [child_thread_id],
        f"session id mismatch: {actual['session_ids']}",
        identity_failures,
    )
    check(actual["parse_error_count"] == 0, "session record has parse errors", identity_failures)
    check(actual["turn_context_count"] >= 1, "session has no turn_context", identity_failures)
    check(actual["dispatch_marker_found"] is True, "dispatch marker not found in initial prompt", identity_failures)

    check(
        actual["models"] == [expected_model],
        f"effective model mismatch: {actual['models']}",
        model_failures,
    )
    check(
        actual["reasoning_efforts"] == [expected_reasoning],
        f"effective reasoning mismatch: {actual['reasoning_efforts']}",
        model_failures,
    )
    if expected_sandbox is not None:
        check(
            actual["sandbox_modes"] == [expected_sandbox],
            f"effective sandbox mismatch: {actual['sandbox_modes']}",
            sandbox_failures,
        )

    if surface == "internal-child":
        check(actual["source_kind"] == "subagent", "session is not a proven subagent", identity_failures)
        parent_thread_id = dispatch.get("parent_thread_id")
        check(
            isinstance(parent_thread_id, str)
            and actual["parent_thread_ids"] == [parent_thread_id],
            f"parent mismatch: {actual['parent_thread_ids']}",
            identity_failures,
        )
    elif surface == "standalone-support":
        check(
            actual["source_kind"] == "standalone",
            "session is not a proven standalone task",
            identity_failures,
        )
        check(
            actual["parent_thread_ids"] == [],
            f"standalone session has parent metadata: {actual['parent_thread_ids']}",
            identity_failures,
        )

    capabilities = set((surface_capabilities or {}).get(str(surface), []))
    caller_model_control_attested = (
        "model" in capabilities
        and bool({"thinking", "model_reasoning_effort"} & capabilities)
    )
    caller_role_control_attested = bool(
        {"agent_type", "agent_role", "role"} & capabilities
    )
    role_label_match = actual["agent_types"] == [role]
    # Current rollout metadata exposes at most a role label. It does not expose
    # the selected custom TOML path, config ID, or hash, so provenance remains
    # unproven even when the label and effective settings match.
    custom_profile_proven = False

    attested_preconditions_passed = not policy_failures
    session_identity_passed = not identity_failures
    effective_model_match_passed = session_identity_passed and not model_failures
    sandbox_passed = session_identity_passed and not sandbox_failures
    profile_consistency_passed = (
        attested_preconditions_passed
        and effective_model_match_passed
        and sandbox_passed
    )
    caller_model_controls_consistent = (
        caller_model_control_attested and effective_model_match_passed
    )
    diagnostic_passed = profile_consistency_passed
    return {
        "dispatch_id": dispatch_id,
        "role": role,
        "diagnostic_passed": diagnostic_passed,
        "profile_consistency_passed": profile_consistency_passed,
        "attested_preconditions_passed": attested_preconditions_passed,
        "session_identity_passed": session_identity_passed,
        "effective_model_match_passed": effective_model_match_passed,
        "sandbox_passed": sandbox_passed,
        "role_label_match": role_label_match,
        "custom_profile_proven": custom_profile_proven,
        "caller_model_control_attested": caller_model_control_attested,
        "caller_role_control_attested": caller_role_control_attested,
        "caller_model_controls_consistent": caller_model_controls_consistent,
        "policy_failures": policy_failures,
        "identity_failures": identity_failures,
        "model_failures": model_failures,
        "sandbox_failures": sandbox_failures,
        "expected": {
            "model": expected_model,
            "reasoning": expected_reasoning,
            "sandbox": expected_sandbox,
        },
        "actual": {
            "session_ids": actual["session_ids"],
            "models": actual["models"],
            "reasoning_efforts": actual["reasoning_efforts"],
            "agent_types": actual["agent_types"],
            "sandbox_modes": actual["sandbox_modes"],
            "parent_thread_ids": actual["parent_thread_ids"],
            "source_kind": actual["source_kind"],
            "dispatch_marker_found": actual["dispatch_marker_found"],
            "parse_error_count": actual["parse_error_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    args = parser.parse_args()

    try:
        manifest = load_object(args.manifest)
        policy = load_object(args.policy)
        validate_policy(policy)
        dispatches = validate_manifest(manifest, policy)
        surface_capabilities = manifest["surface_capabilities"]
        session_index = build_session_index(args.codex_home)
        results = [
            validate_dispatch(
                item,
                policy,
                args.codex_home,
                session_index,
                surface_capabilities,
            )
            for item in dispatches
        ]
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"input_error": str(error)}, ensure_ascii=False, indent=2))
        return 2

    output = {
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "policy_sha256": object_sha256(policy),
        "diagnostic_only": True,
        "integrity_limit": "Local rollout files and manifest evidence are mutable and unsigned.",
        "diagnostic_passed": sum(
            1 for item in results if item["diagnostic_passed"]
        ),
        "diagnostic_failed": sum(
            1 for item in results if not item["diagnostic_passed"]
        ),
        "profile_consistency_passed": sum(
            1 for item in results if item["profile_consistency_passed"]
        ),
        "session_identity_passed": sum(
            1 for item in results if item["session_identity_passed"]
        ),
        "effective_model_match_passed": sum(
            1 for item in results if item["effective_model_match_passed"]
        ),
        "sandbox_passed": sum(1 for item in results if item["sandbox_passed"]),
        "role_label_matches": sum(
            1 for item in results if item["role_label_match"]
        ),
        "caller_model_controls_consistent": sum(
            1 for item in results if item["caller_model_controls_consistent"]
        ),
        "custom_profiles_proven": 0,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["diagnostic_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
