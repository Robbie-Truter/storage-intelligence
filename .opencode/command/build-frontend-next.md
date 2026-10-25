---
description: Sequential frontend handoff — frontend-todo-reader briefs the next unfinished checklist item in frontend/frontend-todo.md, then frontend-builder executes and ticks it. One item per run.
---

Run exactly one frontend handoff for the next unfinished checklist item in
`frontend/frontend-todo.md`. If the user supplied a phase, start at that phase:
`$ARGUMENTS`.

**Step 1 — scout.** Call the Task tool with `subagent_type:
frontend-todo-reader` and this task:

> Produce the build brief for the next unfinished checklist item in
> `frontend/frontend-todo.md` (or for the first unfinished item in the phase
> named here: `$ARGUMENTS`), following your instructions.
> Return the brief only.

**Step 2 — gate.** Read the scout result before dispatching anyone.

- If it is `ALL_DONE`, report that the frontend checklist is complete and stop.
- If it is `NEEDS_HUMAN`, list the manual items and stop; do not dispatch the
  builder.
- If `UNKNOWN:` is anything other than `none`, show the gap and stop; do not
  let the builder guess.
- If `MODE` is `build` and `TASKS:` does not contain exactly **one** unchecked
  item, stop and report the malformed brief; do not let the builder complete a
  whole phase.
- If `TASKS:` is empty and `MODE` is `verify`, continue to Step 3 so the
  builder can verify automated acceptance.

**Step 3 — build.** Call the Task tool with `subagent_type:
frontend-builder`. Pass the scout's **entire brief verbatim**, then append:

> Read `AGENTS.md`. Execute this brief only. Work only in `frontend/`. Implement
> exactly the single item in `TASKS` — do not implement sibling tasks and do not
> finish the phase. Run VERIFY from `frontend/`. Tick only that one item's
> checkbox plus any acceptance criterion this item alone proves. Do not touch
> backend, MCP, CI, or Postman files. Report exactly as your instructions
> require.

**Step 4 — relay.** Summarize the builder's report: files changed, verification
result, the one task ticked, remaining unchecked items in the phase, and any
remaining manual acceptance. If manual items remain, ask the user to verify
them; do not redispatch the same item.

Do not chain another item in this run. Invoke this command again for the next
item.
