# Root-cause debugging

## Contents

1. Freeze the failure signal
2. Parallelize hypotheses
3. Maintain an evidence ledger
4. Fix the root cause
5. Review and close

## Freeze the failure signal

Define one observed failure, the expected behavior, the smallest safe reproduction command or artifact, and the acceptance test. Preserve exact errors, inputs, environment facts, and timing without copying secrets or excessive logs.

If the failure is intermittent, quantify frequency and capture the smallest useful trace. Do not start random edits before establishing what counts as reproduced and fixed.

## Parallelize hypotheses

Launch scouts only for independent, falsifiable questions. Useful scopes include:

- code path, state transition, and data-flow tracing;
- configuration, environment, dependency, or platform differences;
- version history, recent diff, concurrency, timing, and test behavior.

Give every scout the same frozen symptom and a different hypothesis. Require evidence that confirms or falsifies it. Do not let scouts edit the shared tree or each run the full suite.

## Maintain an evidence ledger

The controller keeps a compact table with hypothesis, predicted observation, evidence, result, confidence, and next discriminating check. Record rejected hypotheses so later agents do not repeat them.

Prefer the cheapest check that separates competing explanations. Compare known-good and failing cases, bisect when history is relevant, and instrument only the narrow path needed. Remove temporary instrumentation unless it is intentionally retained and tested.

## Fix the root cause

Make the smallest change that explains the evidence. Keep one writer. Add a focused regression test that fails before and passes after the fix. Run focused checks before any broad suite.

If the reproduction disappears without a causal explanation, report the uncertainty; do not label the issue fixed merely because one rerun passed.

## Review and close

Give an independent reviewer the frozen symptom, root-cause claim, stable diff, regression test, and acceptance criteria. Ask whether the change fixes the cause rather than masking the symptom, introduces new failure modes, or leaves an equivalent path untested.

Close only when the reproduction is resolved, the regression test passes, relevant final gates pass, temporary artifacts are accounted for, and the evidence ledger identifies why the fix works. If a deterministic regression test is genuinely impossible, document the reason and use an explicit statistical, integration, or operational acceptance check instead.
