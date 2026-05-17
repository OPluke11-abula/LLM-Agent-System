# Contributing to AI Agent Topology Viewer

Thank you for your interest in contributing! This project is built by developers who want to make AI-assisted workflows more transparent and trustworthy. Every contribution helps make that vision a reality.

AI contributors must read [`AGENTS.md`](./AGENTS.md) before making changes.

## Prerequisites

Before contributing, ensure you have the following installed:

| Tool | Minimum Version | Notes |
|------|----------------|-------|
| [Rust](https://www.rust-lang.org/) | `1.80+` (stable) | Install via `rustup` |
| [Node.js](https://nodejs.org/) | `22 LTS` | Recommended via `nvm` or `fnm` |
| [Tauri CLI](https://tauri.app/start/) | `2.0` | `npm install -D @tauri-apps/cli` |
| [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) | Latest | Windows only — usually pre-installed |

## Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/YourUsername/ai-agent-topology-viewer.git
cd ai-agent-topology-viewer

# 2. Install frontend dependencies
npm install

# 3. Launch the full Tauri app in dev mode (hot reload enabled)
npm run tauri dev
```

The app watches `workspace/agent_memory.json` by default. Try editing that file while the app is running to see live DAG updates.

To point the watcher at a different directory:
```powershell
$env:AGENT_WORKSPACE_DIR = "C:\path\to\your\workspace"
npm run tauri dev
```

## Project Structure

```
ai-agent-topology-viewer/
├── src/              # React + TypeScript frontend
│   └── App.tsx       # All UI components (single-file architecture)
├── src-tauri/        # Rust Tauri backend
│   ├── src/lib.rs    # File watcher + IPC commands
│   └── tauri.conf.json
├── workspace/        # Default agent memory location
│   └── agent_memory.json
└── .agent/           # AI domain skill libraries
    └── skills/
```

## Contribution Guidelines

### Code Style
- **TypeScript:** Use the latest stable syntax (`~5.8`). No `any` types unless absolutely unavoidable.
- **Rust:** Follow standard `rustfmt` formatting. Run `cargo fmt` before committing.
- **CSS:** Tailwind utility classes only. No custom CSS files unless a new animation is truly required.

### Architecture Rules
- **Do not create new files** unless the feature absolutely cannot fit into the existing architecture.
- **Iterate on `src/App.tsx`** for all frontend changes.
- **Iterate on `src-tauri/src/lib.rs`** for all backend/IPC changes.
- Keep every change small, verifiable, and production-oriented.

### `agent_memory.json` Schema

When extending the data model, maintain backward compatibility by using `Option<T>` in Rust and `?: T` in TypeScript:

```json
{
  "tasks": [
    {
      "id": "task-001",
      "description": "Human-readable task description",
      "status": "pending | in_progress | completed",
      "dependencies": ["task-id"],
      "ai_feedback": "Optional AI note for this task node",
      "tasks": []
    }
  ]
}
```

## Submitting a Pull Request

1. **Fork** this repository and create a branch: `feature/my-feature` or `fix/bug-name`.
2. Make your changes following the guidelines above.
3. **Update `README.md`** to reflect any user-facing changes.
4. Open a Pull Request with a clear title and description explaining:
   - What problem does this solve?
   - What did you change and why?
   - How did you test it?

## Reporting Bugs

Open a [GitHub Issue](../../issues/new) and include:
- OS version and architecture
- Steps to reproduce
- Expected vs. actual behavior
- The contents of your `agent_memory.json` (sanitize any private info)

## Community

This project is maintained by **防呆工作室 (FindAi)**.  
Website: [Hello FindAi](https://sites.google.com/view/hello-findai/首頁)  
Email: `we.are.findai@gmail.com`

All interactions in this project follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/).
