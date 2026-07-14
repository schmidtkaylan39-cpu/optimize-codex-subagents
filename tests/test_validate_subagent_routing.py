from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import validate_subagent_routing as routing  # noqa: E402
import verify_subagent_session as session  # noqa: E402


POLICY = routing.load_object(SKILL_ROOT / "references" / "routing-policy-v1.json")
PARENT = "019f6111-4416-7cc1-8748-0b33b7bb3c0a"
CHILD = "019f6115-f340-7873-80bf-2f8c88c3ba09"
OTHER_CHILD = "019f6115-f340-7873-80bf-2f8c88c3ba10"
CAPABILITIES = {
    "internal-child": ["task_name", "message", "fork_turns"],
    "standalone-support": ["prompt", "target", "model", "thinking"],
}
CAPABILITY_EVIDENCE = {
    "internal-child": "active spawn_agent tool schema",
    "standalone-support": "active create_thread tool schema",
}


def manifest_for(
    dispatches: list[dict[str, object]],
    *,
    version: object = 1,
) -> dict[str, object]:
    return {
        "policy_version": version,
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
) -> dict[str, object]:
    return {
        "thread_id": CHILD,
        "thread_id_valid": True,
        "file_count": 1,
        "session_ids": [CHILD],
        "models": [model],
        "reasoning_efforts": [reasoning],
        "agent_types": [role] if role else [],
        "sandbox_modes": [sandbox] if sandbox else [],
        "parent_thread_ids": [PARENT] if source_kind == "subagent" else [],
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
        "dispatch_marker": f"ROUTING-DISPATCH-{role}-{suffix}",
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


def write_rollout(
    root: Path,
    *,
    thread_id: str = CHILD,
    source_kind: str = "subagent",
    role: str | None = "scout",
    model: str = "gpt-5.6-terra",
    reasoning: str = "medium",
    sandbox: str = "read-only",
    marker: str = "ROUTING-DISPATCH-scout-one",
    bom: bool = False,
    extra_records: list[dict[str, object]] | None = None,
) -> Path:
    session_dir = root / "sessions" / "2026" / "07" / "14"
    session_dir.mkdir(parents=True)
    path = session_dir / f"rollout-example-{thread_id}.jsonl"
    if source_kind == "subagent":
        source: object = {
            "subagent": {
                "thread_spawn": {
                    "parent_thread_id": PARENT,
                    "agent_role": role,
                }
            }
        }
        meta: dict[str, object] = {
            "id": thread_id,
            "parent_thread_id": PARENT,
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
        meta = {"id": thread_id, "source": {"app": "desktop"}}
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
        prompt,
    ]
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
        actual["parent_thread_ids"] = ["019f6111-6609-7113-9af3-7ba914e70539"]
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
        with self.assertRaisesRegex(ValueError, "high-risk flags require"):
            routing.validate_manifest(manifest_for([scout]), POLICY)

        reviewer = dispatch_for(
            "high-risk-reviewer",
            ["read_only", "security"],
            child_id=OTHER_CHILD,
            suffix="two",
        )
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
                "ROUTING-DISPATCH-scout-one",
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
                marker="ROUTING-DISPATCH-controller-one",
            )
            result = session.inspect_thread(
                root,
                CHILD,
                "ROUTING-DISPATCH-controller-one",
            )
        self.assertEqual(result["source_kind"], "standalone")
        self.assertEqual(result["parent_thread_ids"], [])
        self.assertTrue(result["dispatch_marker_found"])

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
  default_prompt: "Use $optimize-codex-subagents for this task; I explicitly authorize you, when exact model and reasoning materially improve time to trustworthy completion, to create, monitor, integrate, and archive read-only standalone support tasks using the Skill's audited mapping, while keeping this main task as the sole writer."
"""
        expected_contract = """## Use explicit standalone-task authorization

- Treat standalone support-task authorization as present only when the current user message explicitly grants it. The Skill's UI default prompt contains that grant; this file or an `AGENTS.md` rule alone does not.
- When authorized and exact model/reasoning materially improves time to trustworthy completion, create, monitor, integrate, and archive a short-lived standalone support task. Do not make the user open it or switch models manually.
- Use the audited target mapping only after verifying host availability: Luna `low` for large mechanical batches, Terra `medium` for bounded read-heavy scouting, Sol `high` for stable-diff review, and Sol `xhigh` for high-risk review.
- Keep every support task read-only: no file edits, Git operations, external actions, or child agents. Keep the main task as the sole shared-tree writer and final acceptor.
- Embed a unique routing marker, verify the effective model/reasoning and sandbox, integrate only evidence-backed results, then archive the support task.
- Use internal children with complete behavior contracts when exact settings do not justify standalone-task startup. Report their effective settings without claiming caller-controlled routing.
- If the requested standalone model/reasoning cannot be created or verified, report the fallback and continue with the controller or a generic internal child; never silently claim the intended route succeeded.
"""
        self.assertEqual(metadata, expected_metadata)
        self.assertIn(expected_contract, instructions)


if __name__ == "__main__":
    unittest.main()
