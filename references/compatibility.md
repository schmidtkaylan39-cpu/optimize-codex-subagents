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

Supported session keys such as `model`, `model_reasoning_effort`, and `sandbox_mode` may also be set. Omitted values inherit from the parent session.

Codex automatically discovers standalone custom agents under `~/.codex/agents/` for personal roles and `.codex/agents/` for project-scoped roles. The `name` field is the identity; matching the filename is a convention.

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

Do not override the built-in `default` role merely to install this Skill. A read-only `default` is appropriate only when named roles cannot be selected and policy requires every generic child to be read-only. It otherwise prevents generic children from performing legitimate implementation inside isolated worktrees.

When the spawn schema cannot select named roles, choose one of these audited fallbacks:

- keep `default` unchanged and embed the complete read-only scout or reviewer contract in each child message;
- deliberately register a read-only `default` when the environment prohibits all child writes;
- defer write-capable work to the controller until an isolated worker role is selectable and validated.

## Version-sensitive role exposure

Some current multi-agent tool schemas hide custom role metadata. First inspect the active spawn tool. If it already accepts an agent type, do not add experimental fields.

On a verified compatible build, these fields can expose agent selection and avoid the reserved collaboration namespace conflict:

```toml
[features.multi_agent_v2]
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

Treat this block as version-sensitive. Do not blindly add protocol enable flags, wait-time fields, or concurrency fields copied from community posts. Back up the config and run strict validation. Remove the block if the installed build rejects it.

If setting `hide_spawn_agent_metadata = false` while keeping the `collaboration` namespace causes a reserved `spawn_agent` schema error, use `tool_namespace = "agents"` on builds that accept it. If the build does not accept this workaround, use generic children with self-contained role prompts.

## Validation

Use the installed CLI path, not an unrelated executable on `PATH`.

Example:

```powershell
codex exec --strict-config --skip-git-repo-check -s read-only "Return exactly CONFIG_OK."
```

Then run a minimal role test and inspect the child session or UI to confirm its effective model, reasoning level, and sandbox. Do not infer success merely because the parent returned a final message.

## Permission caveat

Subagents inherit or receive parent runtime overrides depending on the active Codex surface. Never assume an agent file alone is a security boundary. Use repository rules, read-only tasks, diff inspection, worktrees for write agents, and final controller verification.

Official references:

- https://developers.openai.com/codex/codex-manual.md#multi-agent-operations
- https://developers.openai.com/api/docs/guides/latest-model.md
