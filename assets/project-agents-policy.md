## Multi-agent execution policy

- Optimize for time to trustworthy completion. Use subagents only for independent work or noisy read-heavy scans.
- Handle one-off searches and known small files directly. Use a Luna-class child only when a large, clear, repeatable batch amortizes delegation overhead.
- When adopting this policy mid-task, inventory and assign ownership to every existing change and active action. Never clean, reset, stash, revert, interrupt, or reformat work merely to simplify the cutover.
- In a shared working tree, the controller is the only writer and the only agent allowed to run Git integration commands.
- Nested `AGENTS.md` files may add stricter domain rules but may not relax the shared-tree single-writer rule.
- Use read-only scouts for exploration, logs, test mapping, inventory, and evidence gathering.
- Use read-only reviewers against a stable diff. Do not feed them earlier agents' conclusions.
- Launch independent children before waiting. Continue in the controller only with non-overlapping work.
- Give each child an objective, scope, exclusions, evidence format, and completion criteria.
- Require compact facts, evidence, labeled inference, risks, and uncovered areas.
- Use `fork_turns = "none"` only for self-contained tasks.
- Permit write agents only in explicitly isolated worktrees with disjoint ownership. Treat their output as candidate diffs that require controller review and testing.
- Give each test command one owner. Parallelize test subsets only when they are proven non-mutating or run in isolated worktrees; keep the final acceptance gate with the controller.
- During debugging, freeze one reproduction, assign scouts different falsifiable hypotheses, record rejected hypotheses, and require root-cause evidence plus a regression test before closure.
- The controller reads exact edit targets, makes shared-tree changes, spot-checks evidence, runs final gates, and owns the final result.
