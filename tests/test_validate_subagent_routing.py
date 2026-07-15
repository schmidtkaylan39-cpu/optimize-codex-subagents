from __future__ import annotations

import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import validate_subagent_routing as routing  # noqa: E402
import verify_subagent_session as session  # noqa: E402


POLICY = routing.load_object(SKILL_ROOT / "references" / "routing-policy-v1.json")
# Deliberately synthetic UUIDs. Never publish local task or session IDs.
PARENT = "00000000-0000-4000-8000-000000000001"
CHILD = "00000000-0000-4000-8000-000000000002"
OTHER_CHILD = "00000000-0000-4000-8000-000000000003"
THIRD_CHILD = "00000000-0000-4000-8000-000000000004"
FOURTH_CHILD = "00000000-0000-4000-8000-000000000005"
POD = "00000000-0000-4000-8000-000000000006"
SECOND_POD = "00000000-0000-4000-8000-000000000007"
FIFTH_CHILD = "00000000-0000-4000-8000-000000000008"
SIXTH_CHILD = "00000000-0000-4000-8000-000000000009"
CAPABILITIES = {
    "internal-child": ["task_name", "message", "fork_turns"],
    "standalone-support": ["prompt", "target", "model", "thinking"],
}
CAPABILITY_EVIDENCE = {
    "internal-child": "active spawn_agent tool schema",
    "standalone-support": "active create_thread tool schema",
}


def marker_for(label: str) -> str:
    return f"ROUTING-DISPATCH-{uuid.uuid5(uuid.NAMESPACE_URL, label)}"


def manifest_for(
    dispatches: list[dict[str, object]],
    *,
    version: object = 1,
) -> dict[str, object]:
    return {
        "policy_version": version,
        "controller_thread_id": PARENT,
        "wave_capacity": {
            "thread_cap": 4,
            "occupied_before_wave": 1,
            "evidence": "active host reports four total slots and one occupied controller",
        },
        "surface_capabilities": CAPABILITIES,
        "surface_capability_evidence": CAPABILITY_EVIDENCE,
        "dispatches": dispatches,
    }


def actual_for(
    model: str,
    reasoning: str,
    *,
    role: str | None = None,
    source_kind: str = "subagent",
    sandbox: str | None = None,
    thread_id: str = CHILD,
    parent_thread_id: str = PARENT,
) -> dict[str, object]:
    return {
        "thread_id": thread_id,
        "thread_id_valid": True,
        "file_count": 1,
        "session_ids": [thread_id],
        "models": [model],
        "reasoning_efforts": [reasoning],
        "agent_types": [role] if role else [],
        "sandbox_modes": [sandbox] if sandbox else [],
        "parent_thread_ids": [parent_thread_id] if source_kind == "subagent" else [],
        "source_kind": source_kind,
        "source_is_subagent": source_kind == "subagent",
        "turn_context_count": 1,
        "parse_error_count": 0,
        "dispatch_marker_checked": True,
        "dispatch_marker_found": True,
    }


def dispatch_for(
    role: str,
    flags: list[str],
    *,
    independent_parts: int | None = None,
    surface: str | None = None,
    child_id: str = CHILD,
    suffix: str = "one",
) -> dict[str, object]:
    spec = POLICY["roles"][role]
    selected_surface = surface or spec["candidate_surfaces"][0]
    value: dict[str, object] = {
        "dispatch_id": f"{role}-{suffix}",
        "dispatch_marker": marker_for(f"{role}-{suffix}"),
        "role": role,
        "surface": selected_surface,
        "child_thread_id": child_id,
        "flags": flags,
        "flag_evidence": {flag: f"case:{role}:{flag}" for flag in flags},
        "intended_model": spec["model"],
        "intended_reasoning": spec["reasoning"],
    }
    if selected_surface == "internal-child":
        value["parent_thread_id"] = PARENT
    if spec.get("sandbox") is not None:
        value["intended_sandbox"] = spec["sandbox"]
    if role == POLICY["writer_role"]:
        value["workspace_id"] = f"workspace-{suffix}"
    if independent_parts is not None:
        value["independent_parts"] = independent_parts
        value["independent_part_evidence"] = [
            f"case:{role}:part-{index + 1}" for index in range(independent_parts)
        ]
    return value


def pod_dispatches(
    child_count: int = 2,
    *,
    available_child_slots: int = 2,
    independent_parts: int = 2,
    pod_id: str = POD,
    child_ids: list[str] | None = None,
    suffix_prefix: str = "pod",
) -> list[dict[str, object]]:
    flags = ["read_only", "read_heavy", "bounded"]
    pod = dispatch_for(
        "scout",
        flags,
        independent_parts=independent_parts,
        surface="standalone-support",
        child_id=pod_id,
        suffix=f"{suffix_prefix}-root",
    )
    pod["available_child_slots"] = available_child_slots
    pod["capacity_evidence"] = "active host reports available child slots"
    selected_child_ids = child_ids or [CHILD, OTHER_CHILD, THIRD_CHILD, FOURTH_CHILD]
    leaves: list[dict[str, object]] = []
    for index in range(child_count):
        leaf = dispatch_for(
            "scout",
            flags,
            surface="internal-child",
            child_id=selected_child_ids[index],
            suffix=f"{suffix_prefix}-leaf-{index + 1}",
        )
        leaf["parent_thread_id"] = pod_id
        leaves.append(leaf)
    return [pod, *leaves]


def write_rollout(
    root: Path,
    *,
    thread_id: str = CHILD,
    source_kind: str = "subagent",
    role: str | None = "scout",
    model: str = "gpt-5.6-terra",
    reasoning: str = "medium",
    sandbox: str = "read-only",
    marker: str = marker_for("scout-one"),
    bom: bool = False,
    extra_records: list[dict[str, object]] | None = None,
    misleading_standalone_response: bool = False,
    standalone_source: object | None = None,
    standalone_thread_source: object | None = None,
    subagent_source: object | None = None,
    parent_thread_id: str = PARENT,
) -> Path:
    session_dir = root / "sessions" / "2026" / "07" / "14"
    session_dir.mkdir(parents=True)
    path = session_dir / f"rollout-example-{thread_id}.jsonl"
    if source_kind == "subagent":
        source: object = subagent_source if subagent_source is not None else {
            "subagent": {
                "thread_spawn": {
                    "agent_nickname": "Synthetic Scout",
                    "agent_path": "synthetic/scout",
                    "agent_role": role,
                    "depth": 1,
                    "parent_thread_id": parent_thread_id,
                }
            }
        }
        meta: dict[str, object] = {
            "id": thread_id,
            "parent_thread_id": parent_thread_id,
            "source": source,
        }
        prompt = {
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "author": "controller",
                "recipient": "child",
                "content": marker,
            },
        }
    else:
        meta = {
            "id": thread_id,
            "source": standalone_source if standalone_source is not None else {"app": "desktop"},
        }
        if standalone_thread_source is not None:
            meta["thread_source"] = standalone_thread_source
        prompt = {
            "type": "event_msg",
            "payload": {"type": "user_message", "message": marker},
        }
    records: list[dict[str, object]] = [
        {"type": "session_meta", "payload": meta},
        {
            "type": "turn_context",
            "payload": {
                "model": model,
                "effort": reasoning,
                "sandbox_policy": {"type": sandbox},
            },
        },
    ]
    if misleading_standalone_response and source_kind == "standalone":
        records.append(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": "context contribution without the dispatch marker",
                },
            }
        )
    records.append(prompt)
    if extra_records:
        records.extend(extra_records)
    encoding = "utf-8-sig" if bom else "utf-8"
    path.write_text(
        "".join(json.dumps(item) + "\n" for item in records),
        encoding=encoding,
    )
    return path


class RoutingPolicyTests(unittest.TestCase):
    def validate(
        self,
        dispatch: dict[str, object],
        *,
        include_role_label: bool = True,
    ) -> dict[str, object]:
        role = str(dispatch["role"])
        spec = POLICY["roles"][role]
        source_kind = "subagent" if dispatch["surface"] == "internal-child" else "standalone"
        actual_role = role if include_role_label else None
        with patch.object(
            routing,
            "inspect_thread",
            return_value=actual_for(
                spec["model"],
                spec["reasoning"],
                role=actual_role,
                source_kind=source_kind,
                sandbox=spec.get("sandbox"),
            ),
        ):
            return routing.validate_dispatch(
                dispatch,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )

    def test_all_role_contracts_accept_their_minimum_valid_facts(self) -> None:
        cases = [
            dispatch_for("controller", []),
            dispatch_for("writer", ["single_writer"]),
            dispatch_for("scout", ["read_only", "read_heavy", "bounded"]),
            dispatch_for(
                "batch-reader",
                ["read_only", "high_volume", "repeatable", "objective_schema"],
            ),
            dispatch_for("reviewer", ["read_only", "stable_diff"]),
            dispatch_for("high-risk-reviewer", ["read_only", "financial"]),
            dispatch_for("plan", ["architecture"]),
            dispatch_for("max-solver", ["hardest", "mostly_indivisible"]),
            dispatch_for(
                "ultra-controller",
                ["parallel_materially_helpful"],
                independent_parts=2,
            ),
        ]
        for case in cases:
            with self.subTest(role=case["role"]):
                self.assertTrue(self.validate(case)["diagnostic_passed"])

    def test_missing_required_all_flag_is_rejected(self) -> None:
        result = self.validate(dispatch_for("scout", ["read_only", "read_heavy"]))
        self.assertFalse(result["diagnostic_passed"])
        self.assertIn("missing required flags: ['bounded']", result["policy_failures"])

    def test_missing_required_any_flag_is_rejected(self) -> None:
        result = self.validate(dispatch_for("high-risk-reviewer", ["read_only"]))
        self.assertFalse(result["diagnostic_passed"])
        self.assertTrue(any("required-any" in item for item in result["policy_failures"]))

    def test_ultra_requires_two_independent_parts(self) -> None:
        case = dispatch_for(
            "ultra-controller",
            ["parallel_materially_helpful"],
            independent_parts=1,
        )
        result = self.validate(case)
        self.assertFalse(result["diagnostic_passed"])
        self.assertIn("independent_parts must be >= 2", result["policy_failures"])

    def test_internal_child_cannot_claim_controller(self) -> None:
        result = self.validate(dispatch_for("controller", [], surface="internal-child"))
        self.assertFalse(result["diagnostic_passed"])
        self.assertTrue(any("not a candidate" in item for item in result["policy_failures"]))

    def test_effective_model_mismatch_is_rejected_separately(self) -> None:
        case = dispatch_for("scout", ["read_only", "read_heavy", "bounded"])
        with patch.object(
            routing,
            "inspect_thread",
            return_value=actual_for(
                "gpt-5.6-sol",
                "xhigh",
                role="scout",
                sandbox="read-only",
            ),
        ):
            result = routing.validate_dispatch(
                case,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertTrue(result["session_identity_passed"])
        self.assertFalse(result["effective_model_match_passed"])
        self.assertTrue(any("effective model mismatch" in item for item in result["model_failures"]))

    def test_sandbox_mismatch_does_not_relabel_model_failure(self) -> None:
        case = dispatch_for("scout", ["read_only", "read_heavy", "bounded"])
        with patch.object(
            routing,
            "inspect_thread",
            return_value=actual_for(
                "gpt-5.6-terra",
                "medium",
                role="scout",
                sandbox="workspace-write",
            ),
        ):
            result = routing.validate_dispatch(
                case,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertTrue(result["effective_model_match_passed"])
        self.assertFalse(result["sandbox_passed"])
        self.assertFalse(result["profile_consistency_passed"])

    def test_correct_model_without_agent_role_is_reported_separately(self) -> None:
        case = dispatch_for("high-risk-reviewer", ["read_only", "safety"])
        result = self.validate(case, include_role_label=False)
        self.assertTrue(result["profile_consistency_passed"])
        self.assertFalse(result["role_label_match"])
        self.assertFalse(result["custom_profile_proven"])
        self.assertTrue(result["diagnostic_passed"])

    def test_unpinned_sandbox_is_reported_as_not_pinned(self) -> None:
        result = self.validate(dispatch_for("controller", []))
        self.assertIsNone(result["sandbox_passed"])
        self.assertEqual(result["sandbox_status"], "not_pinned")
        self.assertTrue(result["profile_consistency_passed"])

    def test_unknown_role_uses_complete_failed_sandbox_schema(self) -> None:
        case = dispatch_for("controller", [])
        case["role"] = "unknown-role"
        result = routing.validate_dispatch(
            case,
            POLICY,
            Path("unused"),
            surface_capabilities=CAPABILITIES,
        )
        self.assertFalse(result["sandbox_passed"])
        self.assertEqual(result["sandbox_status"], "failed")

    def test_current_internal_schema_cannot_attest_caller_control(self) -> None:
        case = dispatch_for("scout", ["read_only", "read_heavy", "bounded"])
        result = self.validate(case)
        self.assertTrue(result["effective_model_match_passed"])
        self.assertTrue(result["role_label_match"])
        self.assertFalse(result["caller_model_control_attested"])
        self.assertFalse(result["caller_role_control_attested"])
        self.assertFalse(result["caller_model_controls_consistent"])
        self.assertFalse(result["custom_profile_proven"])

    def test_standalone_schema_can_attest_model_control_but_not_profile(self) -> None:
        case = dispatch_for("controller", [])
        result = self.validate(case, include_role_label=False)
        self.assertTrue(result["effective_model_match_passed"])
        self.assertTrue(result["caller_model_control_attested"])
        self.assertTrue(result["caller_model_controls_consistent"])
        self.assertFalse(result["caller_role_control_attested"])
        self.assertFalse(result["role_label_match"])
        self.assertFalse(result["custom_profile_proven"])

    def test_multiple_agent_types_do_not_match_one_exact_label(self) -> None:
        case = dispatch_for("reviewer", ["read_only", "stable_diff"])
        actual = actual_for("gpt-5.6-sol", "high", sandbox="read-only")
        actual["agent_types"] = ["scout", "reviewer"]
        with patch.object(routing, "inspect_thread", return_value=actual):
            result = routing.validate_dispatch(
                case,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertFalse(result["role_label_match"])
        self.assertFalse(result["custom_profile_proven"])
        self.assertTrue(result["diagnostic_passed"])

    def test_parent_mismatch_is_rejected(self) -> None:
        case = dispatch_for("reviewer", ["read_only", "stable_diff"])
        actual = actual_for("gpt-5.6-sol", "high", role="reviewer", sandbox="read-only")
        actual["parent_thread_ids"] = ["00000000-0000-4000-8000-000000000099"]
        with patch.object(routing, "inspect_thread", return_value=actual):
            result = routing.validate_dispatch(
                case,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertFalse(result["session_identity_passed"])
        self.assertTrue(any("parent mismatch" in item for item in result["identity_failures"]))

    def test_missing_dispatch_marker_is_rejected(self) -> None:
        case = dispatch_for("reviewer", ["read_only", "stable_diff"])
        actual = actual_for("gpt-5.6-sol", "high", role="reviewer", sandbox="read-only")
        actual["dispatch_marker_found"] = False
        with patch.object(routing, "inspect_thread", return_value=actual):
            result = routing.validate_dispatch(
                case,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertFalse(result["session_identity_passed"])

    def test_manifest_version_rejects_bool_and_float(self) -> None:
        case = dispatch_for("controller", [])
        for value in (True, 1.0):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "policy version mismatch"):
                    routing.validate_manifest(manifest_for([case], version=value), POLICY)

    def test_manifest_requires_surface_capability_evidence(self) -> None:
        case = dispatch_for("controller", [])
        value = manifest_for([case])
        del value["surface_capability_evidence"]
        with self.assertRaisesRegex(ValueError, "surface_capability_evidence"):
            routing.validate_manifest(value, POLICY)

    def test_duplicate_dispatch_child_and_marker_are_rejected(self) -> None:
        first = dispatch_for("controller", [])
        duplicate = dict(first)
        with self.assertRaisesRegex(ValueError, "duplicate dispatch_id"):
            routing.validate_manifest(manifest_for([first, duplicate]), POLICY)

        duplicate["dispatch_id"] = "different-dispatch"
        with self.assertRaisesRegex(ValueError, "duplicate child_thread_id"):
            routing.validate_manifest(manifest_for([first, duplicate]), POLICY)

        duplicate["child_thread_id"] = OTHER_CHILD
        with self.assertRaisesRegex(ValueError, "duplicate dispatch_marker"):
            routing.validate_manifest(manifest_for([first, duplicate]), POLICY)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.json"
            path.write_text('{"policy_version": 1, "policy_version": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                routing.load_object(path)

    def test_high_risk_flag_requires_matching_reviewer_dispatch(self) -> None:
        scout = dispatch_for(
            "scout",
            ["read_only", "read_heavy", "bounded", "security"],
        )
        with self.assertRaisesRegex(ValueError, "explicit same-wave reviewer coverage"):
            routing.validate_manifest(manifest_for([scout]), POLICY)

        reviewer = dispatch_for(
            "high-risk-reviewer",
            ["read_only", "security"],
            child_id=OTHER_CHILD,
            suffix="two",
        )
        reviewer["reviewed_dispatch_ids"] = [scout["dispatch_id"]]
        routing.validate_manifest(manifest_for([scout, reviewer]), POLICY)

    def test_writer_workspace_must_be_unique(self) -> None:
        first = dispatch_for("writer", ["single_writer"], suffix="one")
        second = dispatch_for(
            "writer",
            ["single_writer"],
            child_id=OTHER_CHILD,
            suffix="two",
        )
        second["workspace_id"] = first["workspace_id"]
        with self.assertRaisesRegex(ValueError, "multiple writer dispatches"):
            routing.validate_manifest(manifest_for([first, second]), POLICY)

    def test_valid_standalone_pod_respects_capacity_and_depth(self) -> None:
        dispatches = routing.validate_manifest(manifest_for(pod_dispatches()), POLICY)
        self.assertEqual(len(dispatches), 3)

    def test_standalone_pod_rejects_more_than_three_children(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds three internal children"):
            routing.validate_manifest(
                manifest_for(pod_dispatches(4, available_child_slots=3)), POLICY
            )

    def test_standalone_pod_rejects_capacity_overcommit(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds available_child_slots"):
            routing.validate_manifest(
                manifest_for(
                    pod_dispatches(
                        3,
                        available_child_slots=2,
                        independent_parts=3,
                    )
                ),
                POLICY,
            )

    def test_standalone_pod_requires_two_independent_parts(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least two independent_parts"):
            routing.validate_manifest(
                manifest_for(pod_dispatches(independent_parts=1)), POLICY
            )

    def test_standalone_pod_requires_one_independent_part_per_child(self) -> None:
        with self.assertRaisesRegex(ValueError, "more children than independent_parts"):
            routing.validate_manifest(
                manifest_for(
                    pod_dispatches(
                        3,
                        available_child_slots=3,
                        independent_parts=2,
                    )
                ),
                POLICY,
            )

    def test_internal_child_cannot_parent_grandchild(self) -> None:
        dispatches = pod_dispatches()
        dispatches[2]["parent_thread_id"] = CHILD
        with self.assertRaisesRegex(ValueError, "max_depth = 1 violation"):
            routing.validate_manifest(manifest_for(dispatches), POLICY)

    def test_standalone_pod_requires_capacity_evidence(self) -> None:
        dispatches = pod_dispatches()
        dispatches[0].pop("capacity_evidence")
        with self.assertRaisesRegex(ValueError, "capacity_evidence is required"):
            routing.validate_manifest(manifest_for(dispatches), POLICY)

    def test_writer_or_controller_cannot_coordinate_pod_children(self) -> None:
        for role in ("writer", "controller"):
            with self.subTest(role=role):
                dispatches = pod_dispatches()
                dispatches[0]["role"] = role
                if role == "writer":
                    dispatches[0]["workspace_id"] = "synthetic-workspace"
                with self.assertRaisesRegex(ValueError, "read-only role"):
                    routing.validate_manifest(manifest_for(dispatches), POLICY)

    def test_adapted_policy_cannot_use_unsafe_role_for_pod_leaf(self) -> None:
        adapted_policy = copy.deepcopy(POLICY)
        adapted_policy["roles"]["unsafe-leaf"] = {
            "model": "gpt-5.6-terra",
            "reasoning": "medium",
            "required_all_flags": [],
            "candidate_surfaces": ["internal-child"],
        }
        dispatches = pod_dispatches()
        dispatches[1]["role"] = "unsafe-leaf"
        dispatches[1]["flags"] = ["read_heavy", "bounded"]
        dispatches[1]["flag_evidence"].pop("read_only")
        with self.assertRaisesRegex(ValueError, "pod leaf.*read-only role"):
            routing.validate_manifest(manifest_for(dispatches), adapted_policy)

    def test_pod_wave_capacity_must_include_live_controller(self) -> None:
        manifest = manifest_for(pod_dispatches())
        manifest["wave_capacity"]["occupied_before_wave"] = 0
        with self.assertRaisesRegex(ValueError, "include the live controller"):
            routing.validate_manifest(manifest, POLICY)

    def test_omitted_non_controller_parent_is_rejected(self) -> None:
        leaf = pod_dispatches()[1]
        with self.assertRaisesRegex(ValueError, "neither controller_thread_id"):
            routing.validate_manifest(manifest_for([leaf]), POLICY)

    def test_two_pods_cannot_double_count_one_host_capacity(self) -> None:
        first = pod_dispatches(1, available_child_slots=1)
        second = pod_dispatches(
            1,
            available_child_slots=1,
            pod_id=SECOND_POD,
            child_ids=[FIFTH_CHILD, SIXTH_CHILD],
            suffix_prefix="second-pod",
        )
        with self.assertRaisesRegex(ValueError, "aggregate host capacity"):
            routing.validate_manifest(manifest_for([*first, *second]), POLICY)

    def test_pod_wave_capacity_counts_non_pod_dispatches_too(self) -> None:
        dispatches = pod_dispatches()
        direct_child = dispatch_for(
            "scout",
            ["read_only", "read_heavy", "bounded"],
            child_id=THIRD_CHILD,
            suffix="direct-child",
        )
        with self.assertRaisesRegex(ValueError, "aggregate host capacity"):
            routing.validate_manifest(
                manifest_for([*dispatches, direct_child]), POLICY
            )

    def test_dispatched_child_cannot_reuse_controller_thread_id(self) -> None:
        case = dispatch_for(
            "scout",
            ["read_only", "read_heavy", "bounded"],
            child_id=PARENT,
        )
        with self.assertRaisesRegex(ValueError, "differ from controller_thread_id"):
            routing.validate_manifest(manifest_for([case]), POLICY)

    def test_dispatch_marker_requires_canonical_uuid(self) -> None:
        case = dispatch_for("controller", [])
        case["dispatch_marker"] = "ROUTING-DISPATCH-UUID"
        with self.assertRaisesRegex(ValueError, "canonical UUID"):
            routing.validate_manifest(manifest_for([case]), POLICY)

    def test_manifest_rejects_role_missing_from_policy(self) -> None:
        case = dispatch_for("controller", [])
        case["role"] = "unknown-role"
        with self.assertRaisesRegex(ValueError, "not defined by policy"):
            routing.validate_manifest(manifest_for([case]), POLICY)

    def test_high_risk_reviewer_must_name_the_risky_dispatch(self) -> None:
        scout = dispatch_for(
            "scout", ["read_only", "read_heavy", "bounded", "security"]
        )
        reviewer = dispatch_for(
            "high-risk-reviewer",
            ["read_only", "security"],
            child_id=OTHER_CHILD,
            suffix="reviewer",
        )
        reviewer["reviewed_dispatch_ids"] = ["unrelated-dispatch"]
        with self.assertRaisesRegex(ValueError, "unknown reviewed_dispatch_ids"):
            routing.validate_manifest(manifest_for([scout, reviewer]), POLICY)

    def test_high_risk_reviewer_rejects_empty_or_non_risky_scope(self) -> None:
        ordinary = dispatch_for(
            "scout", ["read_only", "read_heavy", "bounded"]
        )
        reviewer = dispatch_for(
            "high-risk-reviewer",
            ["read_only", "security"],
            child_id=OTHER_CHILD,
            suffix="reviewer-empty",
        )
        with self.assertRaisesRegex(ValueError, "at least one risky dispatch"):
            routing.validate_manifest(manifest_for([ordinary, reviewer]), POLICY)

        reviewer["reviewed_dispatch_ids"] = [ordinary["dispatch_id"]]
        with self.assertRaisesRegex(ValueError, "only risky dispatches"):
            routing.validate_manifest(manifest_for([ordinary, reviewer]), POLICY)

    def test_pod_root_and_leaf_sessions_validate_end_to_end(self) -> None:
        dispatches = pod_dispatches()
        routing.validate_manifest(manifest_for(dispatches), POLICY)
        for dispatch in dispatches:
            source_kind = (
                "subagent" if dispatch["surface"] == "internal-child" else "standalone"
            )
            with patch.object(
                routing,
                "inspect_thread",
                return_value=actual_for(
                    str(dispatch["intended_model"]),
                    str(dispatch["intended_reasoning"]),
                    source_kind=source_kind,
                    sandbox="read-only",
                    thread_id=str(dispatch["child_thread_id"]),
                    parent_thread_id=str(dispatch.get("parent_thread_id", PARENT)),
                ),
            ):
                result = routing.validate_dispatch(
                    dispatch,
                    POLICY,
                    Path("unused"),
                    surface_capabilities=CAPABILITIES,
                )
            self.assertTrue(result["session_identity_passed"])
            self.assertTrue(result["effective_model_match_passed"])
            self.assertEqual(result["sandbox_status"], "verified")

        leaf = dispatches[1]
        with patch.object(
            routing,
            "inspect_thread",
            return_value=actual_for(
                str(leaf["intended_model"]),
                str(leaf["intended_reasoning"]),
                source_kind="subagent",
                sandbox="read-only",
                thread_id=str(leaf["child_thread_id"]),
                parent_thread_id=PARENT,
            ),
        ):
            mismatch = routing.validate_dispatch(
                leaf,
                POLICY,
                Path("unused"),
                surface_capabilities=CAPABILITIES,
            )
        self.assertFalse(mismatch["session_identity_passed"])

    def test_standalone_parent_and_child_equal_parent_are_rejected(self) -> None:
        standalone = dispatch_for("controller", [])
        standalone["parent_thread_id"] = PARENT
        with self.assertRaisesRegex(ValueError, "not allowed for standalone"):
            routing.validate_manifest(manifest_for([standalone]), POLICY)

        child = dispatch_for("scout", ["read_only", "read_heavy", "bounded"])
        child["parent_thread_id"] = child["child_thread_id"]
        with self.assertRaisesRegex(ValueError, "must differ"):
            routing.validate_manifest(manifest_for([child]), POLICY)

    def test_bool_is_not_accepted_as_independent_part_count(self) -> None:
        case = dispatch_for(
            "ultra-controller",
            ["parallel_materially_helpful"],
            independent_parts=2,
        )
        case["independent_parts"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            routing.validate_manifest(manifest_for([case]), POLICY)

    def test_windows_utf8_bom_manifest_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(json.dumps({"policy_version": 1}), encoding="utf-8-sig")
            self.assertEqual(routing.load_object(path), {"policy_version": 1})


class SessionInspectionTests(unittest.TestCase):
    def test_authoritative_child_metadata_and_marker_are_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(root)
            result = session.inspect_thread(
                root,
                CHILD,
                marker_for("scout-one"),
            )
        self.assertEqual(result["session_ids"], [CHILD])
        self.assertEqual(result["parent_thread_ids"], [PARENT])
        self.assertEqual(result["agent_types"], ["scout"])
        self.assertEqual(result["models"], ["gpt-5.6-terra"])
        self.assertEqual(result["reasoning_efforts"], ["medium"])
        self.assertEqual(result["sandbox_modes"], ["read-only"])
        self.assertEqual(result["source_kind"], "subagent")
        self.assertTrue(result["dispatch_marker_found"])
        self.assertTrue(session.record_is_valid(result, marker_required=True))

    def test_copied_session_meta_and_unrelated_fields_do_not_contaminate(self) -> None:
        extras = [
            {
                "type": "session_meta",
                "payload": {
                    "id": PARENT,
                    "model": "wrong-model",
                    "agent_type": "wrong-role",
                    "source": {
                        "subagent": {
                            "thread_spawn": {
                                "parent_thread_id": OTHER_CHILD,
                                "agent_role": "wrong-role",
                            }
                        }
                    },
                },
            },
            {
                "type": "unrelated",
                "payload": {
                    "model": "wrong-model",
                    "reasoning_effort": "ultra",
                    "agent_type": "wrong-role",
                    "parent_thread_id": OTHER_CHILD,
                },
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(root, extra_records=extras)
            result = session.inspect_thread(root, CHILD)
        self.assertEqual(result["session_ids"], [CHILD])
        self.assertEqual(result["models"], ["gpt-5.6-terra"])
        self.assertEqual(result["reasoning_efforts"], ["medium"])
        self.assertEqual(result["agent_types"], ["scout"])
        self.assertEqual(result["parent_thread_ids"], [PARENT])

    def test_standalone_source_and_marker_are_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(
                root,
                source_kind="standalone",
                role=None,
                model="gpt-5.6-sol",
                reasoning="high",
                sandbox="workspace-write",
                marker=marker_for("controller-one"),
            )
            result = session.inspect_thread(
                root,
                CHILD,
                marker_for("controller-one"),
            )
        self.assertEqual(result["source_kind"], "standalone")
        self.assertEqual(result["parent_thread_ids"], [])
        self.assertTrue(result["dispatch_marker_found"])

    def test_standalone_authoritative_event_beats_earlier_user_context(self) -> None:
        marker = marker_for("controller-authoritative")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(
                root,
                source_kind="standalone",
                role=None,
                marker=marker,
                misleading_standalone_response=True,
            )
            result = session.inspect_thread(root, CHILD, marker)

        self.assertTrue(result["dispatch_marker_found"])
        self.assertTrue(session.record_is_valid(result, marker_required=True))

    def test_standalone_marker_substring_is_rejected(self) -> None:
        marker = marker_for("substring")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(
                root,
                source_kind="standalone",
                role=None,
                marker=marker + "-suffix",
            )
            result = session.inspect_thread(root, CHILD, marker)
        self.assertFalse(result["dispatch_marker_found"])

    def test_marker_with_same_line_label_prefix_is_rejected(self) -> None:
        marker = marker_for("label-prefix")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(
                root,
                source_kind="standalone",
                role=None,
                marker=f"Dispatch marker: {marker}",
            )
            result = session.inspect_thread(root, CHILD, marker)
        self.assertFalse(result["dispatch_marker_found"])

    def test_unknown_source_is_not_classified_as_standalone(self) -> None:
        cases = [
            ({"future": "unknown"}, None),
            (123, "app"),
            ([], "desktop"),
        ]
        for source_value, thread_source in cases:
            with self.subTest(source=source_value, thread_source=thread_source):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    write_rollout(
                        root,
                        source_kind="standalone",
                        role=None,
                        standalone_source=source_value,
                        standalone_thread_source=thread_source,
                    )
                    result = session.inspect_thread(root, CHILD)
                self.assertEqual(result["source_kind"], "unknown")
                self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_unknown_subagent_source_shapes_fail_closed(self) -> None:
        known_spawn = {
            "agent_nickname": "Synthetic Scout",
            "agent_path": "synthetic/scout",
            "agent_role": "scout",
            "depth": 1,
            "parent_thread_id": PARENT,
        }
        cases = [
            {"subagent": {}},
            {"subagent": {"thread_spawn": known_spawn}, "future": "unknown"},
            {"subagent": {"thread_spawn": {**known_spawn, "future": "unknown"}}},
        ]
        for source_value in cases:
            with self.subTest(source=source_value):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    write_rollout(root, subagent_source=source_value)
                    result = session.inspect_thread(root, CHILD)
                self.assertEqual(result["source_kind"], "unknown")
                self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_noncanonical_subagent_parent_fails_record_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(root, parent_thread_id="not-a-canonical-uuid")
            result = session.inspect_thread(root, CHILD)
        self.assertEqual(result["source_kind"], "subagent")
        self.assertEqual(result["parent_thread_ids"], ["not-a-canonical-uuid"])
        self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_partial_thread_id_is_rejected_before_file_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(root)
            result = session.inspect_thread(root, CHILD[-12:])
        self.assertFalse(result["thread_id_valid"])
        self.assertEqual(result["file_count"], 0)

    def test_parse_error_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = write_rollout(root)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("{truncated\n")
            result = session.inspect_thread(root, CHILD)
        self.assertEqual(result["parse_error_count"], 1)
        self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_duplicate_jsonl_key_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = write_rollout(root)
            with path.open("a", encoding="utf-8") as handle:
                handle.write('{"type":"turn_context","type":"unrelated","payload":{}}\n')
            result = session.inspect_thread(root, CHILD)
        self.assertEqual(result["parse_error_count"], 1)
        self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_session_index_finds_live_and_archived_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            live = write_rollout(root)
            archived_dir = root / "archived_sessions" / "2026" / "07" / "14"
            archived_dir.mkdir(parents=True)
            archived = archived_dir / live.name
            archived.write_text(live.read_text(encoding="utf-8"), encoding="utf-8")
            index = session.build_session_index(root)
            result = session.inspect_thread(root, CHILD, session_index=index)
        self.assertEqual(result["file_count"], 2)
        self.assertFalse(session.record_is_valid(result, marker_required=False))

    def test_jsonl_bom_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_rollout(root, bom=True)
            result = session.inspect_thread(root, CHILD)
        self.assertEqual(result["parse_error_count"], 0)
        self.assertEqual(result["session_ids"], [CHILD])

    def test_verifier_main_rejects_mismatched_primary_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = write_rollout(root)
            records = [
                {"type": "session_meta", "payload": {"id": PARENT, "source": {"app": "desktop"}}},
                {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
            ]
            path.write_text(
                "".join(json.dumps(item) + "\n" for item in records),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with patch.object(
                sys,
                "argv",
                ["verify_subagent_session.py", CHILD, "--codex-home", str(root)],
            ), contextlib.redirect_stdout(stdout):
                exit_code = session.main()
        self.assertEqual(exit_code, 2)


class SkillPromptContractTests(unittest.TestCase):
    def test_default_prompt_carries_explicit_support_task_authorization(self) -> None:
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        instructions = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        expected_metadata = """interface:
  display_name: "Optimize Codex Subagents"
  short_description: "Speed up live Codex projects safely"
  default_prompt: "Use $optimize-codex-subagents for this task; I explicitly authorize you, when exact model and reasoning materially improve time to trustworthy completion, to create, monitor, integrate, and archive read-only standalone support pods using the Skill's audited mapping, and to let each pod fan out to at most three read-only internal children for substantial independent workstreams, with no deeper nesting and this main task as the sole writer."
"""
        expected_contract = """## Use explicit standalone-pod authorization

- Treat standalone support-task authorization as present only when the current user message explicitly grants it. The Skill's UI default prompt contains that grant; this file or an `AGENTS.md` rule alone does not.
- When authorized and exact model/reasoning materially improves time to trustworthy completion, create, monitor, integrate, and archive a short-lived standalone support task. Do not make the user open it or switch models manually.
- Use the audited target mapping only after verifying host availability: Luna `low` for large mechanical batches, Terra `medium` for bounded read-heavy scouting, Sol `high` for stable-diff review, and Sol `xhigh` for high-risk review.
- Treat each standalone support task as a read-only pod coordinator. When at least two substantial independent workstreams justify the startup cost, let it launch at most three internal children in one parallel wave with disjoint scopes and complete leaf behavior contracts.
- Before fan-out, record the live available child slots and its evidence, then launch no more than `min(3, available_child_slots)`. When the current four-slot host counts the active main task and pod root, admit at most two pod children at once.
- Keep the pod root and every internal child read-only: no file edits, Git operations, or external actions. Set `max_depth = 1`; pod children must not spawn descendants or standalone tasks. Keep the main task as the sole shared-tree writer, pod creator, integrator, and final acceptor.
- Treat read-only as a behavior contract unless effective session metadata proves a read-only sandbox. The live pod test reported `danger-full-access`; capture the main task's status/diff before and after every pod wave and fail the wave on any unexplained write or artifact.
- Exact model/reasoning controls apply to the standalone pod root. On the verified build, internal children inherited their parent, but inheritance is observed behavior rather than caller-controlled routing. Verify every child session and report any inherited, opaque, or mismatched assignment honestly.
- If an internal child must have exact settings and its effective model/reasoning does not match the pod root, return the unmet work to the main task so it can create another exact standalone pod; never solve this with deeper nesting.
- Embed a unique routing marker, verify the effective model/reasoning and sandbox, integrate only evidence-backed results, then archive the support task.
- Return every leaf's thread ID, unique marker, effective model/reasoning, validation evidence pointer, and any high-risk flags. High-risk flags require a matching high-risk reviewer dispatch before acceptance.
- Use internal children with complete behavior contracts when exact settings do not justify standalone-task startup. Report their effective settings without claiming caller-controlled routing.
- If the requested standalone model/reasoning cannot be created or verified, report the fallback and continue with the controller or a generic internal child; never silently claim the intended route succeeded.
"""
        self.assertEqual(metadata, expected_metadata)
        self.assertIn(expected_contract, instructions)

    def test_live_pod_evidence_is_sanitized_and_records_runtime_limits(self) -> None:
        evidence_path = SKILL_ROOT / "references" / "live-pod-validation-v1.0.3.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        encoded = json.dumps(evidence, sort_keys=True)

        self.assertEqual(evidence["report_version"], 1)
        self.assertEqual(evidence["runtime"]["host_thread_cap_observed"], 4)
        self.assertEqual(len(evidence["runs"]), 2)
        self.assertNotIn("C:\\\\Users", encoded)
        self.assertNotRegex(encoded, r"\b019f[0-9a-f-]{28,}\b")
        self.assertNotRegex(encoded, r"/(?:Users|home)/[A-Za-z0-9._-]+/")
        for run in evidence["runs"]:
            self.assertRegex(run["pod_thread_id_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(run["pod_effective_sandbox"], "danger-full-access")
            self.assertEqual(len(run["children"]), 2)
            for child in run["children"]:
                self.assertRegex(child["thread_id_sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(child["parent_matches_pod"])


if __name__ == "__main__":
    unittest.main()
