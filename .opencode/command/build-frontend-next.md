---
description: Sequential frontend handoff — frontend-todo-reader briefs the next unfinished phase in frontend-todo.md, then frontend-builder executes and ticks it. One phase per run.
---

Run exactly one frontend handoff for the next unfinished phase in
`frontend-todo.md`. If the user supplied a phase, use it: `$ARGUMENTS`.

**Step 1 — scout.** Call the Task tool with `subagent_type:
frontend-todo-reader` and this task:

> Produce the build brief for the next unfinished phase in `frontend-todo.md`
> (or for the phase named here: `$ARGUMENTS`), following your instructions.
> Return the brief only.

**Step 2 — gate.** Read the scout result before dispatching anyone.

- If it is `ALL_DONE`, report that the frontend checklist is complete and stop.
- If it is `NEEDS_HUMAN`, list the manual items and stop; do not dispatch the
  builder.
- If `UNKNOWN:` is anything other than `none`, show the gap and stop; do not
  let the builder guess.
- If `TASKS:` is empty and `MODE` is `verify`, continue to Step 3 so the
  builder can verify automated acceptance.

**Step 3 — build.** Call the Task tool with `subagent_type:
frontend-builder`. Pass the scout's **entire brief verbatim**, then append:

> Read `AGENTS.md`. Execute this brief only. Work only in `frontend/` and
> `frontend-todo.md`. Run VERIFY from `frontend/`. Tick only the completed
> tasks and provable acceptance criteria. Do not touch backend, MCP, CI, or
> Postman files. Report exactly as your instructions require.

**Step 4 — relay.** Summarize the builder's report: files changed, verification
result, tasks ticked, and any remaining manual acceptance. If manual items
remain, ask the user to verify them; do not redispatch the same phase.

Do not chain another phase in this run. Invoke this command again for the next
phase.
