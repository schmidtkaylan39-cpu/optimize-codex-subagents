# Decision guide

## Contents

1. Role selection
2. Model and reasoning selection
3. Routing-surface gate
4. Traditional Chinese UI labels
5. Profile without credit acceleration
6. Concurrency
7. Context inheritance
8. Execution waves
9. Measurement

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

Treat these as intended targets when the selected surface exposes model and
reasoning controls. Otherwise use the matching behavior contract and report the
effective inherited or opaque assignment without claiming caller routing:

- Controller: strongest broadly capable model at `high` for routine large-project execution.
- Plan mode: `xhigh` for architecture, migrations, safety boundaries, or milestone planning.
- Batch reader: Luna-class model at `low` only for high-volume, clear, repeatable work with an objective output schema. Do not spawn it for a one-off lookup.
- Scout: Terra-class fast balanced model at `medium` for cross-file exploration, logs, data flow, test mapping, and bounded debugging hypotheses.
- Reviewer: strongest model at `high`; use `xhigh` only when failure has material safety, financial, security, or migration impact.
- Read-only status monitor: balanced model at `high` when synthesis matters, otherwise `medium`.

Current GPT-5.6 examples are Sol for the controller/reviewer and Terra for scouts. Treat these as examples, not hard requirements. Verify host availability.

## Routing-surface gate

Model choice and task ownership are policy targets until the active tool proves it can enforce them.

- If `spawn_agent` exposes a supported named-role field, request the role and verify the role label and effective settings. Do not claim custom-TOML provenance unless metadata exposes the selected profile/config ID, path, or hash.
- If it exposes explicit model and reasoning fields, set them and verify the effective values.
- Some runtimes may make an opaque assignment for an unpinned child. That is not a caller routing capability.
- If it exposes only task name, message, and context fork, do not claim that a role prompt switched the child to Terra or Luna. The child may inherit the parent model; verify the session either way.
- Use an explicitly authorized short-lived standalone support task with `model` and `thinking` when exact model/reasoning is required. Integrate its result and archive it afterward; treat its role prompt as a behavioral contract, not proof of named-role identity.
- A generic child may still follow a scout or reviewer behavior contract. Report the behavior contract, effective model, role-label match, and custom-profile provenance as separate facts.

Run `scripts/verify_subagent_session.py` and `scripts/validate_subagent_routing.py` when local session evidence is available.
Embed a unique routing marker in each initial prompt, validate one concurrent
wave per manifest, give every writer a unique workspace ID, and require a
matching high-risk reviewer for every risk flag. Treat the result as an unsigned
local consistency check, not cryptographic attestation.

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

Use this intended baseline only after verifying both model availability and the selected surface's routing capability:

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

Most tasks need neither 最大 nor 超高. A controller at 高 can still request parallel children, but those internal children may inherit its model when the spawn schema has no model or role field.

Recover wall-clock time through parallel independent discovery, compact context, one writer, single ownership for tests, stable-diff review, and root-cause regression testing. Claim caller-controlled model routing only when the pre-dispatch schema exposes model/reasoning controls and post-dispatch effective settings match. Claim custom-profile selection only when metadata also exposes its provenance. Otherwise, use an authorized standalone support task for exact model/reasoning or report the internal child's inherited or opaque assignment.

## Concurrency

Use the runtime's actual cap. Count the controller when the runtime does.

- Start with one or two children.
- Use three children only for three genuinely independent workstreams.
- Leave room for the controller and later review.
- Keep nesting depth at one unless recursive delegation is explicitly required and tested.
- The recursion exception never applies to standalone support pods; pods always keep `max_depth = 1`.
- More agents do not help when they share assumptions, touch the same files, or depend on the same result.

### Bounded standalone pods

When exact model/reasoning and high parallel throughput both matter, flatten
model routing at the standalone-task layer and allow bounded fan-out below it:

- create the standalone pod with the exact audited model/reasoning;
- record live `available_child_slots` with evidence, then let the pod launch no more than `min(3, available_child_slots)` read-only internal children only for two or more substantial independent workstreams;
- give every child a disjoint scope and a complete leaf behavior contract;
- keep `max_depth = 1`, so children cannot spawn descendants or new standalone tasks;
- verify every child session. On the verified build children inherited the pod root, but observed inheritance is not caller-controlled routing and must not be promised on another build;
- if a child must have exact settings and mismatches, return that scope to the controller for a new exact standalone pod.

Use pods in waves. Discovery pods run before implementation; reviewer pods run
only after the diff is stable. Do not launch every role at once merely to raise
the agent count.

On the verified four-slot host, the main task, one standalone pod root, and two
pod children filled the working wave. Admit a third child only when current
capacity evidence shows another slot; do not infer standalone tasks use a
separate unlimited pool.
On that four-slot host, choose one Luna or Terra discovery pod per wave. Multiple
pod roots may run together only when aggregate host admission for the entire
wave passes; per-pod slot claims must not double-count the same capacity.

## Context inheritance

- Use `fork_turns = "none"` for independent verification, repository inventory, bounded log analysis, or tasks whose complete constraints fit in the child message.
- Fork a small number of recent turns when subtle user intent or decisions would be expensive or risky to restate.
- Avoid full-history forks for long threads unless the child truly needs the whole conversation.
- Include immutable project invariants directly or rely on an applicable project `AGENTS.md`.

## Execution waves

Role names below describe behavior contracts, not proven custom-profile routes.
For exact model/reasoning, use an authorized standalone support task or a
future internal surface that exposes those controls. Report effective settings,
role labels, and custom-profile provenance separately.

### Normal material change

1. Spawn one or two generic internal children with bounded scout behavior contracts, or use an authorized Terra/medium standalone pod with up to three read-only leaf children when exact settings and enough independent scope justify it.
2. Let the controller read foundational documents and exact edit targets.
3. Integrate evidence and implement as the sole shared-tree writer.
4. Run focused tests.
5. Spawn one generic internal child with the reviewer behavior contract against the stable diff, or use an authorized Sol/high standalone reviewer pod with disjoint read-only leaf reviews when exact settings matter.
6. Fix findings and run final gates.

### High-risk change

1. Spawn generic children with scout behavior contracts for independent code paths or invariants; report their effective settings.
2. Implement through the controller.
3. Spawn two children with different reviewer behavior contracts in parallel. If exact settings matter and separate support tasks are authorized, use:
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
