# Storage Intelligence

**Storage Intelligence** is a local-first Model Context Protocol (MCP) server built with [FastMCP](https://gofastmcp.com) for intelligent local storage analysis, disk usage profiling, duplicate file detection, and automated safe cleanup workflows.

---

## Features

Modern local environments accumulate significant storage waste (caches, build artifacts, duplicate files, heavy media, and unused dependencies). **Storage Intelligence** bridges local disk analysis with AI capabilities by exposing structured MCP tools, resources, and prompts.

Features:

- **Comprehensive Disk & Folder Profiling**: Detailed breakdowns of file sizes, directory trees, depth analysis, and large file scanning.
- **Duplicate & Junk Detection**: Hashing and category-based identification of waste across directories.
- **Safe & Intelligent Cleanup**: Staging dry-runs, safety checks, and selective removal/archival options.
- **Local Privacy & Control**: Operates entirely locally on your system, keeping file paths and system metadata secure.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI Assistant / Client                           │
│                   (Claude Desktop, Cursor, etc.)                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │  Model Context Protocol (Stdio / SSE)
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                   Storage Intelligence (MCP Server)                    │
│                                                                        │
│   core.py     FastMCP instance `mcp` — central server object           │
│   server.py   Entry point — imports and registers primitives           │
│                                                                        │
│   Exposed Primitives:                                                  │
│   ├── Tools        storage.py   12 read-only analysis tools            │
│   │                cleanup.py   6 cleanup tools (defined, planned)     │
│   ├── Resources    resources/   System storage views & metadata        │
│   └── Prompts      prompts/     Predefined templates for analysis      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │  Local File I/O
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                           Local File System                            │
└────────────────────────────────────────────────────────────────────────┘
```

### Future Deployment Target

```
┌────────────────────────────────────────────────────────────────────────┐
│                      React Dashboard (Browser UI)                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                     Express MCP Host (Daemon / Proxy)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                   Storage Intelligence (MCP Server)                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    v
┌────────────────────────────────────────────────────────────────────────┐
│                           Local File System                            │
└────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/storage_intelligence/
├── __init__.py         # Package entry marker
├── core.py             # FastMCP instance configuration
├── server.py           # Entry point wiring tools, resources, and prompts
├── utils.py            # Helpers for file formatting, hashing, and OS traversal
├── tools/              # MCP Tools exposed to AI clients
│   ├── storage.py      # Storage analysis, tree traversal, and duplicate detection
│   └── cleanup.py      # Safe file removal, staging, and cleanup routines
├── resources/          # MCP Resources (read-only system storage views)
└── prompts/            # MCP Prompts (predefined templates for analysis flows)
```

---

## Getting Started (Local Development)

### Prerequisites

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv) package manager

### Running Locally

```bash
# Clone and enter directory
cd storage-intelligence

# Install dependencies
uv sync

# Run the MCP server via stdio
uv run storage-intelligence
```

---

## Future Roadmap

- **Integrated MCP Host**: Build a standalone host daemon to manage MCP lifecycle, background scanning, and persistent index storage.
- **React Dashboard UI**: Web-based visual dashboard for interacting with the MCP server, visualizing storage breakdowns with interactive charts (treemaps, sunbursts), and reviewing cleanup recommendations.
- **Docker Deployment**: Containerized setup for local NAS, home server, or sandbox environments with configurable disk mounts.
- **Background Indexing & Caching**: Asynchronous background workers for real-time file system monitoring and instant duplicate query results.
- **Enhanced Safety Profiles**: Preset safety rules (e.g., protected system paths, trash/recycle bin integration, backup before delete).
