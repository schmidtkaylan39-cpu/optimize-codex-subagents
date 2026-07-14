# Retrofitting an in-flight project

## Contents

1. Capture current state
2. Establish ownership
3. Choose a cutover boundary
4. Apply changes in layers
5. Validate the handoff

## Capture current state

Treat every unexplained file, process, agent, deployment, migration, and external action as owned work until proven otherwise.

Record without changing state:

- active tasks, agents, objectives, scopes, and last known status;
- working tree, index, untracked and generated files, branches, and worktrees;
- running or recently completed commands, tests, services, migrations, and deployments;
- accepted decisions, open hypotheses, blockers, user constraints, and completion gates;
- current configuration and hashes of files that may be changed.

Never clean the tree to simplify adoption. Preserve unrelated user and agent work.

## Establish ownership

Name one controller for the shared working tree. Map each active change, command, and external action to an owner. Resolve overlapping ownership before another write.

An already-running child does not inherit a newly installed Skill or changed instruction automatically. Let safe bounded work finish, interrupt only when continued work is riskier, or request a compact handoff at a message boundary. Do not interrupt a deployment, migration, or destructive external operation without its authorized owner and rollback plan.

## Choose a cutover boundary

Prefer a coherent checkpoint:

- a bounded investigation has returned;
- a small edit and its focused test are complete;
- a stable diff exists before review;
- an external operation has reached a documented safe pause point.

If immediate conflict prevention matters, impose the single-writer lease and task ownership through the current controller prompt now. Defer config reloads and broad policy edits until the checkpoint.

## Apply changes in layers

1. Apply prompt-level ownership, no-duplicate-work, and compact evidence rules.
2. Add or reconcile repository `AGENTS.md` at a safe edit point.
3. Adapt custom role files and global settings only after backup and compatibility checks.
4. Start a new task when Skill discovery, agent files, or global configuration must reload.
5. Hand off goal, current state, owned diffs, decisions, evidence, commands run, failures, and exact next gate. Do not carry raw history when a compact state packet is sufficient.

## Validate the handoff

Compare before and after inventories. Every pre-existing change must still exist and have an owner. Confirm the new controller is the only shared-tree writer, active children have bounded scopes, required tests still have one owner, and no deployment or external operation was orphaned.

Run the smallest relevant health check first. Run broad gates only after the current diff stabilizes. If ownership or state cannot be reconstructed, stop new writes and request the missing handoff instead of guessing.
