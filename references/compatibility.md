# Configuration compatibility

## Contents

1. Documented settings
2. Custom agent schema and discovery
3. Generic fallback
4. Version-sensitive role exposure
5. Validation
6. Permission caveat

## Documented settings

Prefer the current documented global settings:

```toml
[agents]
max_threads = 4
max_depth = 1
interrupt_message = true
```

Adjust `max_threads` to the runtime's actual concurrency cap. Keep `max_depth = 1` unless recursive delegation is deliberately required.

## Custom agent schema and discovery

Every custom agent file requires:

```toml
name = "scout"
description = "Human-facing description"
developer_instructions = """Role instructions"""
```

Supported session keys such as `model`, `model_reasoning_effort`, and `sandbox_mode` may also be set. Omitted values inherit from the parent session. Values in the file describe the intended profile. A child session can prove only its effective settings unless metadata also records the selected profile/config provenance.

Codex automatically discovers standalone custom agents under `~/.codex/agents/` for personal roles and `.codex/agents/` for project-scoped roles. The `name` field is the declared identity; matching the filename is a convention. Discovery makes a profile available to Codex but does not prove that a particular child selected it.

Alternatively, reference a role file explicitly from the config that owns it:

```toml
[agents.scout]
description = "Fast read-only evidence scout"
config_file = "./agents/scout.toml"

[agents.reviewer]
description = "Independent high-accuracy read-only reviewer"
config_file = "./agents/reviewer.toml"
```

Resolve `config_file` relative to the config that declares the role. Prefer one discovery method per role and verify precedence before combining them.

Agent-level `sandbox_mode = "read-only"` is a default, not an absolute guarantee. Live parent-session permission overrides may be reapplied to children. Enforce read-only behavior in instructions and inspect the final diff.

## Generic fallback

Do not override the built-in `default` role merely to install this Skill. A read-only `default` can prevent generic children from performing legitimate implementation inside isolated worktrees. Reconsider only when policy intentionally prohibits every generic child from writing and a future build records the selected profile/config provenance; a matching model or role label is not enough.

When the spawn schema cannot select named roles, choose one of these audited fallbacks:

- keep `default` unchanged and embed the complete read-only scout or reviewer contract in each child message;
- defer write-capable work to the controller until an isolated worker role is selectable and validated.

## Version-sensitive role exposure

Official Codex guidance says some runtimes may make an opaque model assignment for an unpinned subagent, and custom agent files can set model and reasoning defaults when selected. Opaque assignment is not a caller routing capability. Inspect the active spawn tool and resulting session; distinguish callable controls, effective settings, role labels, and custom-profile provenance.

Do not infer role selection merely because custom agent TOML files are installed. If the active `spawn_agent` schema exposes only a task name, message, and context-fork setting, a prompt that says "use scout" can still inherit the parent model.

Verified on Windows Desktop `26.707.9564.0` with CLI `0.144.4`:

- the active collaboration schema did not expose `agent_type`, `model`, or reasoning fields;
- a custom `scout` TOML was discovered and strict config validation passed, but a real child probe still inherited the parent `gpt-5.6-sol / high`;
- a `[features.multi_agent_v2]` metadata table was rejected as an invalid feature value;
- enabling boolean `features.multi_agent_v2 = true` conflicted with an existing `agents.max_threads` setting at thread start.

Therefore, do not enable `multi_agent_v2` in a production config on this build. Re-test after a Codex update in an isolated config, then restart the desktop app and inspect the fresh task's tool schema. Keep the current stable multi-agent configuration until the fresh schema actually exposes named role selection.

Until then, use one of these evidence-backed paths:

- generic internal children with complete role prompts, followed by session-metadata verification; never claim Terra/Luna routing when the child inherited the parent;
- explicitly authorized fresh standalone support tasks created with model and reasoning fields, then unpin/archive them after their result is integrated so each user retains one visible mainline task.

## Validation

Use the installed CLI path, not an unrelated executable on `PATH`.

Example:

```powershell
codex exec --strict-config --skip-git-repo-check -s read-only "Return exactly CONFIG_OK."
```

Then run a minimal profile-consistency test and inspect the child session to confirm its effective model, reasoning level, and sandbox. Inspect the caller schema separately. Do not infer custom-profile selection from the parent message, effective settings, or role label.

For local session evidence, use:

```powershell
python -B scripts\verify_subagent_session.py CHILD_THREAD_ID --dispatch-marker ROUTING-DISPATCH-UUID
python -B scripts\validate_subagent_routing.py DISPATCH_MANIFEST.json
```

Minimal manifest shape for the currently observed schemas:

```json
{
  "policy_version": 1,
  "surface_capabilities": {
    "internal-child": ["task_name", "message", "fork_turns"],
    "standalone-support": ["prompt", "target", "model", "thinking"]
  },
  "surface_capability_evidence": {
    "internal-child": "pointer to captured spawn_agent schema",
    "standalone-support": "pointer to captured create_thread schema"
  },
  "dispatches": [
    {
      "dispatch_id": "scout-1",
      "dispatch_marker": "ROUTING-DISPATCH-UUID",
      "role": "scout",
      "surface": "internal-child",
      "parent_thread_id": "PARENT-UUID",
      "child_thread_id": "CHILD-UUID",
      "intended_model": "gpt-5.6-terra",
      "intended_reasoning": "medium",
      "intended_sandbox": "read-only",
      "flags": ["read_only", "read_heavy", "bounded"],
      "flag_evidence": {
        "read_only": "pointer to task contract",
        "read_heavy": "pointer to assigned scope",
        "bounded": "pointer to completion condition"
      }
    }
  ]
}
```

Here `role` classifies the workload/behavior contract. It is not a claim that a
same-named custom TOML was loaded. On the verified internal schema, this example
also records no caller model or role controls, so an inherited Sol child will
correctly fail the effective-model consistency check.

The verifier requires a canonical full thread UUID, an exact rollout filename,
matching primary `session_meta.id`, a parse-clean `turn_context`, and the exact
marker in the initial prompt. The routing validator reports session identity,
effective model/reasoning, sandbox, profile consistency, caller controls,
role-label match, and custom-profile provenance separately. On a build whose
spawn schema has no role field, an exact standalone
support profile can pass `profile_consistency_passed` and
`caller_model_controls_consistent` while `role_label_match` and
`custom_profile_proven` remain false; that is a behavior contract with exact
model controls, not custom-role selection.

Use one manifest per concurrent wave. A writer requires a unique `workspace_id`,
and high-risk flags require a matching high-risk reviewer in that wave. The
manifest and rollout files are mutable local evidence, not signed attestation.

## Permission caveat

Subagents inherit or receive parent runtime overrides depending on the active Codex surface. Never assume an agent file alone is a security boundary. Use repository rules, read-only tasks, diff inspection, worktrees for write agents, and final controller verification.

Official references:

- https://developers.openai.com/codex/codex-manual.md#multi-agent-operations
- https://learn.chatgpt.com/docs/agent-configuration/subagents
- https://developers.openai.com/api/docs/guides/latest-model.md
