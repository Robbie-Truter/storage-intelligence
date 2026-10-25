# Storage Intelligence — Frontend Handoff

**Status:** build brief (greenfield)
**Date:** 2026-10-25
**Branch:** `feature/frontend` (clean tree, `frontend/` empty)
**Integration target:** `refactor/monorepo-structure`
**Audience:** the frontend builder agent / engineer

This is a **snapshot**, not a contract. The backend source is authoritative. If
this document and the code disagree, the code wins and this document gets fixed.

---

## 1. Scope

Build the React dashboard for the Storage Intelligence backend:

- **Home** — read-only storage overview (volume usage, largest children, file
  counts, path context, entry metadata).
- **AI Assistant** — question/answer over the read-only agent, with a visible
  tool-call timeline.
- **Settings** — theme, model selection, in-memory provider keys.
- **Shared cleanup review** — an explicit-path, explicitly-confirmed move to the
  system trash, reachable from Home and the Assistant.

Non-goals for v1:

- No new backend endpoints, and no changes to `backend/`, `mcp-server/`, CI, or
  the Postman collection as part of this work.
- No chat persistence, sessions, or streaming.
- No auth, accounts, or multi-user concerns.
- No deployment wiring (containers, hosting, reverse proxy).
- No charting library, no state-management library, no heavy UI kit.

---

## 2. Source of truth and precedence

Use this order when anything is ambiguous:

1. `backend/src/storage_intelligence_backend/schemas.py` (Pydantic models)
2. `backend/src/storage_intelligence_backend/routers/{health,disk,agent,cleanup}.py`
3. `backend/tests/`
4. A live `GET http://127.0.0.1:8000/openapi.json`
5. `backend/README.md`
6. `backend/postman/` collection

Supporting files:

| Concern                               | File                                                                 |
| ------------------------------------- | -------------------------------------------------------------------- |
| App factory, CORS, exception handlers | `backend/src/storage_intelligence_backend/main.py`                   |
| Settings + env prefix                 | `backend/src/storage_intelligence_backend/config.py`                 |
| Model catalogue                       | `backend/src/storage_intelligence_backend/agents/models.py`          |
| Agent run + tool-call records         | `backend/src/storage_intelligence_backend/agents/storage_agent.py`   |
| Read-only allowlist                   | `backend/src/storage_intelligence_backend/mcp/manager.py:42`         |
| Error types                           | `backend/src/storage_intelligence_backend/mcp/errors.py`             |
| MCP tool result shapes                | `mcp-server/src/storage_intelligence_mcp/utils.py`                   |
| MCP tool behaviour                    | `mcp-server/src/storage_intelligence_mcp/tools/{storage,cleanup}.py` |

Known documentation drift is catalogued in section 11. Do not code against the
drifted docs.

---

## 3. Stack and dependency decisions

- **React + Vite + TypeScript (strict)**
- **Tailwind CSS v4** via `@tailwindcss/vite`
- **shadcn/ui** (New York style, CSS variables, Tailwind v4 setup)
- **React Router** (`react-router-dom`) for routing
- **TanStack Query** for server state
- **Axios** for HTTP
- **Framer Motion** for motion
- **lucide-react** for icons
- **Biome** for linting and formatting (replaces ESLint/Prettier)
- npm as the package manager

Runtime dependencies:

```text
react
react-dom
react-router-dom
@tanstack/react-query
axios
framer-motion
lucide-react
class-variance-authority
clsx
tailwind-merge
```

Dev dependencies:

```text
vite
@vitejs/plugin-react
typescript
@tailwindcss/vite
tailwindcss
@biomejs/biome
@types/react
@types/react-dom
@types/node
```

Install Biome with `npm i -D -E @biomejs/biome`, then run `npx biome init` and
commit the generated `biome.json`. Biome replaces ESLint and Prettier; do not
install either.

Explicitly **do not** add: Zustand/Redux/Jotai, Recharts/Chart.js/D3, MUI/Chakra,
Vitest/RTL (deferred; see section 13), MSW, ESLint, Prettier, or any date
library beyond `Intl`.

Build the volume-usage and "largest children" visuals with CSS/SVG and shadcn
primitives (progress, cards, bars). No chart dependency in v1.

`package.json` scripts:

```json
{
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "check": "biome check .",
  "check:write": "biome check --write .",
  "format": "biome format --write .",
  "typecheck": "tsc --noEmit"
}
```

---

## 4. Backend contract snapshot

Base URL: `http://127.0.0.1:8000` (the backend binds `127.0.0.1:8000`).
Configure via `VITE_API_BASE_URL`; default `http://127.0.0.1:8000`.

### 4.1 Endpoint table

| Method | Route                  | Params / body                                                                        | Response                                                             |
| ------ | ---------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| GET    | `/health`              | none                                                                                 | `{ status }`                                                         |
| GET    | `/health/ready`        | none                                                                                 | 200 `{ status, mcp, tool_count }` or 503 `{ status, mcp, detail }`   |
| GET    | `/api/disk/usage`      | `path?`                                                                              | `{ path, total_bytes, used_bytes, free_bytes, usage_percent }`       |
| GET    | `/api/disk/directory`  | `path?`, `top_n=10`                                                                  | `{ path, entries: [{ name, type, size_bytes }] }`                    |
| GET    | `/api/disk/explore`    | `path?`, `pattern=""`, `search=""`, `kind=all`, `recursive=false`, `max_results=100` | `{ path, entries: [{ name, path, type }], truncated }`               |
| GET    | `/api/disk/count`      | `path?`                                                                              | `{ path, total_files, by_extension }`                                |
| GET    | `/api/disk/info`       | `path?`                                                                              | `{ name, path, type, size_bytes, modified, created, extension }`     |
| GET    | `/api/agent/models`    | none                                                                                 | `AgentModelOption[]`                                                 |
| POST   | `/api/agent/analyze`   | `{ model, api_key?, path?, question? }`                                              | `{ summary, tool_calls: [{ name, args, status, result }] }`          |
| POST   | `/api/cleanup/execute` | `{ paths: string[] }` (min 1, extra keys rejected)                                   | `{ mode, paths, deleted, failed, missing_paths, total_valid_paths }` |

Notes that affect the client:

- **Omit `path` entirely when blank.** Do not send `path=`. The routers omit the
  argument when it is `None`, and the MCP tool then applies its home-directory
  default. With Axios, pass `undefined` for a blank path; an empty string would
  be transmitted as `path=`.
- `GET /api/disk/usage` reports the **whole volume** containing `path`, not the
  directory. Label it "Volume usage", never "this folder uses X".
- `modified` and `created` are **Unix seconds** (floats), not ISO strings.
- `GET /api/disk/explore` `type` values are plain `"file"` / `"directory"`.
  (The MCP docstrings claim emoji-prefixed labels; the payload does not. Still
  normalize defensively — see section 5.)
- `GET /api/disk/info` returns metadata for **one file or directory**, despite
  the route docstring saying "whole volume". Trust `FileInfoResponse`.
- `POST /api/cleanup/execute` returns no `requires_confirmation` field; the
  Pydantic response model filters it out. Do not rely on it. The submitted paths
  are forwarded verbatim, but the MCP tool deduplicates and orders them deepest
  first, so the returned `paths` may differ from the submitted list.
- The only mutating route is `/api/cleanup/execute`. It forwards paths to the
  MCP `trash_path` tool with `confirm=True` and sends them to the system trash
  via `send2trash`. There is no undo.
- `/health/ready` `tool_count` is the count of **raw MCP tools** (currently 12),
  not the agent allowlist size (11). FastAPI serializes model defaults, so both
  `tool_count` and `detail` can appear even when unset (`detail: null` on 200,
  `tool_count: 0` on 503). Treat them as optional on the client.
- CORS defaults to `[]`. The dev origin must be configured; see section 9.

### 4.2 Request/response examples

```jsonc
// GET /health
{ "status": "ok" }

// GET /health/ready (200)
{ "status": "ok", "mcp": "ok", "tool_count": 12, "detail": null }

// GET /health/ready (503)
{
  "status": "unavailable",
  "mcp": "unavailable",
  "tool_count": 0,
  "detail": "MCP server is not connected"
}

// GET /api/disk/usage?path=/Users/me
{
  "path": "/Users/me",
  "total_bytes": 994662584320,
  "used_bytes": 812340000000,
  "free_bytes": 182322584320,
  "usage_percent": 81.7
}

// GET /api/disk/directory?path=/Users/me&top_n=5
{
  "path": "/Users/me",
  "entries": [
    { "name": "Downloads", "type": "directory", "size_bytes": 41234567 },
    { "name": "movie.mov", "type": "file", "size_bytes": 1048576 }
  ]
}

// GET /api/disk/explore?path=/Users/me&pattern=*.zip&kind=files
{
  "path": "/Users/me",
  "entries": [
    { "name": "old.zip", "path": "/Users/me/old.zip", "type": "file" }
  ],
  "truncated": false
}

// GET /api/disk/count?path=/Users/me/Downloads
{
  "path": "/Users/me/Downloads",
  "total_files": 128,
  "by_extension": { ".pdf": 41, ".zip": 12, "(no extension)": 3 }
}

// GET /api/disk/info?path=/Users/me/Downloads/old.zip
{
  "name": "old.zip",
  "path": "/Users/me/Downloads/old.zip",
  "type": "file",
  "size_bytes": 2024096,
  "modified": 1717089123.42,
  "created": 1710000000.0,
  "extension": ".zip"
}

// GET /api/agent/models
[
  {
    "id": "openai-gpt-4.1",
    "label": "GPT-4.1",
    "provider": "openai",
    "model_name": "gpt-4.1",
    "mode": "cloud"
  },
  {
    "id": "ollama-llama3.1",
    "label": "Llama 3.1 (Ollama)",
    "provider": "ollama",
    "model_name": "llama3.1",
    "mode": "local"
  }
]

// POST /api/agent/analyze
{
  "model": "openai-gpt-4.1",
  "api_key": "sk-...",
  "path": "/Users/me/Downloads",
  "question": "What is taking the most space?"
}

// 200
{
  "summary": "The largest item is ...",
  "tool_calls": [
    {
      "name": "directory_disk_usage",
      "args": { "path": "/Users/me/Downloads" },
      "status": "ok",
      "result": { "path": "/Users/me/Downloads", "entries": [] }
    }
  ]
}

// POST /api/cleanup/execute
{ "paths": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"] }

// 200
{
  "mode": "executed",
  "paths": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"],
  "deleted": ["/Users/me/Downloads/old.zip", "/Users/me/Downloads/tmp"],
  "failed": [],
  "missing_paths": [],
  "total_valid_paths": 2
}
```

### 4.3 Error envelopes

Error bodies are **not uniform**. Normalize them in one place
(`lib/api/errors.ts`) and never index into `detail` blindly.

| Condition                                                       | Status | `detail` shape                               |
| --------------------------------------------------------------- | ------ | -------------------------------------------- |
| MCP tool returned an error                                      | 400    | object `{ tool, message }`                   |
| Agent hit its step limit                                        | 400    | string                                       |
| Unsupported model id                                            | 422    | string                                       |
| Cloud model without `api_key`                                   | 422    | string                                       |
| Agent model could not be built                                  | 503    | string `"Agent model is not available: ..."` |
| MCP unavailable                                                 | 503    | string `"MCP server is not available"`       |
| FastAPI request validation (including cleanup `extra="forbid"`) | 422    | array of validation objects                  |
| Network/CORS/timeout                                            | —      | no body; synthesize a client error           |

Contract for `getApiErrorMessage(error: unknown): string`:

- Axios error with a response:
  - `detail` is a string → return it.
  - `detail` is an object with `message` → return `message` (optionally prefix
    with `tool`).
  - `detail` is an array → join item `msg` values (fall back to "Invalid
    request").
- Response with no parseable body → `Request failed (HTTP <status>)`.
- `error.code === "ECONNABORTED"` → `The request timed out.`
- No response at all → `Cannot reach the backend. Is it running?`
- Never include the API key, request body, or full URL with secrets in the
  message or logs.

### 4.4 Model catalogue (snapshot — never hardcode)

`GET /api/agent/models` currently returns 7 entries
(`backend/src/storage_intelligence_backend/agents/models.py:20`):

| id                             | label                        | provider     | mode  |
| ------------------------------ | ---------------------------- | ------------ | ----- |
| `openai-gpt-4.1`               | GPT-4.1                      | openai       | cloud |
| `openai-gpt-4.1-mini`          | GPT-4.1 Mini                 | openai       | cloud |
| `google-gemini-3.7-flash`      | Gemini 3.7 Flash (Free Tier) | google_genai | cloud |
| `google-gemini-3.1-flash-lite` | Gemini 3.1 Flash-Lite        | google_genai | cloud |
| `google-gemini-2.5-flash`      | Gemini 2.5 Flash             | google_genai | cloud |
| `ollama-llama3.1`              | Llama 3.1 (Ollama)           | ollama       | local |
| `ollama-qwen3-8b`              | Qwen3 8B (Ollama)            | ollama       | local |

Rules:

- Fetch at runtime; never hardcode ids, labels, or the count.
- Group/annotate with `provider` and `mode`; show "Local" vs "Cloud".
- `api_key` is required when `provider !== "ollama"`; unused for Ollama.
- Provider keys are sent per request and never stored by the backend.

### 4.5 MCP tool-result shapes (rendered from `tool_calls[].result`)

`AgentToolCall.result` is typed `unknown`. Each renderer must validate the shape
it expects and fall back to a pretty-printed JSON accordion.

```jsonc
// preview_trash
{
  "mode": "preview",
  "requires_confirmation": true,
  "paths": ["/Users/me/a", "/Users/me/b"],
  "missing_paths": [],
  "total_valid_paths": 2,
  "message": "Preview only: ..."
}

// directory_disk_usage
{ "path": "/Users/me", "entries": [{ "name": "Downloads", "type": "directory", "size_bytes": 123 }] }

// disk_usage
{ "path": "/Users/me", "total_bytes": 0, "used_bytes": 0, "free_bytes": 0, "usage_percent": 0.0 }

// explore_directory
{ "path": "/Users/me", "entries": [{ "name": "a", "path": "/Users/me/a", "type": "file" }], "truncated": false }

// count_files
{ "path": "/Users/me", "total_files": 10, "by_extension": { ".py": 7 } }

// file_info
{ "name": "a", "path": "/Users/me/a", "type": "file", "size_bytes": 1, "modified": 0.0, "created": 0.0, "extension": "" }

// find_large_files
[{ "path": "/Users/me/big.iso", "size_bytes": 123, "size_mb": 0.1 }]

// find_duplicate_files
[{ "size_bytes": 123, "files": ["/a", "/b"] }]

// find_stale_files
[{ "path": "/Users/me/old.txt", "size_bytes": 12, "days_unmodified": 400.2 }]

// find_empty_directories
{
  "path": "/Users/me",
  "recursive": true,
  "total_empty_directories": 3,
  "sample": ["/Users/me/a/b"],
  "truncated": false,
  "skipped_directories_count": 0,
  "skipped_directories": []
}

// find_junk_files
{
  "path": "/Users/me/proj",
  "total_files": 4,
  "by_extension": { ".log": 3, ".ds_store": 1 },
  "directories": ["/Users/me/proj/node_modules"],
  "sample": ["/Users/me/proj/a.log"],
  "truncated": false
}
```

Errors inside the agent are reported on the call, not thrown:
`status: "error"` and `result` is the tool's error text string. Render it as a
failed step, not a crash.

### 4.6 TypeScript types mirroring the Pydantic models

```ts
export type DiskEntryType = "file" | "directory";

export interface HealthResponse {
  status: string;
}

export interface ReadinessResponse {
  status: string;
  mcp: string;
  tool_count?: number;
  detail?: string | null;
}

export interface DiskUsageResponse {
  path: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  usage_percent: number;
}

export interface DirectoryUsageEntry {
  name: string;
  type: DiskEntryType;
  size_bytes: number;
}

export interface DirectoryDiskUsageResponse {
  path: string;
  entries: DirectoryUsageEntry[];
}

export interface ExploreDirectoryEntry {
  name: string;
  path: string;
  type: string;
}

export interface ExploreDirectoryResponse {
  path: string;
  entries: ExploreDirectoryEntry[];
  truncated: boolean;
}

export interface CountFilesResponse {
  path: string;
  total_files: number;
  by_extension: Record<string, number>;
}

export interface FileInfoResponse {
  name: string;
  path: string;
  type: DiskEntryType;
  size_bytes: number;
  modified: number; // Unix seconds
  created: number; // Unix seconds
  extension: string;
}

export interface AgentModelOption {
  id: string;
  label: string;
  provider: string;
  model_name: string;
  mode: "cloud" | "local" | string;
}

export interface AgentAnalyzeRequest {
  model: string;
  api_key?: string;
  path?: string;
  question?: string;
}

export interface AgentToolCall {
  name: string;
  args: Record<string, unknown>;
  status: "ok" | "error";
  result: unknown;
}

export interface AgentAnalyzeResponse {
  summary: string;
  tool_calls: AgentToolCall[];
}

export interface CleanupExecuteRequest {
  paths: string[];
}

export interface CleanupFailure {
  path: string;
  error: string;
}

export interface CleanupExecuteResponse {
  mode: string;
  paths: string[];
  deleted: string[];
  failed: CleanupFailure[];
  missing_paths: string[];
  total_valid_paths: number;
}
```

Formatting rules (`lib/format.ts`):

- Bytes: binary units (`B`, `KB`, `MB`, `GB`, `TB`), 1–2 decimals.
- Percent: one decimal, matching the backend.
- Timestamps: `new Date(seconds * 1000)`, formatted with
  `Intl.DateTimeFormat`; show invalid values as `—`.
- Large counts: `Intl.NumberFormat`.
- Empty strings / `""` extension → `(none)`.

---

## 5. Frontend architecture

```text
frontend/
├── .env.example
├── components.json
├── index.html
├── package.json
├── biome.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── lib/
    │   ├── api/client.ts
    │   ├── api/errors.ts
    │   ├── api/types.ts
    │   ├── format.ts
    │   └── utils.ts
    ├── components/
    │   ├── ui/                 # shadcn generated
    │   ├── layout/             # AppShell, Sidebar, PageHeader
    │   └── common/             # QueryState, EmptyState, ErrorState, Skeletons
    ├── providers/              # QueryClient, Theme, Settings
    ├── features/
    │   ├── health/             # api, hooks, ReadinessBanner
    │   ├── disk/               # api, hooks, keys, dashboard components
    │   ├── assistant/          # api, hooks, chat + tool-result components
    │   ├── cleanup/            # api, hooks, CleanupReviewDialog
    │   └── settings/           # models query, settings components
    └── pages/
        ├── HomePage.tsx
        ├── AssistantPage.tsx
        ├── SettingsPage.tsx
        └── NotFoundPage.tsx
```

Rules:

- Feature folders own their API calls, hooks, keys, and components.
- Presentational components never call Axios. Pages/hooks call feature hooks.
- Shared code only when genuinely reused; do not create a rigid layer stack.
- `components/ui` is generated by shadcn; avoid hand-editing unless necessary.

TypeScript: `strict: true`, `noUnusedLocals`, `noUnusedParameters`,
`noFallthroughCasesInSwitch`, `verbatimModuleSyntax` as appropriate. Use the
`@/*` path alias configured in both `tsconfig` and `vite.config.ts`.

---

## 6. API client and query strategy

`lib/api/client.ts`:

```ts
import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL,
  timeout: 30_000,
  withCredentials: false,
});

export const agentApi = axios.create({
  baseURL,
  timeout: 180_000, // agent runs can take a while; no streaming in v1
  withCredentials: false,
});
```

- Never log request bodies for `/api/agent/analyze` or any request carrying a key.
- Never put the key in a URL, query string, or error message.
- No interceptors that echo config (headers include the key).
- Trim inputs and convert `""` → `undefined` before building params.

Query keys:

```ts
["health", "ready"][("disk", "usage", path ?? null)][
  ("disk", "directory", path ?? null, topN)
][("disk", "explore", { path, pattern, search, kind, recursive, maxResults })][
  ("disk", "count", path ?? null)
][("disk", "info", path ?? null)][("agent", "models")];
```

Cache settings:

| Query             | staleTime  | gcTime | Refetch                          |
| ----------------- | ---------- | ------ | -------------------------------- |
| readiness         | 10s        | 60s    | `refetchInterval: 30_000`        |
| disk usage        | 60s        | 5m     | no                               |
| directory         | 5m         | 10m    | no (recursive scan is expensive) |
| explore           | 60s        | 5m     | no                               |
| count             | 2m         | 5m     | no                               |
| info              | 60s        | 5m     | no                               |
| models            | `Infinity` | 1h     | no                               |
| analyze / cleanup | mutation   | n/a    | `retry: 0`                       |

Global `QueryClient` defaults:

- `refetchOnWindowFocus: false` for disk queries (and preferably globally).
- One retry for cheap GETs; zero retries for mutations and 4xx responses.
- Do not cache analyze responses or selections in Query Cache.

After a successful cleanup:

```ts
queryClient.invalidateQueries({ queryKey: ["disk"] });
```

Use `ExploreDirectoryResponse.truncated` to show "showing the first N matches",
not pagination. The API has no offset.

---

## 7. App shell and design

Routes:

```text
/           HomePage
/assistant  AssistantPage
/settings   SettingsPage
*           NotFoundPage
```

Shell:

- `AppShell` with a sidebar and a content outlet.
- Sidebar expanded/collapsed with Framer Motion; when collapsed, render an icon
  rail with tooltips.
- Mobile: off-canvas overlay with a backdrop and focus trap.
- Persist the collapsed preference in `localStorage` (non-secret UI preference).
- `PageHeader` per page: title, one-line description, optional actions.

Providers (compose in `main.tsx`/`App.tsx`):

- `QueryClientProvider`
- `ThemeProvider` — `light` / `dark` / `system`, persisted in `localStorage`,
  applied via the `dark` class.
- `SettingsProvider` — selected model id and per-provider API keys held in
  **React state only** (memory). Optional: persist the selected model id in
  `localStorage`; never persist keys.
- `BrowserRouter`

Motion:

- Sidebar width transition, page fade/slide, message entrance, tool-call
  accordion, cleanup dialog.
- Wrap with `useReducedMotion()` from Framer Motion and disable transforms when
  the user prefers reduced motion.

Accessibility:

- Every icon button has an accessible name.
- Dialog focus trap and restore focus on close.
- `aria-live="polite"` for the assistant's streaming-less result/status region.
- Keyboard navigable lists, tab order, visible focus rings.
- Contrast checked in both themes.

Visual language: trust-first and local-first. Say **"Move to Trash"**, not
"Delete permanently". Make destructive state visually distinct but not alarming.

---

## 8. Page specifications

### 8.1 Home

Data: `GET /health/ready`, `/api/disk/usage`, `/api/disk/directory`,
`/api/disk/count`, `/api/disk/info` (on selection).

- **Readiness banner** — healthy / degraded (MCP down) / backend unreachable.
  Do not block the whole page; Home can show a degraded state.
- **Path context bar** — free-text absolute path input; blank means default
  (home). Show a "Reset" control. Never send `path=` for blank.
- **Volume usage card** — used / free / total, percentage bar, and the resolved
  `path` from the response. Copy must state it is the whole volume, not the
  folder.
- **Largest immediate children** — ranked list or horizontal bar visual from
  `directory.entries`, with type icon. Directories are recursive totals; label
  this.
- **File count by extension** — top N extension groups plus total files.
  Collapse the long tail.
- **Selected entry metadata** — when a child is selected, fetch
  `/api/disk/info?path=<full path>` and show name, type, size, modified,
  created, extension. Note that a directory's `size_bytes` is the inode entry,
  not its contents.
- **States** — per-card skeleton, empty state, error state with Retry, and a CTA
  linking to `/assistant`.
- Do not invent large/duplicate/stale/junk panels; there are no REST endpoints
  for them (section 11).

### 8.2 AI Assistant

Layout: chat-style, the central experience.

- Composer: path input, question textarea, Send, model indicator, API-key
  readiness indicator.
- Send → `POST /api/agent/analyze` via `agentApi`. No streaming: show a
  determinate-looking progress state with honest copy ("Analyzing… this can take
  up to a minute"), and disable duplicate sends.
- Render `summary` as plain text or a **sanitized** markdown subset. Never
  `dangerouslySetInnerHTML`. Prefer plain text with preserved newlines.
- Render `tool_calls` as expandable timeline items:
  - tool name, args summary, `ok`/`error` badge;
  - typed renderer per tool (section 4.5);
  - unknown shape → JSON `<pre>` in the accordion.
- If a `preview_trash` call appears, render its `paths` with checkboxes and a
  "Review cleanup" action that opens the shared dialog with the selected paths.
- Cleanup candidates come only from structured `preview_trash` /
  `find_*` results. Never infer paths from the prose summary.
- Errors: 400/422/503 mapped through `getApiErrorMessage`; keep the composer
  contents so the user can retry (or fix the key/model).
- Display-history only, session-only. Label it "Conversations aren't saved".
  Each send is independent; there is no multi-turn memory.
- Do not render provider keys anywhere.

### 8.3 Settings

- Theme selector (light / dark / system).
- Model dropdown from `GET /api/agent/models`, showing label, provider, and
  Local/Cloud. Default to the first entry; do not hardcode an id.
- Per-provider API key fields (openai, google_genai, and any future provider):
  - password input with reveal toggle and clear button;
  - memory only — no `localStorage`, `sessionStorage`, cookies, IndexedDB, or
    URL;
  - note that keys are lost on reload.
- Ollama needs no key; show that the local model keeps analysis local.
- Readiness + API base URL display.
- Privacy notice: cloud models receive tool results (file paths, names, sizes)
  at the provider; Ollama keeps analysis local.
- Note that preferences are local-only and the backend stores nothing.

### 8.4 Shared cleanup review

Triggered only by an explicit user action (Assistant / Home). One dialog
component reused everywhere.

- List exact paths, count, and known size/type where available.
- Destructive button disabled until the user acknowledges that items move to the
  system trash. Require an explicit confirmation step (checkbox or typed
  acknowledgement), not just opening the dialog.
- Request body is exactly `{ paths }`. Never send `confirm` (the backend rejects
  extra keys with 422).
- Show results distinctly: `deleted`, `failed` (path + error), `missing_paths`
  (already gone).
- Copy: "Moved to the system trash." No undo UI; no "permanently deleted".
- Warn that the backend/MCP has no protected-system-path guard; avoid root,
  `/System`, `/Applications`, and other system locations in any bulk action.
- After completion, invalidate all `["disk"]` queries and refresh the current
  view.
- A 400 (all paths missing) and 503 (MCP down) each get a distinct error state.

---

## 9. Safety, security, and privacy invariants

1. Never persist API keys outside React memory.
2. Never put keys in URLs, query strings, logs, analytics, error messages, or
   crash reports.
3. Never use `dangerouslySetInnerHTML` for LLM output.
4. Never auto-execute cleanup from model output. A human selects and confirms.
5. Never invent endpoints, params, or response fields. If the backend lacks it,
   say so in the UI.
6. Do not expose `trash_path` or any destructive MCP tool to the browser. The
   browser's only mutating call is `POST /api/cleanup/execute`.
7. Surface the cloud-model privacy trade-off in Settings and at the point of
   choosing a cloud model.
8. Require exact-path confirmation; no "select all" on large or system paths.
9. Treat the backend as authoritative; do not hardcode model ids or payload
   shapes beyond the type mirrors above.
10. CORS must allow the Vite origin. Either set
    `STORAGE_BACKEND_CORS_ORIGINS=["http://localhost:5173"]` (the documented
    approach) or configure a Vite dev proxy; do not disable browser security.

Document `VITE_API_BASE_URL` in `frontend/.env.example`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

This is not a secret and is safe to commit.

---

## 10. API gaps and decisions

| Gap                                            | Impact                                                    | Safe v1 behavior                                                                                          |
| ---------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| No REST `preview_trash` route                  | Cannot preview an arbitrary batch directly over HTTP      | Use `preview_trash` results from agent `tool_calls`, or paths selected from disk listings; always confirm |
| No REST routes for the five `find_*` tools     | Home cannot show large/duplicate/stale/junk/empty reports | Keep those capabilities inside the Assistant only; do not fabricate endpoints                             |
| `/api/agent/analyze` is stateless and one-shot | No true multi-turn chat memory                            | Keep a client-side display history; label session-only; each send is independent                          |
| No settings or key persistence                 | Model/key choices cannot be stored server-side            | Persist theme and (optionally) selected model locally; keep keys in memory only                           |
| No key-validation endpoint                     | Cannot verify a key before analysis                       | First analyze may fail 422/503; show actionable errors and let the user retry                             |
| No volume/mount enumeration                    | Cannot build a disk/mount picker                          | Operate on a free-text path; blank means home                                                             |
| No OS directory picker                         | Cannot browse natively from the browser                   | Free-text absolute path input with backend error handling                                                 |
| No protected-path guard                        | Cleanup can target anything the user selects              | Exact-path confirmation; no bulk shortcuts; warn about system paths                                       |
| No cleanup history, audit, or undo             | Outcomes are ephemeral                                    | Show the immediate response; state that items are in the system trash                                     |
| No frontend CI job                             | Regressions are not caught automatically                  | Run Biome check/typecheck/build locally; propose a CI job separately                                      |
| CORS defaults to `[]`                          | Browser calls fail until configured                       | Set `STORAGE_BACKEND_CORS_ORIGINS` or use a dev proxy                                                     |
| Shell command / script endpoints absent        | No terminal integration                                   | Not in scope; do not add                                                                                  |

For each gap: do not invent a backend route or response field to paper over it.

---

## 11. Documentation and Postman drift (flag, do not copy)

Fix only if the user explicitly asks; none of these are frontend work.

- `backend/README.md` lists only 3 models; the code has 7
  (`agents/models.py:20`).
- `backend/postman/.../Agent/Analyze.request.yaml` omits `model` and `api_key`,
  so it would 422 as written.
- The Postman collection has no `GET /api/agent/models` request.
- `routers/disk.py:109` describes `/api/disk/info` as volume info; it returns
  single file/directory metadata (`FileInfoResponse`).
- `explore_directory` MCP docstrings mention emoji-prefixed `type` labels; the
  payload values are plain `"file"` / `"directory"`.
- `BACKEND_HANDOFF.md` is referenced by the root README, `AGENTS.md`, and
  `.opencode/` agents but is **missing from the repository**.
- The root README claims `refactor/monorepo` triggers CI; `.github/workflows/ci.yml`
  only triggers on `master` and `refactor/monorepo-structure`.

---

## 12. Phased implementation plan

**Phase 0 — Scaffold**
Vite + React + TS, Tailwind v4, shadcn init, path alias, Biome, `.env.example`,
providers, router, app shell, theme toggle.

**Phase 1 — API layer and Home**
`client.ts`, `errors.ts`, `types.ts`, `format.ts`; query keys and cache settings;
readiness banner; the five disk views; path context; loading/empty/error states.

**Phase 2 — Assistant**
Models query, Settings key fields, composer, analyze mutation, summary rendering,
tool-call timeline and typed result renderers.

**Phase 3 — Cleanup**
Selection state from `preview_trash`, shared review dialog, confirmation gate,
execute mutation, outcome display, disk invalidation.

**Phase 4 — Polish**
Responsive layout, sidebar collapse, reduced-motion support, accessibility pass,
copy review, empty/error edge cases, long-path handling.

**Phase 5 — Verification and docs**
Biome check/typecheck/build, manual matrix (section 13), update `frontend/README.md` with
durable setup/run instructions once the app exists. Keep this handoff as the
build snapshot; do not duplicate package docs into it.

---

## 13. Acceptance criteria and verification

Commands (from `frontend/`):

```bash
npm run check
npm run typecheck
npm run build
```

Behavior:

- [ ] App boots and renders the shell with the backend **down**, showing a
      degraded/offline state rather than a blank screen or unhandled error.
- [ ] Home loads all five disk views with a blank path (home default) and shows
      the correct volume-vs-directory caveats.
- [ ] Blank path is omitted from the query string, not sent as `path=`.
- [ ] `/api/disk/info` is fetched on selection and formats Unix seconds.
- [ ] Assistant works with a cloud key and with an Ollama model without a key.
- [ ] Tool calls render for every shape in section 4.5, and unknown shapes do not
      crash the page.
- [ ] `status: "error"` tool calls render as failed steps.
- [ ] Unsupported model / missing key / step limit / MCP down each produce an
      actionable message from `getApiErrorMessage`.
- [ ] Settings never write keys to `localStorage`/`sessionStorage`/cookies.
      Verify in DevTools Application storage.
- [ ] Model list is fetched from `/api/agent/models`; no model ids are hardcoded.
- [ ] Cleanup cannot run without explicit acknowledgement, submits only
      `{ paths }`, and displays deleted / failed / missing separately.
- [ ] All `["disk"]` queries refetch after cleanup.
- [ ] No direct Axios usage in presentational components.
- [ ] No `dangerouslySetInnerHTML` anywhere.
- [ ] No invented endpoints or response fields.

Git workflow:

- Work on `feature/frontend`.
- Open the PR against `refactor/monorepo-structure`.
- Never target `master` (or a nonexistent `main`) without explicit approval.
- Do not modify backend, MCP server, CI, or Postman files in this workstream.

---

## 14. Open decisions handed to the builder

Resolved here unless the user overrides:

- Filename is `frontend/FRONTEND_HANDOFF.md`, not `frontend/README.md`
  (`AGENTS.md` reserves package READMEs for durable docs).
- Tailwind v4 via `@tailwindcss/vite`; npm; TypeScript strict.
- Shared cleanup review is in v1 and reachable from Home and Assistant.
- No charting library; CSS/SVG visuals.
- Tests deferred: Biome check, typecheck, build, and the manual matrix above.
- Gaps are documented, not designed around with new endpoints.
