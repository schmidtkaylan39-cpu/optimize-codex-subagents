---
name: optimize-codex-subagents
description: Optimize Codex multi-agent workflows for large, long-running, or already in-progress projects when strong models such as Sol feel slow, context becomes noisy, debugging loops repeat, parallel agents duplicate work, or shared-tree edits cause conflicts. Use to retrofit a live project without losing active work, audit an existing Codex setup, shorten root-cause debugging, choose controller/scout/reviewer roles, configure AGENTS.md and custom agent TOML files, reduce context rot, enforce single-writer or worktree-safe collaboration, validate model and sandbox behavior, benchmark speed versus quality, or roll the workflow out across a team.
---

# Optimize Codex Subagents

Build the fastest workflow that still produces trustworthy results. Spend parallel capacity on independent evidence gathering and review; keep integration ownership explicit.

## Start with an audit

1. Inspect the active Codex version, available models, reasoning levels, collaboration-tool schema, advertised concurrency limit, and whether any speed-for-credits acceleration is actually available.
2. Read applicable global and project `AGENTS.md` files, plus relevant `.codex/config.toml` layers and custom agent files.
3. Inspect the repository state, validation commands, high-risk files, generated artifacts, and whether agents share one working tree.
4. Identify the real bottleneck: model reasoning latency, broad exploration, duplicated work, context rot, tool/environment discovery, tests, or merge conflicts.
5. Never print or copy credentials, bearer tokens, API keys, private URLs, or unrelated configuration values. Quote only the non-sensitive settings needed for the decision.

Do not change configuration before completing this audit. Back up every file that will be changed. Treat unavailable acceleration as a hard constraint; never make the workflow depend on a speed or credit mode the account cannot enable.

## Retrofit work already in progress

- Treat adoption as a state migration, not a clean restart. Capture active tasks, agents, commands, worktrees, dirty and untracked files, generated artifacts, decisions, and known test state before changing policy.
- Establish one controller and assign every existing change to an owner. Do not reset, clean, stash, revert, interrupt, or reformat work merely to make the tree look clean.
- Apply prompt-level ownership and compact-report rules immediately. Change `AGENTS.md` or configuration only at a coherent checkpoint; start a new task only when discovery or configuration must reload.
- Reconcile or hand off active children before changing their role. New rules do not retroactively change an already-running agent or external operation.

Read [references/in-flight-projects.md](references/in-flight-projects.md) before changing an active project or task.

## Route the work

- Handle atomic tasks, known small files, single facts, and one-off searches directly. Do not pay child startup and synthesis cost for a single grep or lookup.
- Send only high-volume, clear, repeatable extraction or classification work to a Luna-class `batch-reader` after verifying the model.
- Send noisy, read-heavy, independently bounded work to a `scout`.
- Keep requirements, architecture, exact code edits, integration, and final acceptance with the controller.
- Send a stable diff to an independent `reviewer` for correctness, regression, race, test-gap, and security analysis.
- Permit a write-capable worker only in an isolated worktree with explicit, disjoint ownership. In a shared working tree, use one writer.
- For high-risk changes, run two reviewers in parallel with different scopes, such as safety/invariants and tests/regressions.
- For debugging, assign scouts independent, falsifiable hypotheses against one stable reproduction. Keep the hypothesis ledger, edits, and root-cause decision with the controller.

Read [references/decision-guide.md](references/decision-guide.md) when selecting models, reasoning levels, concurrency, or `fork_turns` behavior.
Read [references/debugging.md](references/debugging.md) when repeated trial-and-error, flaky behavior, or an unclear root cause dominates the task.

## Configure the smallest durable surface

1. Put personal defaults in global config or global guidance.
2. Put repository-specific safety rules, test commands, ownership, and completion criteria in the repository's `AGENTS.md`.
3. Put reusable role behavior in standalone custom agent TOML files under the documented global or project agent directory. Alternatively, register a role with `[agents.<name>]` and `config_file`; do not define the same role through both paths without verifying precedence.
4. Prefer documented `[agents]` settings. Read [references/compatibility.md](references/compatibility.md) before adding version-sensitive multi-agent fields.
5. Reconcile conflicts between global and nested `AGENTS.md` files. A nested policy that permits shared-tree writers can defeat a global single-writer rule.
6. Do not replace the built-in `default` role unless the audit proves that every generic child must be read-only and named roles cannot be selected. An accidental override can disable legitimate isolated workers.

Use these output templates as starting points, then adapt them to the audited environment:

- [assets/config-snippet.toml](assets/config-snippet.toml)
- [assets/scout.toml](assets/scout.toml)
- [assets/reviewer.toml](assets/reviewer.toml)
- [assets/batch-reader.toml](assets/batch-reader.toml)
- [assets/high-risk-reviewer.toml](assets/high-risk-reviewer.toml)
- [assets/project-agents-policy.md](assets/project-agents-policy.md)
- [assets/in-flight-handoff-template.md](assets/in-flight-handoff-template.md)
- [assets/no-acceleration-profile.toml](assets/no-acceleration-profile.toml)

Do not assume example model IDs are available. Preserve the user's provider and select only models verified on that host.

## Orchestrate in waves

1. Define each child task with objective, scope, exclusions, evidence format, and completion criteria.
2. Launch all independent children before waiting. Continue in the controller only with non-overlapping work.
3. Use `fork_turns = "none"` only when the child message is self-contained. Otherwise include the smallest recent context that preserves user constraints.
4. Require compact results: facts, evidence pointers, inferences, risks, and uncovered areas. Do not return raw search or test logs unless they are the evidence.
5. Spot-check decisive evidence instead of repeating the full exploration.
6. Stabilize the diff and run initial tests before independent review.
7. Fix confirmed findings and perform the final validation in the controller.

Parallelize independent test subsets only when they are proven non-mutating or run in isolated worktrees. Give every test command one owner; keep the final acceptance gate with the controller.

Read [references/prompt-contracts.md](references/prompt-contracts.md) when composing child tasks.

## Validate before declaring success

Verify all of the following:

- The configuration parses in strict mode when the installed Codex supports strict validation.
- A scout actually starts with the intended model, reasoning level, and sandbox.
- A reviewer actually starts with its intended stronger configuration.
- The configured agent types are selectable in the active tool schema.
- The workflow does not require an acceleration, service tier, or credit mode unavailable to the account.
- Shared-tree scouts and reviewers created no diff or tracked artifacts.
- Every pre-existing change remains present and has a known owner after an in-flight cutover.
- The controller ran the repository's required tests and completion gates.
- A bug fix is tied to root-cause evidence and a regression test, or records why a deterministic regression test is impossible.
- A restore path exists for every modified configuration file.

If a version-sensitive option fails, restore the documented configuration, report the exact incompatibility, and keep the workflow usable through prompt-level role instructions.

## Measure the result

Compare at least 10 representative tasks before widening rollout. Record:

- wall-clock time;
- time to first useful evidence;
- total agent count;
- duplicated searches or tests;
- missed issues found during review;
- rework and merge conflicts;
- reproduction and root-cause debugging time;
- rejected hypotheses that were accidentally repeated;
- final gate success.

Copy [assets/benchmark-template.csv](assets/benchmark-template.csv) for a consistent team comparison.

Optimize for time to trustworthy completion, not the number of agents or raw token use.

## Roll out to a team

Keep personal paths, providers, credentials, and project-specific safety rules out of the shared Skill. Store project invariants in each repository. Pilot on one repository, publish a tagged Skill version, and let teammates audit before applying changes.

Read [references/team-rollout.md](references/team-rollout.md) when installing from GitHub, onboarding colleagues, or updating an existing deployment.
