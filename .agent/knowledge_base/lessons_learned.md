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

---

### Lesson ID: L-20260531-002 (Context Bloat & File-Based Hallucination Prevention)
- **Mistake Encountered**: AI agents experiencing hallucinations, thread confusion, or excessive token usage due to an over-bloated workspace context containing obsolete handoff logs, redundant manual scripts, and verbose task master-lists.
- **Root Cause**: Failure to actively prune completed execution paths and historical tasks from the prompt context, leaving obsolete files (e.g. `handoff.md`, manual `test_*.py` files) inside the active workspace boundaries.
- **Resolution Actions**:
  - Automatically prune completed tasks in `agent_tasks.md` by consolidating finished phases into dense, high-level summary logs (reducing token weight by up to 88%).
  - Ensure immediate removal of obsolete handoff guides and manual scripts that are 100% redundant, keeping only clean automated test suites.
- **Best Practice Policy**: Maintain a highly optimized, lean context footprint by dynamically compressing past execution logs and purging redundant files to enforce strict state consistency and eliminate AI context noise.

---

### Lesson ID: L-20260601-001 (Dynamic Concurrency Balancer Queue Race)
- **Mistake Encountered**: Thread balancer failing to dynamically scale up worker allocations under high task submission rates.
- **Root Cause**: active_tasks counters were incremented *inside* the worker threads' wrapper functions. Under low thread pool worker allocations (e.g. max_workers = 2), new tasks were queued but not running, so they could not execute the first line of the wrapper function to increment the active counter. The active count never exceeded the threshold, preventing dynamic scaling.
- **Resolution Code**:
  ```python
  def offload(self, fn: Any, category: str = "heavy", *args: Any, **kwargs: Any) -> Any:
      with self._lock:
          self.active_tasks[category] += 1
      self.balance_loads()
      
      def wrapped(*a: Any, **kw: Any) -> Any:
          try:
              return fn(*a, **kw)
          finally:
              with self._lock:
                  self.active_tasks[category] = max(0, self.active_tasks[category] - 1)
              self.balance_loads()
  ```
- **Best Practice Policy**: Always increment thread pool queue and active task counters synchronously on the main calling thread at the time of submission, rather than deferring the counter update to when the worker thread starts executing.


