# Declared Project Runtime & Dependency Versions

This file specifies the official declared runtime and toolchain versions for LLM-Agent-System (LAS). Machine-local variations belong in `.agent/local/environment.md` (gitignored).

---

## 1. Protocol & Framework Standards
- **Universal Coding Protocol**: `3.8.0`
- **Universal Chat Agent Protocol**: `2.7.0`
- **Portable Agent Protocol (PAP)**: `0.2.0`

## 2. Core Python Runtime
- **Python**: `>= 3.11, < 3.13`
- **FastAPI**: `>= 0.110.0`
- **Pydantic**: `>= 2.6.0`
- **Uvicorn**: `>= 0.28.0`
- **Pytest**: `>= 8.0.0`
- **Cryptography**: `>= 42.0.0`

## 3. Viewer & Presentation Runtime
- **Node.js**: `>= 20.0.0`
- **React**: `19.0.0`
- **Tauri**: `2.x`
- **Vite / Rolldown**: `>= 5.0.0`
- **Radix UI Primitives**: Compatible with React 19

## 4. Local Memory & Knowledge OS
- **SQLite Engine**: SQLite 3 with FTS5 enabled
- **Obsidian Vault Target**: `C:\Users\luke2\OneDrive\文件\Obsidian Vault`
