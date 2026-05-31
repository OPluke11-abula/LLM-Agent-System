# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry

This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices. It is dynamically parsed by the dynamic Prompt Composer to auto-evolve prompt directives and ensure zero repetition of development mistakes.

---

## ⚡ 1. Active Resolution Directory (Lessons Database)

### Lesson ID: L-20260528-001 (Task Mocking Deadlocks)
- **Mistake Encountered**: Async pytest suites hanging indefinitely during automated HITL validation tests.
- **Root Cause**: The router was requesting approval from `.agent/agent.md` manifest having standard interactive-approval configured, blocking the non-interactive test process.
- **Resolution Code**:
  ```python
  router._get_authorization_level = MagicMock(return_value="standard")
  ```
- **Best Practice Policy**: Always mock approval checks and bypass interactive prompt gateways when executing automated suites inside CI/CD/pytest environments.

---

### Lesson ID: L-20260528-002 (SQLite Concurrency Locks)
- **Mistake Encountered**: SQLite database returning `sqlite3.OperationalError: database is locked` on parallel multi-agent writes.
- **Root Cause**: Multiple concurrent OS threads or asyncio tasks writing to a single SQLite backend without transaction queues or connection synchronization locks.
- **Resolution Code**:
  ```python
  class MemoryBackend:
      _lock = asyncio.Lock()
      async def write(self, ...):
          async with self._lock:
              # Perform transactional write with isolation_level="IMMEDIATE"
  ```
- **Best Practice Policy**: Wrap all sqlite3/disk write transactions in a dedicated asynchronous lock guard to enforce serial execution.

---

### Lesson ID: L-20260528-003 (React Flow Resize Loop Warning)
- **Mistake Encountered**: Chromium console flooded with `ResizeObserver loop completed with undelivered notifications` errors during layout rendering.
- **Root Cause**: ResizeObserver trigger executing state transitions immediately inside resize events, causing infinite resize loops during React Flow auto-layouts.
- **Resolution Code**:
  ```typescript
  const observer = new ResizeObserver(() => {
    window.cancelAnimationFrame(animationFrame);
    animationFrame = window.requestAnimationFrame(() => fitFlowToView(120));
  });
  ```
- **Best Practice Policy**: Throttle or debounce all dynamic viewport resizing logic using standard requestAnimationFrame techniques to decouple layout changes from observer loops.

---

### Lesson ID: L-20260531-001 (Dynamic Swarm Workspace Path Resolution)
- **Mistake Encountered**: Incorrect project root path resolution when `PromptComposer` or `DiscussionRoom` tries to locate role configuration files or learning guides in a temporary directory or directly in the workspace root.
- **Root Cause**: The composer was resolving the project root by blindly taking `Path(workspace_path).parent`, which is invalid if `workspace_path` itself is the root directory or if a temporary test directory is utilized.
- **Resolution Code**:
  ```python
  path_check = Path(self.workspace_path)
  if (path_check / ".agent").is_dir():
      self.project_root = path_check
  elif (path_check.parent / ".agent").is_dir():
      self.project_root = path_check.parent
  else:
      self.project_root = path_check.parent
  ```
- **Best Practice Policy**: Dynamically inspect parent and current working directories for the presence of the contract-first `.agent` folder before falling back to fixed path traversal logic.
