---
description: Sequential multi-agent handoff — todo-reader produces a full build brief for the next unfinished item in BACKEND_HANDOFF.md, builder executes it and ticks it. One item per run.
---

Run a two-step sequential handoff to complete exactly ONE todo item from `BACKEND_HANDOFF.md`.

**Step 1 — scout.** Use the Task tool with subagent_type `todo-reader`. Task: "Produce the build brief for the next unfinished item in BACKEND_HANDOFF.md, per your instructions." No other work.

**Step 2 — check.** If the scout returned `ALL_DONE`, report "All items in BACKEND_HANDOFF.md are done" and stop. Do not invent work.

**Step 3 — build.** Use the Task tool with subagent_type `builder`. The task description must contain the scout's **entire brief verbatim** (ITEM through RISKS/UNKNOWN), followed by: "Read AGENTS.md for repo rules. Execute this brief only, run its VERIFY commands, tick only this item, then report."

If the brief contains an `UNKNOWN:` line, do not dispatch it — report the gap to the user and ask how to resolve it.

**Step 4 — relay.** Report the builder's summary (item id, what changed, files, verification, brief corrections) to the user. If verification failed, say so plainly.

Do not chain additional items in this run — the user invokes this command again for the next one.
