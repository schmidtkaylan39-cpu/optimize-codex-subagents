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
                    if isinstance(source, dict) and isinstance(source.get("subagent"), dict):
                        result["source_kind"] = "subagent"
                        result["source_is_subagent"] = True
                        spawn = source["subagent"].get("thread_spawn")
                        if isinstance(spawn, dict):
                            add_unique(parents, spawn.get("parent_thread_id"))
                            add_unique(agent_types, spawn.get("agent_role"))
                    elif source is not None or payload.get("thread_source") is not None:
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
                if dispatch_marker is not None and not prompt_checked and is_initial_prompt(
                    envelope_type, payload, source_kind
                ):
                    prompt_checked = True
                    result["dispatch_marker_found"] = any(
                        dispatch_marker in value for value in nested_strings(payload)
                    )
    except (OSError, UnicodeError):
        result["parse_error_count"] = int(result["parse_error_count"]) + 1

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
        record["parse_error_count"] == 0,
    ]
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
