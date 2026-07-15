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

## Separate routing evidence before delegation

1. Inspect the active child-spawn schema before promising model or role routing. Some runtimes may make an opaque model assignment when settings are unpinned, but that is not a caller-controlled routing capability. On the verified build below, internal children inherited the parent.
2. Treat a custom agent TOML as an intended profile, not proof that a child selected it.
3. Do not claim that a custom profile was selected unless the caller surface accepts that profile and session metadata records profile/config provenance such as an ID, path, or hash. A matching role label alone is insufficient.
4. If the internal spawn surface exposes only a task name, message, and context fork, treat its model/role selection as non-enforceable and assume the child can inherit the parent until session evidence proves otherwise. A role prompt can constrain behavior, but it does not change the effective model.
5. When exact model and reasoning are required and the user has authorized a separate support task, use a short-lived standalone task whose creation surface explicitly accepts `model` and `thinking`, verify its session metadata, integrate the result, and archive it.

Never describe Terra, Luna, or a named Reviewer as automatically selected merely because its file is installed or its name appears in a prompt. Read [references/compatibility.md](references/compatibility.md) before choosing a routing surface.

## Retrofit work already in progress

- Treat adoption as a state migration, not a clean restart. Capture active tasks, agents, commands, worktrees, dirty and untracked files, generated artifacts, decisions, and known test state before changing policy.
- Establish one controller and assign every existing change to an owner. Do not reset, clean, stash, revert, interrupt, or reformat work merely to make the tree look clean.
- Apply prompt-level ownership and compact-report rules immediately. Change `AGENTS.md` or configuration only at a coherent checkpoint; start a new task only when discovery or configuration must reload.
- Reconcile or hand off active children before changing their role. New rules do not retroactively change an already-running agent or external operation.

Read [references/in-flight-projects.md](references/in-flight-projects.md) before changing an active project or task.

## Route the work

- Handle atomic tasks, known small files, single facts, and one-off searches directly. Do not pay child startup and synthesis cost for a single grep or lookup.
- Use the `batch-reader` behavior contract only for high-volume, clear, repeatable extraction or classification. If effective Luna/low is required, use a caller-controlled surface and verify the resulting model; otherwise report the actual inherited or opaque assignment without calling it Luna routing.
- Use the scout behavior contract for noisy, read-heavy, independently bounded work. A generic internal child can follow that contract. Call its effective model Terra only when session metadata matches Terra, and do not infer that the caller forced that assignment.
- Keep requirements, architecture, exact code edits, integration, and final acceptance with the controller.
- Send a stable diff to an independent child with the reviewer behavior contract for correctness, regression, race, test-gap, and security analysis. Treat `reviewer` session metadata as a role-label match, not custom-profile provenance.
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
6. Do not replace the built-in `default` role merely to force routing. Reconsider only on a future build that exposes the selected profile/config provenance and after policy intentionally prohibits every generic child from writing. An accidental override can disable legitimate isolated workers.
7. Keep role files when the current internal surface cannot explicitly name them, but report them as intended profiles until session metadata exposes selected profile/config provenance and use an audited fallback meanwhile.

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
The supplied role TOMLs are configuration templates, not proof of effective child routing.

## Use explicit standalone-pod authorization

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

Read [references/live-pod-validation-v1.0.3.json](references/live-pod-validation-v1.0.3.json)
before citing the v1.0.3 inheritance or sandbox observations. It is a sanitized,
unsigned local evidence record, not proof for another host.

## Orchestrate in waves

1. Define each child task with objective, scope, exclusions, evidence format, and completion criteria.
2. Launch all independent children before waiting. Continue in the controller only with non-overlapping work.
   When exact child model/reasoning matters and internal spawn cannot express it, use an explicitly authorized standalone support task instead of silently accepting inheritance.
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
- Every exact scout claim is backed by the effective model, reasoning level, sandbox, and named-role evidence the claim requires; otherwise label it only as a behavior contract.
- Every exact reviewer claim is backed by its effective stronger configuration and named-role evidence; otherwise label it only as a behavior contract.
- Any configured agent type being claimed is selectable in the active tool schema and recorded in the child session.
- The workflow does not require an acceleration, service tier, or credit mode unavailable to the account.
- Shared-tree scouts and reviewers created no diff or tracked artifacts.
- Every pre-existing change remains present and has a known owner after an in-flight cutover.
- The controller ran the repository's required tests and completion gates.
- A bug fix is tied to root-cause evidence and a regression test, or records why a deterministic regression test is impossible.
- A restore path exists for every modified configuration file.

When the child tool surface does not report effective model fields, embed a
unique `ROUTING-DISPATCH-<UUID>` marker in the initial task prompt and run
`scripts/verify_subagent_session.py <child-thread-id> --dispatch-marker <marker>`.
Use only its redacted model/reasoning/parent/sandbox output. This can show
inheritance in the local rollout record; it does not prove that a custom
profile was selected. Use an authorized standalone task when exact
model/reasoning is required. Treat its role prompt as a behavioral contract,
not proof of custom-profile selection.

For a fail-closed local diagnostic, record one JSON manifest per concurrent
dispatch wave and run
`scripts/validate_subagent_routing.py <manifest.json>`. The validator applies
`references/routing-policy-v1.json`, checks the attested role preconditions and
their evidence pointers, and compares the intended route with the effective
session metadata. The manifest must also record every surface's observed
callable fields and an evidence pointer in `surface_capabilities` and
`surface_capability_evidence`. Each dispatch must include unique dispatch and
child IDs; a canonical `ROUTING-DISPATCH-<UUID>` marker; role; surface; parent
where applicable; intended model/reasoning and policy-required sandbox; flags;
and `flag_evidence`. Embed the exact marker in the initial prompt. The manifest
also requires `controller_thread_id`. Pod waves require aggregate
`wave_capacity`, per-pod independent-part and slot evidence, and every high-risk
reviewer must name its `reviewed_dispatch_ids`. Writers also require a unique
`workspace_id`; sequential
writers belong in separate wave manifests. Any high-risk flag requires a
matching `high-risk-reviewer` dispatch in the same wave.

The bundled policy is a versioned baseline for the verified GPT-5.6 host, not
model-availability evidence for another computer. Copy and adapt it after the
host audit, then pass the copy with `--policy`; do not silently rewrite the
installed Skill's reference policy for one project.

The output deliberately separates:

- `attested_preconditions_passed`: the declared facts satisfy policy;
- `session_identity_passed`: exact session ID, source, parent, marker, and
  parse integrity match;
- `effective_model_match_passed`: the identity-bound effective model and reasoning match, whether inherited, opaque, or caller-controlled;
- `sandbox_status`: `verified`, `failed`, or `not_pinned`;
- `sandbox_passed`: `true` or `false` only when policy pins one, otherwise `null`;
- `profile_consistency_passed`: policy, identity, effective model/reasoning, and any pinned sandbox match;
- `role_label_match`: session metadata contains exactly the expected role label;
- `caller_model_control_attested` and `caller_role_control_attested`: the recorded caller schema exposes the corresponding fields;
- `caller_model_controls_consistent`: caller model controls were recorded and the effective model/reasoning match; this still does not prove which values the caller passed;
- `custom_profile_proven`: whether profile/config provenance was recorded; this remains false on the verified schema;
- `diagnostic_passed`: the local policy/profile consistency check passed.

Do not relabel a behavior-only support task as a custom profile merely because
its effective settings or role label match. A task claim or UI label never substitutes for
session metadata. The manifest, evidence pointers, and local rollout files are
mutable and unsigned; this tool catches consistency errors but is not a
cryptographic attestation. An independent reviewer must open decisive evidence.

The validator regression suite is:

```powershell
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

Before widening rollout, also keep a human-labeled set of at least 10 real task
examples and compare the selected role with the expected role. Require 100%
recall for high-risk triggers; unit tests alone do not prove semantic routing
accuracy on new task descriptions.

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
