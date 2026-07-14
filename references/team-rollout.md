# Team rollout

## Contents

1. Pilot
2. Install
3. Apply to a repository
4. Share safely
5. Update

## Pilot

1. Select one representative large repository.
2. Record baseline time, rework, review misses, and merge conflicts for at least 10 tasks.
3. Install the Skill for one maintainer.
4. Apply only the project policy and audited intended role files.
5. Record the effective child model, reasoning, parent, and role label separately. Claim caller routing only when the callable schema exposes the control, and claim a custom profile only when session metadata records its profile/config provenance. Installed TOMLs and prompt labels are insufficient.
6. Compare results before changing organization-wide defaults.

Audit speed-for-credits availability per account. Keep the shared baseline usable without it; never require teammates to enable a feature their account does not expose.

## Install

Ask Codex to install the repository with the Skill Installer:

```text
Use $skill-installer to install optimize-codex-subagents from https://github.com/schmidtkaylan39-cpu/optimize-codex-subagents,
using repository path `.` and destination name `optimize-codex-subagents`.
```

After installation, start a new Codex task so discovery and configuration layers reload.

## Apply to a repository

Use:

```text
Use $optimize-codex-subagents to audit this repository and implement the safest high-speed multi-agent workflow. Preserve project rules, back up configuration, and validate every effective role.
```

The Skill should produce:

- a bottleneck diagnosis;
- selected controller, scout, and reviewer workload contracts, with exact named routes distinguished from generic behavior prompts;
- global versus project-scoped changes;
- a single-writer or worktree policy;
- strict configuration tests and live session-metadata checks;
- a routing evidence report that separates session identity, effective model/reasoning, sandbox, behavior contract, role-label match, caller controls, and custom-profile provenance;
- restore instructions;
- a benchmark plan.

## Share safely

Do not publish personal paths, providers, auth files, tokens, private repository names, internal URLs, or project-specific secrets. Keep reusable orchestration in the Skill and keep business or safety invariants in the repository.

Tag releases so teammates can roll back. Require review for changes to templates that affect permissions, sandboxing, model selection, or writer ownership.

## Update

Re-run the audit after major Codex releases. Verify documented config fields, tool namespaces, caller controls, effective child session metadata, sandbox behavior, role labels, and any exposed custom-profile provenance before distributing a new tag.
