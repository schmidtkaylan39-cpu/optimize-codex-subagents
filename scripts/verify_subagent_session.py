#!/usr/bin/env python3
"""Print redacted effective metadata from one local Codex session rollout."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


THREAD_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def add_unique(items: list[str], value: object) -> None:
    if isinstance(value, str) and value and value not in items:
        items.append(value)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def build_session_index(root: Path) -> dict[str, list[Path]]:
    """Index rollout UUID suffixes once for multi-dispatch validation."""
    index: dict[str, list[Path]] = {}
    for directory in (root / "sessions", root / "archived_sessions"):
        if not directory.exists():
            continue
        for path in directory.rglob("*.jsonl"):
            match = re.search(r"-([0-9a-f-]{36})\.jsonl$", path.name)
            if match and THREAD_ID_RE.fullmatch(match.group(1)):
                index.setdefault(match.group(1), []).append(path)
    return index


def nested_strings(value: object) -> list[str]:
    """Return strings from a prompt payload without exposing them in output."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(nested_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(nested_strings(item))
        return result
    return []


def marker_in_payload(payload: dict[str, Any], dispatch_marker: str) -> bool:
    """Match a marker as a complete trimmed prompt line, never a substring."""
    return any(
        dispatch_marker == line.strip()
        for value in nested_strings(payload)
        for line in value.splitlines()
    )


def is_known_standalone_source(source: object, thread_source: object) -> bool:
    """Whitelist currently observed standalone source shapes and fail closed."""
    allowed = {"app", "cli", "desktop", "vscode"}
    if isinstance(source, str):
        return source in allowed
    if isinstance(source, dict):
        return set(source) == {"app"} and source.get("app") in {"desktop", "vscode"}
    if source is not None:
        return False
    return isinstance(thread_source, str) and thread_source in allowed


def known_subagent_spawn(source: object) -> dict[str, Any] | None:
    """Return the currently observed spawn record only for its exact source shape."""
    if not isinstance(source, dict) or set(source) != {"subagent"}:
        return None
    subagent = source.get("subagent")
    if not isinstance(subagent, dict) or set(subagent) != {"thread_spawn"}:
        return None
    spawn = subagent.get("thread_spawn")
    expected_keys = {
        "agent_nickname",
        "agent_path",
        "agent_role",
        "depth",
        "parent_thread_id",
    }
    if not isinstance(spawn, dict) or set(spawn) != expected_keys:
        return None
    if not isinstance(spawn.get("agent_nickname"), str) or not spawn["agent_nickname"]:
        return None
    if not isinstance(spawn.get("agent_path"), str) or not spawn["agent_path"]:
        return None
    role = spawn.get("agent_role")
    if role is not None and (not isinstance(role, str) or not role):
        return None
    if type(spawn.get("depth")) is not int or spawn["depth"] < 1:
        return None
    if not isinstance(spawn.get("parent_thread_id"), str):
        return None
    return spawn


def is_initial_prompt(envelope_type: object, payload: dict[str, Any], source_kind: str) -> bool:
    """Recognize the first task prompt on currently observed rollout schemas."""
    payload_type = payload.get("type")
    if source_kind == "subagent":
        return envelope_type == "response_item" and payload_type == "agent_message"
    if source_kind == "standalone":
        return (
            envelope_type == "event_msg" and payload_type == "user_message"
        ) or (
            envelope_type == "response_item"
            and payload_type == "message"
            and payload.get("role") == "user"
        )
    return False


def inspect_thread(
    root: Path,
    thread_id: str,
    dispatch_marker: str | None = None,
    session_index: dict[str, list[Path]] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "thread_id": thread_id,
        "thread_id_valid": bool(THREAD_ID_RE.fullmatch(thread_id)),
        "file_count": 0,
        "session_ids": [],
        "parent_thread_ids": [],
        "models": [],
        "reasoning_efforts": [],
        "agent_types": [],
        "sandbox_modes": [],
        "source_kind": "unknown",
        "source_is_subagent": None,
        "turn_context_count": 0,
        "parse_error_count": 0,
        "dispatch_marker_checked": dispatch_marker is not None,
        "dispatch_marker_found": None if dispatch_marker is None else False,
    }
    if not result["thread_id_valid"]:
        return result

    if session_index is None:
        candidates = list((root / "sessions").glob(f"**/*-{thread_id}.jsonl"))
        candidates += list((root / "archived_sessions").glob(f"**/*-{thread_id}.jsonl"))
    else:
        candidates = list(session_index.get(thread_id, []))
    result["file_count"] = len(candidates)
    if len(candidates) != 1:
        return result

    session_ids = result["session_ids"]
    parents = result["parent_thread_ids"]
    models = result["models"]
    efforts = result["reasoning_efforts"]
    agent_types = result["agent_types"]
    sandbox_modes = result["sandbox_modes"]
    assert isinstance(session_ids, list)
    assert isinstance(parents, list)
    assert isinstance(models, list)
    assert isinstance(efforts, list)
    assert isinstance(agent_types, list)
    assert isinstance(sandbox_modes, list)

    primary_meta_seen = False
    prompt_checked = False
    standalone_fallback_marker_found: bool | None = None
    try:
        with candidates[0].open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    envelope = json.loads(line, object_pairs_hook=reject_duplicate_keys)
                    payload = envelope.get("payload", {})
                except (json.JSONDecodeError, AttributeError, ValueError):
                    result["parse_error_count"] = int(result["parse_error_count"]) + 1
                    continue
                if not isinstance(envelope, dict) or not isinstance(payload, dict):
                    result["parse_error_count"] = int(result["parse_error_count"]) + 1
                    continue

                envelope_type = envelope.get("type")
                if envelope_type == "session_meta":
                    # A child rollout can contain copied parent history. Only
                    # the first session_meta is authoritative for this file.
                    if primary_meta_seen:
                        continue
                    primary_meta_seen = True
                    add_unique(session_ids, payload.get("id"))
                    add_unique(parents, payload.get("parent_thread_id"))
                    add_unique(models, payload.get("model"))
                    add_unique(agent_types, payload.get("agent_type"))

                    source = payload.get("source")
                    spawn = known_subagent_spawn(source)
                    if spawn is not None:
                        result["source_kind"] = "subagent"
                        result["source_is_subagent"] = True
                        add_unique(parents, spawn.get("parent_thread_id"))
                        add_unique(agent_types, spawn.get("agent_role"))
                    elif is_known_standalone_source(
                        source, payload.get("thread_source")
                    ):
                        result["source_kind"] = "standalone"
                        result["source_is_subagent"] = False
                    continue

                if envelope_type == "turn_context":
                    result["turn_context_count"] = int(result["turn_context_count"]) + 1
                    add_unique(models, payload.get("model"))
                    add_unique(efforts, payload.get("effort"))
                    add_unique(efforts, payload.get("reasoning_effort"))

                    collaboration = payload.get("collaboration_mode")
                    if isinstance(collaboration, dict):
                        settings = collaboration.get("settings")
                        if isinstance(settings, dict):
                            add_unique(models, settings.get("model"))
                            add_unique(efforts, settings.get("reasoning_effort"))

                    sandbox = payload.get("sandbox_policy")
                    if isinstance(sandbox, dict):
                        add_unique(sandbox_modes, sandbox.get("type"))

                source_kind = str(result["source_kind"])
                if dispatch_marker is not None and source_kind == "standalone":
                    payload_type = payload.get("type")
                    marker_found = marker_in_payload(payload, dispatch_marker)
                    if (
                        not prompt_checked
                        and envelope_type == "event_msg"
                        and payload_type == "user_message"
                    ):
                        prompt_checked = True
                        result["dispatch_marker_found"] = marker_found
                    elif (
                        standalone_fallback_marker_found is None
                        and envelope_type == "response_item"
                        and payload_type == "message"
                        and payload.get("role") == "user"
                    ):
                        # Current Desktop rollouts can contain context-generated
                        # user messages before the authoritative event_msg. Keep
                        # the first response item only as a legacy fallback.
                        standalone_fallback_marker_found = marker_found
                elif (
                    dispatch_marker is not None
                    and not prompt_checked
                    and is_initial_prompt(envelope_type, payload, source_kind)
                ):
                    prompt_checked = True
                    result["dispatch_marker_found"] = marker_in_payload(
                        payload, dispatch_marker
                    )
    except (OSError, UnicodeError):
        result["parse_error_count"] = int(result["parse_error_count"]) + 1

    if (
        dispatch_marker is not None
        and not prompt_checked
        and standalone_fallback_marker_found is not None
    ):
        result["dispatch_marker_found"] = standalone_fallback_marker_found

    return result


def record_is_valid(record: dict[str, object], marker_required: bool) -> bool:
    expected_id = record["thread_id"]
    checks = [
        record["thread_id_valid"] is True,
        record["file_count"] == 1,
        record["session_ids"] == [expected_id],
        record["source_kind"] in {"subagent", "standalone"},
        record["turn_context_count"] >= 1,
        len(record["models"]) == 1,
        len(record["reasoning_efforts"]) == 1,
        len(record["sandbox_modes"]) == 1,
        record["parse_error_count"] == 0,
    ]
    if record["source_kind"] == "subagent":
        parents = record["parent_thread_ids"]
        checks.append(
            isinstance(parents, list)
            and len(parents) == 1
            and isinstance(parents[0], str)
            and THREAD_ID_RE.fullmatch(parents[0]) is not None
        )
    elif record["source_kind"] == "standalone":
        checks.append(record["parent_thread_ids"] == [])
    if marker_required:
        checks.append(record["dispatch_marker_found"] is True)
    return all(checks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("thread_ids", nargs="+")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path.home() / ".codex",
    )
    parser.add_argument(
        "--dispatch-marker",
        help="Exact marker embedded in the initial task prompt; output reports only whether it was found.",
    )
    args = parser.parse_args()

    session_index = build_session_index(args.codex_home)
    records = [
        inspect_thread(
            args.codex_home,
            value,
            args.dispatch_marker,
            session_index,
        )
        for value in args.thread_ids
    ]
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0 if all(record_is_valid(item, args.dispatch_marker is not None) for item in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
