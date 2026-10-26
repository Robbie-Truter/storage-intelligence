# Storage Intelligence — Frontend Implementation TODO

Ordered implementation checklist derived from
[`frontend/FRONTEND_HANDOFF.md`](frontend/FRONTEND_HANDOFF.md). The handoff holds
the API contracts, types, and design detail; this file holds the work.

## Working agreements

- Work on `feature/frontend`; open the PR against `refactor/monorepo-structure`.
  Never target `master` (or a nonexistent `main`) without explicit approval.
- Implementation changes stay inside `frontend/`; this checklist at the repo
  root is the only file outside it in scope. Do not modify `backend/`,
  `mcp-server/`, CI, or Postman files.
- Backend source is authoritative (`backend/src/storage_intelligence_backend/`).
  Do not invent endpoints, params, response fields, or features. See handoff
  §2, §4, and §10.
- API keys live in React memory only. Never write them to
  `localStorage`, `sessionStorage`, cookies, IndexedDB, URLs, logs, or error
  messages. See handoff §9.
- No `dangerouslySetInnerHTML` for model output. No auto-executed cleanup. The
  only mutating request is `POST /api/cleanup/execute` with exactly `{ paths }`.
- Stay lean: create folders/files when a phase needs them. Do not pre-build
  unused abstractions or add Zustand, chart libraries, Vitest, or MSW.
- Avoid testing cleanup on real data; use disposable files in a temp directory.

Implementation note: Vite scaffolds a solution-style root `tsconfig.json`, where
`tsc --noEmit` can silently check nothing. Verify the typecheck script catches
an intentional type error; if it does not, use `tsc -b` for `typecheck` and note
the deviation in the PR.

---

## Phase 0 — Scaffold and toolchain

Goal: a running, Biome-clean, strictly typed Vite app with Tailwind, shadcn
primitives, aliases, env config, and scripts. No product UI yet.

- [x] Scaffold Vite React TS **in a temporary directory**, then copy the files
      into `frontend/`. Do not scaffold in place or let Vite clear the
      directory: `frontend/FRONTEND_HANDOFF.md` must survive.
- [x] Remove Vite demo content: `src/App.css`, `src/assets/react.svg`,
      `public/vite.svg`, and the demo markup in `App.tsx`.
- [x] Install runtime dependencies from handoff §3: `react`, `react-dom`,
      `react-router-dom`, `@tanstack/react-query`, `axios`, `framer-motion`,
      `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`.
- [x] Install dev dependencies from handoff §3: `@tailwindcss/vite`,
      `tailwindcss`, `@biomejs/biome`, and `@types/node`.
- [x] Remove the Vite template's ESLint packages and `eslint.config.js`; run
      `npx biome init` and commit `biome.json`. Do not install ESLint or
      Prettier.
- [x] Configure Tailwind v4: add `@tailwindcss/vite` to `vite.config.ts` and
      `@import "tailwindcss";` to `src/index.css`.
- [x] Initialize shadcn/ui with New York style and CSS variables, then add only:
      `button`, `card`, `input`, `label`, `textarea`, `select`, `checkbox`,
      `dialog`, `accordion`, `badge`, `skeleton`, `alert`, `progress`.
      Add `tooltip` in Phase 6 when the collapsed rail needs it.
- [x] Configure the `@/*` alias in `tsconfig.app.json` and
      `vite.config.ts` (`resolve.alias`), plus `src/vite-env.d.ts` typing for
      `VITE_API_BASE_URL`.
- [x] Enable strict TypeScript (`strict`, `noUnusedLocals`,
      `noUnusedParameters`, `noFallthroughCasesInSwitch`).
- [x] Add `src/lib/utils.ts` with the standard `cn()` helper.
- [x] Add scripts: `dev`, `build` (`tsc -b && vite build`), `preview`, `check`
      (`biome check .`), `check:write` (`biome check --write .`), `format`
      (`biome format --write .`), and `typecheck` (verify it actually checks
      `src`; see the note above).
- [x] Add `frontend/.env.example` with
      `VITE_API_BASE_URL=http://127.0.0.1:8000`; confirm `.env.local` is
      git-ignored and `.env.example` is committed.
- [x] Set a placeholder `App.tsx` and `main.tsx` entry point.

### Acceptance criteria

- [x] `npm install` completes and the lockfile is generated and tracked.
- [x] `npm run dev` serves the app on `http://localhost:5173`.
- [x] `npm run check`, `npm run typecheck`, and `npm run build` all pass.
- [x] An intentional type error makes `npm run typecheck` fail (prove the
      script is effective).
- [x] `frontend/FRONTEND_HANDOFF.md` is unchanged and present.
- [x] No demo assets remain and no dependencies beyond handoff §3 plus
      shadcn-managed Radix/animation packages were added.
- [x] No ESLint or Prettier packages/config remain; `biome.json` is committed.

---

## Phase 1 — API foundation, providers, and app shell

Goal: one HTTP layer, normalized errors, formatting helpers, providers, routing,
and a readiness-aware shell. No Home/Assistant product UI yet.

- [x] Create `src/lib/api/types.ts` with the interfaces from handoff §4.6.
- [x] Create `src/lib/api/errors.ts` implementing `getApiErrorMessage` per
      handoff §4.3: string detail, `{ tool, message }` detail, validation-array
      detail, non-JSON response, timeout (`ECONNABORTED`), and no response.
      Never include request bodies, keys, or secret-bearing URLs.
- [x] Create `src/lib/api/client.ts` with the `api` and `agentApi` Axios
      instances from handoff §6 (base URL from `VITE_API_BASE_URL` with the
      documented fallback, 30s/180s timeouts, `withCredentials: false`). Export
      the resolved base URL for Settings. No logging interceptors.
- [x] Create `src/lib/format.ts` for bytes, percent, Unix-seconds timestamps,
      counts, and empty extensions (`(none)`) per handoff §4.6.
- [x] Create `src/lib/api/keys.ts` with query keys from handoff §6 and a
      `toOptionalPath(value)` helper that trims and returns `undefined` for
      blank input.
- [x] Configure `QueryClient` defaults: `refetchOnWindowFocus: false`, one
      retry for cheap GETs, no retry for mutations or 4xx.
- [x] Implement `ThemeProvider`: `light` / `dark` / `system`, persisted under a
      single non-secret key, applied via the `dark` class, reacting to system
      changes.
- [x] Implement `SettingsProvider`: selected model id and per-provider API keys
      in React state; `setApiKey` / `clearApiKey` / `setModelId`. Never persist
      keys. Keep the model id in memory for v1 (simplest safe default).
- [x] Build `AppShell` with a sidebar and content outlet, plus `PageHeader`
      (title, description, actions). Keep the shell simple; collapse and mobile
      overlay are Phase 6.
- [x] Add routes `/`, `/assistant`, `/settings`, and `*` with a
      `NotFoundPage`; highlight the active nav item.
- [x] Implement `useReadiness` + `ReadinessBanner` per handoff §4.1/§8.1:
      healthy, degraded (503), and backend-unreachable states; poll every 30s
      and never block navigation.
- [x] Compose `QueryClientProvider`, theme, settings, and `BrowserRouter` in
      `App.tsx`/`main.tsx`.

### Acceptance criteria

- [ ] All four routes render through the shell; the active link is visible.
- [ ] With the backend down, the app still boots and shows an offline banner.
- [ ] With the backend up and MCP down, readiness shows degraded (503).
- [ ] Theme choice survives a reload; no API key appears in DevTools storage.
- [ ] Manually verify `getApiErrorMessage` with a string detail, an object
      detail, an array detail, a timeout, and no response.
- [x] `npm run check`, `npm run typecheck`, and `npm run build` pass.

---

## Phase 2 — Home dashboard

Goal: the five read-only disk views plus selection metadata, with strict
endpoint usage and per-section states. Reference handoff §8.1.

- [ ] Implement the path context bar: free-text absolute path, Apply on
      Enter/button, Reset, and helper text that blank means the backend's
      default (home).
- [ ] Add `useDiskUsage(path)` for `GET /api/disk/usage`, omitting `path` when
      blank.
- [ ] Add `useDirectoryUsage(path, 10)` for `GET /api/disk/directory` with
      `top_n=10`.
- [ ] Add `useFileCounts(path)` for `GET /api/disk/count`.
- [ ] Add `useFileInfo(selectedPath)` for `GET /api/disk/info`, enabled only
      when an entry is selected.
- [ ] Build the volume usage card from `DiskUsageResponse`: used/free/total,
      percent bar with CSS/shadcn `progress`, and the resolved `path`. Copy must
      say this is the whole volume containing the path, not the folder.
- [ ] Build "Largest immediate children" from `directory.entries`: ranked
      rows/bars, type icon, formatted size, and a note that directory sizes are
      recursive totals. Clicking a row selects it.
- [ ] Build "Files by extension" from `count.by_extension`: top ~8 groups, an
      aggregated remainder, `total_files`, and `(no extension)` handling.
- [ ] Build the selected-entry metadata card from `FileInfoResponse`: name,
      type, size, modified, created, extension. Note that a directory's
      `size_bytes` is the directory entry, not its contents. Include a clear
      action.
- [ ] Add per-section loading skeletons, empty states, and error states with
      Retry. A failed card must not blank the page.
- [ ] Add a CTA linking to `/assistant`.
- [ ] Do not add large/duplicate/stale/junk/empty panels: there are no REST
      endpoints for them (handoff §10).

### Acceptance criteria

- [ ] With a blank path, DevTools shows no `path=` query parameter.
- [ ] With the backend up, all five views load; totals and sizes format
      correctly.
- [ ] Selecting an entry fetches `/api/disk/info` and shows Unix-second
      timestamps correctly.
- [ ] With the backend down, each section shows its own actionable error/Retry
      while the page remains usable.
- [ ] Only the documented disk endpoints are called.
- [ ] `npm run check`, `npm run typecheck`, and `npm run build` pass.

---

## Phase 3 — Settings

Goal: theme, model selection, and in-memory keys with explicit privacy copy.
Reference handoff §8.3.

- [ ] Add `useModels` for `GET /api/agent/models` with `staleTime: Infinity`,
      `gcTime: 1h`, and no polling.
- [ ] Build the model selector: label plus provider and `Local`/`Cloud`,
      defaulting to the first returned entry. Handle an empty/error list
      without hardcoding ids.
- [ ] Derive the provider list from the fetched models; render a password field
      for every provider except `ollama`, each with reveal and clear controls.
- [ ] Wire fields to `SettingsProvider`; confirm no key value is written to any
      storage, URL, or log.
- [ ] Add the theme selector (light/dark/system) bound to `ThemeProvider`.
- [ ] Display readiness and the resolved API base URL.
- [ ] Add the privacy notice: cloud providers receive tool results (paths,
      names, sizes); Ollama keeps analysis local; keys are lost on reload; the
      backend stores nothing; preferences are local-only.
- [ ] Show that Ollama models need no key.

### Acceptance criteria

- [ ] The model list comes from the backend; no model id or count is hardcoded.
- [ ] Settings shows Local/Cloud, and the Ollama key field is absent.
- [ ] DevTools Application storage contains theme only; no key material.
- [ ] A models request failure shows a retryable error.
- [ ] `npm run check`, `npm run typecheck`, and `npm run build` pass.

---

## Phase 4 — AI Assistant

Goal: one-shot analysis with a readable summary and a complete tool-call
timeline. Reference handoff §8.2 and §4.5.

- [ ] Add `useAnalyze` using `agentApi` and `POST /api/agent/analyze`. Build the
      body with `model`, trimmed `question`/`path` only when non-empty, and
      `api_key` only when it is non-empty and the provider is not `ollama`.
- [ ] Build the composer: path, question, model indicator, and key-readiness
      indicator. Require a model; allow blank question/path (backend defaults).
- [ ] Send flow: disable duplicate sends, show honest progress copy ("Analyzing…
      this can take up to a minute"), and keep the composer contents on error.
- [ ] Keep a session-only display history; label it "Conversations aren't
      saved" and make clear each send is independent.
- [ ] Render `summary` as plain text with newlines preserved
      (`white-space: pre-wrap`). No HTML/Markdown injection.
- [ ] Build the tool-call timeline as accordions: tool name, a safe args
      summary, and an `ok`/`error` badge.
- [ ] Add guarded renderers for every shape in handoff §4.5:
      `preview_trash`, `directory_disk_usage`, `disk_usage`,
      `explore_directory`, `count_files`, `file_info`, `find_large_files`,
      `find_duplicate_files`, `find_stale_files`, `find_empty_directories`,
      `find_junk_files`.
- [ ] Render any unknown or malformed `result` as pretty-printed JSON inside
      the accordion; never crash the page.
- [ ] Render `status: "error"` calls as failed steps with the tool's error
      text.
- [ ] Have the `preview_trash` renderer expose its `paths` for Phase 5
      selection; do not execute anything in this phase.
- [ ] Map 400/422/503 errors through `getApiErrorMessage`; keep messages free
      of keys and bodies.
- [ ] Add `aria-live="polite"` for the result/status region.
- [ ] Never render provider keys.

### Acceptance criteria

- [ ] A cloud model with a key and an Ollama model without a key both run.
- [ ] Every tool shape renders; an unknown shape falls back to JSON.
- [ ] A tool with `status: "error"` shows as a failed step.
- [ ] Unsupported model and missing key show actionable messages; MCP-down 503
      is distinct; composer contents survive failures.
- [ ] No cleanup runs automatically from model output.
- [ ] `npm run check`, `npm run typecheck`, and `npm run build` pass.

---

## Phase 5 — Shared cleanup review

Goal: exact-path, human-confirmed moves to the system trash, with clear results.
Reference handoff §8.4 and §10.

- [ ] Create `CleanupProvider` holding cleanup candidates (`path` plus optional
      `size_bytes`/`type`), dialog state, and the submit action; render exactly
      one `CleanupReviewDialog` in the shell. Submit only the candidate paths.
- [ ] In the Assistant `preview_trash` renderer, add per-path checkboxes and a
      "Review cleanup (N)" action that opens the dialog with only the checked
      paths. No select-all.
- [ ] Add one Home entry point per handoff §8.4/§10: from the selected entry
      card, "Add to cleanup review" with that single path. No bulk actions.
- [ ] Dialog content: exact paths, count, and known size/type where available;
      a warning that there is no protected-system-path guard.
- [ ] Require an explicit acknowledgement checkbox; keep "Move to Trash"
      disabled until checked. State clearly that there is no undo.
- [ ] Implement `useCleanupExecute` calling `POST /api/cleanup/execute` with
      exactly `{ paths }`. Never send `confirm` or extra fields. Disable the
      button while pending.
- [ ] Render outcomes separately: `deleted`, `failed` (path + error),
      `missing_paths` (already gone), and the summary count.
- [ ] On success, invalidate every `["disk"]` query and clear the selection.
- [ ] Provide distinct error states for a 400 (all paths missing/invalid) and a
      503 (MCP unavailable).
- [ ] Never derive cleanup paths from prose summaries; only structured
      `preview_trash`/`find_*` results or an explicitly selected entry.

### Acceptance criteria

- [ ] Cleanup cannot execute without the acknowledgement gate.
- [ ] The request body is exactly `{ "paths": [...] }` (verify in DevTools).
- [ ] Results group deleted, failed, and missing correctly.
- [ ] Disk queries refetch after success and the UI reflects the change.
- [ ] No automatic execution and no fabricated paths.
- [ ] `npm run check`, `npm run typecheck`, and `npm run build` pass.

---

## Phase 6 — Responsive design, accessibility, and polish

Goal: usable at mobile and desktop widths, keyboard accessible, motion-safe,
and consistent in tone. Reference handoff §7.

- [ ] Make Home and Assistant layouts responsive: single column on mobile,
      multi-column cards on desktop; no horizontal overflow at 375px.
- [ ] Implement the mobile sidebar as an off-canvas overlay with backdrop,
      Escape handling, focus trap, and close-on-navigation.
- [ ] Implement the desktop collapsed icon rail with accessible tooltips
      (add the `tooltip` primitive), and persist the collapsed preference.
- [ ] Use Framer Motion for sidebar/overlay and page/message transitions per
      handoff §7.
- [ ] Respect `prefers-reduced-motion` via `useReducedMotion()`; disable
      transforms while keeping content changes clear.
- [ ] Keyboard pass: entries selectable via buttons, accordions operable,
      dialog focus moves in and restores on close, visible focus rings
      throughout.
- [ ] Give every icon-only button an accessible name; connect dialog titles and
      descriptions; keep `aria-live` on assistant results.
- [ ] Handle long paths with truncation plus a title/tooltip, and keep large
      sizes/counts from breaking layout.
- [ ] Copy review: "Move to Trash" (never "delete permanently"), volume-vs-folder
      caveat, session-only conversations, keys lost on reload, cloud privacy.
- [ ] Check contrast in both themes; adjust tokens rather than hardcoding
      one-off colors.
- [ ] Cover edge cases: zero entries, empty extension map, huge counts,
      truncated `explore_directory` tool results, MCP down, backend down,
      timeouts.

### Acceptance criteria

- [ ] At 375px, 768px, and 1280px there is no horizontal scrolling or clipped
      controls.
- [ ] The full Home → Assistant → Settings → cleanup flow works with a
      keyboard alone.
- [ ] Mobile sidebar traps focus and restores it; desktop collapse persists.
- [ ] Reduced-motion preference removes non-essential motion.
- [ ] Both themes pass a visual contrast check, and the copy matches the
      approved safety language.

---

## Phase 7 — Final verification and documentation

Goal: prove the build, the contracts, and the safety invariants, then prepare
the PR. Reference handoff §13.

### Automated checks

- [ ] `npm run check` passes with no diagnostics.
- [ ] `npm run typecheck` passes and is proven to check `src` sources.
- [ ] `npm run build` succeeds; run `npm run preview` and smoke-test the
      production bundle.
- [ ] Confirm the build works from a clean install (`npm ci`).
- [ ] Search `frontend/src`: no `dangerouslySetInnerHTML`.
- [ ] Search `frontend/src`: no hardcoded model ids/labels/counts.
- [ ] Confirm Axios is imported only under `src/lib/api/`.
- [ ] Confirm API keys are never passed to storage, URLs, logs, or error text.

### Manual matrix

Prerequisites: backend running at `127.0.0.1:8000`; CORS allows the actual Vite
origin (normally `http://localhost:5173`, or a Vite proxy is configured); MCP
connected; a cloud key or a running Ollama model available.

- [ ] Boot with the backend down: shell renders, offline banner appears, no
      unhandled error.
- [ ] Healthy backend and MCP-down backend show distinct readiness states.
- [ ] Blank path sends no `path=` parameter.
- [ ] Home loads volume usage, largest children, extension counts, path
      context, and info-on-selection with correct formatting.
- [ ] Settings lists backend models; cloud and Ollama paths work; DevTools
      storage contains no keys.
- [ ] Assistant works with a cloud key and with Ollama without a key.
- [ ] All tool-result renderers display; error-status calls and unknown shapes
      behave safely.
- [ ] Error envelopes: unsupported model, missing key, validation error, and
      MCP-down 503 each show a sensible message (step-limit 400 if
      reproducible).
- [ ] Cleanup from the Assistant: gate, exact body, deleted/failed/missing
      display, disk refresh. Use disposable temp files only.
- [ ] Cleanup from Home: single selected path, same gate and results.
- [ ] No endpoint or response field is used that does not exist in handoff §4.

### Documentation and handoff

- [ ] Add `frontend/README.md` with install, dev/build, env var, CORS, scripts,
      key-handling, and cleanup-safety notes. Keep it durable package docs; do
      not duplicate the handoff.
- [ ] Leave `frontend/FRONTEND_HANDOFF.md` as the build snapshot; update it only
      if the user approves a contract change.
- [ ] Confirm `git status` shows only `frontend/`, `frontend-todo.md`, and
      approved changes — no backend, MCP, CI, or Postman edits.
- [ ] Open the PR against `refactor/monorepo-structure` (not `master`) with a
      summary of checks and the manual matrix results.

### Acceptance criteria

- [ ] All automated checks pass from a clean install.
- [ ] Every manual matrix item is verified and noted in the PR.
- [ ] Safety invariants from handoff §9 hold (keys in memory, no HTML
      injection, no auto-cleanup, exact `{ paths }`, no invented endpoints).
- [ ] The diff is frontend-scoped (`frontend/` plus this checklist) and the PR
      targets the integration branch.
