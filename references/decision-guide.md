# Decision guide

## Contents

1. Role selection
2. Model and reasoning selection
3. Traditional Chinese UI labels
4. Profile without credit acceleration
5. Concurrency
6. Context inheritance
7. Execution waves
8. Measurement

## Role selection

| Work | Default owner | Reason |
| --- | --- | --- |
| Known small file, single fact, or one-off search | Controller | Delegation costs more than direct work |
| High-volume clear repeatable extraction | Luna-class batch reader | Amortize startup over many mechanical items |
| Cross-file discovery, logs, inventory, test mapping | Scout | Isolate noisy intermediate context |
| Requirements, architecture, exact edit | Controller | Preserve intent and ownership |
| Stable diff correctness review | Reviewer | Independent error detection |
| Security, concurrency, migration, financial invariants | Strong reviewer | Requires deeper reasoning |
| Parallel implementation | Worktree worker | Prevent shared-tree conflicts |
| Independent test subset | Non-mutating child or isolated worktree tester | Reduce wall time without shared artifacts |
| Final test and acceptance | Controller | One accountable result |

## Model and reasoning selection

Select by capability rather than price alone:

- Controller: strongest broadly capable model at `high` for routine large-project execution.
- Plan mode: `xhigh` for architecture, migrations, safety boundaries, or milestone planning.
- Batch reader: Luna-class model at `low` only for high-volume, clear, repeatable work with an objective output schema. Do not spawn it for a one-off lookup.
- Scout: Terra-class fast balanced model at `medium` for cross-file exploration, logs, data flow, test mapping, and bounded debugging hypotheses.
- Reviewer: strongest model at `high`; use `xhigh` only when failure has material safety, financial, security, or migration impact.
- Read-only status monitor: balanced model at `high` when synthesis matters, otherwise `medium`.

Current GPT-5.6 examples are Sol for the controller/reviewer and Terra for scouts. Treat these as examples, not hard requirements. Verify host availability.

## Traditional Chinese UI labels

On the currently observed Traditional Chinese Codex UI, reasoning levels are ordered from fastest/lightest to strongest/slowest as:

```text
快速 -> 中 -> 高 -> 極高 -> 最大 -> 超高
```

Their configuration values are:

| Chinese UI | Config value |
| --- | --- |
| 快速 | `low` |
| 中 | `medium` |
| 高 | `high` |
| 極高 | `xhigh` |
| 最大 | `max` |
| 超高 | `ultra` |

Treat translations as version-sensitive and verify the active UI after major releases. When communicating with a Traditional Chinese user, lead with the visible Chinese label and keep the config value only for implementation.

## Profile without credit acceleration

Do not require or recommend a speed-for-credits mode when the account cannot enable it. Do not compensate by lowering the controller to `medium`, which can increase review and debugging time, or by keeping every controller turn at `max` or `ultra`, which increases latency.

Use this baseline after verifying model availability:

| Work | Baseline |
| --- | --- |
| Human-selected daily controller | Sol `high` (高) |
| Plan mode | Sol `xhigh` (極高) |
| Known small file, single fact, or one-off search | Controller directly; no child |
| High-volume clear repeatable batch | Luna `low` (快速) |
| General scout | Terra `medium` (中) |
| General reviewer | Sol `high` (高) |
| High-risk reviewer | Sol `xhigh` (極高) |
| Hardest mostly indivisible reasoning problem | Sol `max` (最大), when depth matters more than speed |
| Complex work with several meaningful independent parts | Sol `ultra` (超高), when proactive delegation materially helps |

Most tasks need neither 最大 nor 超高. This Skill can request parallel children while the controller remains 高, so Ultra is not required merely to obtain delegation.

Recover wall-clock time through parallel independent discovery, compact context, one writer, single ownership for tests, stable-diff review, and root-cause regression testing. Once roles are installed and verified, the human keeps the controller at 高; Codex selects child roles without manual switching.

## Concurrency

Use the runtime's actual cap. Count the controller when the runtime does.

- Start with one or two children.
- Use three children only for three genuinely independent workstreams.
- Leave room for the controller and later review.
- Keep nesting depth at one unless recursive delegation is explicitly required and tested.
- More agents do not help when they share assumptions, touch the same files, or depend on the same result.

## Context inheritance

- Use `fork_turns = "none"` for independent verification, repository inventory, bounded log analysis, or tasks whose complete constraints fit in the child message.
- Fork a small number of recent turns when subtle user intent or decisions would be expensive or risky to restate.
- Avoid full-history forks for long threads unless the child truly needs the whole conversation.
- Include immutable project invariants directly or rely on an applicable project `AGENTS.md`.

## Execution waves

### Normal material change

1. Spawn one or two scouts.
2. Let the controller read foundational documents and exact edit targets.
3. Integrate evidence and implement as the sole shared-tree writer.
4. Run focused tests.
5. Spawn one reviewer against the stable diff.
6. Fix findings and run final gates.

### High-risk change

1. Spawn scouts for independent code paths or invariants.
2. Implement through the controller.
3. Spawn two reviewers in parallel:
   - Sol `xhigh` for security, safety, concurrency, and invariant review;
   - Sol `high` for regression, test-gap, compatibility, and operational review.
4. Reconcile only evidence-backed findings.
5. Run the full acceptance gate.

### Parallel writing

Do not use write agents in the shared working tree. Create separate worktrees, assign disjoint ownership, prohibit Git integration by workers, and treat every worker result as an untrusted candidate diff.

### Parallel testing

Assign each test command to exactly one owner. A read-only child may run a subset only after proving that the command does not write caches, snapshots, coverage, generated code, lockfiles, databases, or shared services. Otherwise run it in an isolated worktree with isolated build and service state. The controller still owns the final repository acceptance gate.

## Measurement

Measure the same representative tasks under the old and new workflow. Prefer medians over a single impressive run. Count a run as faster only if the final verified outcome meets the same acceptance criteria.
