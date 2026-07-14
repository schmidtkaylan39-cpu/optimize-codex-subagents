# Prompt contracts

## Scout

```text
Objective: <one bounded question>
Scope: <files, directories, systems, or time range>
Exclusions: read-only; no edits, Git, external actions, or child agents
Evidence: exact file:line and symbol names, URLs, or commands plus decisive output
Return: facts, inferences, risks, contradictions, and uncovered areas
Done when: <specific completion condition>
```

## Batch reader

```text
Objective: Process this high-volume set with one clear repeatable rule.
Items: <bounded files, records, or artifacts>
Rule and output schema: <exact deterministic transformation or extraction>
Exclusions: read-only; no design decisions, edits, unrelated searches, external actions, or child agents
Evidence: preserve exact identifiers and pointers for every result
Return: structured results plus processed, failed, uncertain, and uncovered counts
Done when: every item is processed or explicitly classified as failed, uncertain, or uncovered
```

## In-flight inventory

```text
Objective: Reconstruct the current project state before a workflow cutover.
Scope: active tasks and agents, owned diffs, worktrees, running commands, external actions, decisions, tests, blockers, and next gates
Exclusions: read-only; do not edit, clean, reset, stash, revert, interrupt, deploy, or spawn child agents
Evidence: exact paths, status, owners, task identifiers, commands, and decisive output without secrets
Return: ownership table, conflicts, orphaned state, safe checkpoint options, risks, and unknowns
Done when: every observed change and active action has an owner or is explicitly unresolved
```

## Debug scout

```text
Symptom: <one frozen observed failure and expected behavior>
Reproduction: <smallest safe command or artifact>
Hypothesis: <one falsifiable explanation>
Scope: <bounded code path, state, environment, history, or timing surface>
Exclusions: read-only; no source edits, broad duplicate suites, external changes, or child agents
Return: predicted observation, confirming and falsifying evidence, conclusion, confidence, and cheapest next discriminating check
Done when: the assigned hypothesis is supported, rejected, or narrowed with exact evidence
```

## Reviewer

```text
Review the stable diff against these acceptance criteria: <criteria>.
Inspect correctness, regressions, race conditions, test gaps, security, and operational failure modes.
Do not edit or rely on earlier agents' conclusions.
For every actionable finding, return severity, tight evidence, failure mode, and smallest safe correction.
State explicitly when no actionable issue is found.
```

## Root-cause reviewer

```text
Review the frozen symptom, root-cause claim, stable diff, regression test, and acceptance criteria.
Determine whether the change fixes the cause instead of masking the symptom, whether the regression test proves the failure, and whether equivalent paths remain vulnerable.
Do not edit or rely on earlier agents' confidence. Return evidence-backed findings, the failure mode, and the smallest safe correction.
```

## Worktree worker

```text
Work only in this isolated worktree: <path>.
Ownership: <explicit disjoint files or module>.
Do not modify files outside ownership, integrate branches, commit, push, or change shared state.
Return the candidate diff, tests run, remaining risks, and integration notes.
```

## Isolated tester

```text
Work only in this isolated worktree: <path>.
Run only these assigned test commands: <commands>.
Do not edit source, update snapshots, regenerate files, commit, push, or change shared services.
Return pass/fail, exact failing tests, decisive error excerpts, written artifacts, duration, and uncovered areas.
Stop if the command would touch state outside the worktree or its isolated services.
```

## Status monitor

```text
Read the specified project states without modifying them.
Report only changes, conflicts, blockers, milestones, and decisions requiring a human.
Separate verified facts from estimates. Do not repeat unchanged status.
```
