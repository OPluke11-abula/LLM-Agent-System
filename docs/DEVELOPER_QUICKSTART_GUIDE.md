# LAS Developer Quickstart & Beta Operations Guide

> **Protocol Version**: `3.8.0` (`Universal_Coding_Agent_Development_Protocol.md`)
> **Tool Version**: `v0.5.0` (Developer Beta)
> **Architectural Reference**: [[01 Agent Strategy Integration & TaskEnvironment Architecture]], [[60 Architectural Decision Records (ADR) Graph#ADR-006|ADR-006: Agent Strategy Integration]]

---

## 1. Executive Summary & Core Philosophy

The **FindAi Studio LLM Agent System (LAS)** is a governed, autonomous multi-agent development control plane. Built upon **ADR-006**, LAS synthesizes three foundational engineering paradigms:

1. **Antigravity (Design for Abundance)**: Useful parallelism over maximal parallelism; dynamic, disposable agent sessions operating within non-overlapping mutable scopes.
2. **Claude (Design for Failure & Containment)**: Autonomy rooted in containment rather than trust. Non-bypassable execution chain with `ScopeGuard` physical boundary enforcement.
3. **Codex (Harness Amplification)**: Maximizing agent effectiveness through high **Environment Legibility**, minimum sufficient context (`TaskEnvironment`), and structured feedback.

$$\text{Verified Engineering Throughput} \approx \frac{\text{Accepted Engineering Work}}{\text{Time} \times \text{Compute} \times \text{Human Attention}}$$

---

## 2. 1-Minute Installation

### Prerequisites
- **Python**: `>= 3.10` (Python 3.11, 3.12, 3.13, 3.14 supported)
- **Git**: `>= 2.30` (Required for native `git worktree` physical isolation)
- **Node.js** *(Optional for Web Cockpit)*: `>= 18.0`

### Installation via pip or uv
Install LAS directly into your virtual environment in editable mode:

```bash
# Clone the repository
git clone https://github.com/OPluke11-abula/LLM-Agent-System.git
cd LLM-Agent-System

# Install via uv (recommended for ultra-fast installation)
uv pip install -e .

# Or via standard pip
pip install -e .
```

Verify that the `las` CLI toolbelt is available:
```bash
las --help
```

---

## 3. Command-Line Toolbelt Reference (`las`)

```text
Usage:
  las <command> [options]

Core Subcommands:
  init [path]        Bootstrap Protocol v3.8.0 workspace (.agent/, AGENTS.md)
  onboard [path]     Analyze target repository and generate TaskEnvironment configuration
  pipeline run ...   Execute an autonomous coding task with Anti-Summary preflight & Stop-and-Wait gate
  benchmark          Run the official Golden Flow Benchmark suite and calculate 6 KPIs
  serve              Launch FastAPI REST API server and WebSocket telemetry hub
  status [path]      Inspect repository branch, worktree status, and latest verification receipt
```

### 3.1 `las onboard` (Target Repository Sensing)
Analyzes any Git repository, automatically detecting programming languages, test commands, branch topology, and protected paths, and synthesizes a recommended `TaskEnvironment`:

```bash
# Analyze and scaffold .agent/ in the target directory
las onboard /path/to/target-repo

# Dry-run analysis with JSON output
las onboard /path/to/target-repo --no-scaffold --format json
```

### 3.2 `las pipeline run` (Autonomous Task Execution)
Executes an end-to-end coding task inside an isolated Git worktree:

```bash
# Interactive run with Stop-and-Wait human approval gate
las pipeline run \
  --target-dir ./my-project \
  --requirement "Implement divide(a, b) with zero-division check in src/math.py and add unit test" \
  --inspected-files "src/math.py,tests/test_math.py" \
  --target-files "src/math.py,tests/test_math.py" \
  --role DOMAIN_LOGIC_AGENT

# Non-interactive CI/CD execution with auto-approval
las pipeline run \
  --target-dir ./my-project \
  --requirement "Fix typo in docstring" \
  --inspected-files "README.md" \
  --target-files "README.md" \
  --auto-approve
```

### 3.3 `las benchmark` (Golden Flow Benchmark)
Executes the official 3-scenario benchmark suite against an isolated target repository fixture and computes the 6 ADR-006 engineering KPIs:

```bash
# Run all 3 canonical scenarios
las benchmark

# Run a specific scenario and export JSON receipt
las benchmark --scenarios HAPPY_PATH_FEATURE --output-json .agent/evidence/my_receipt.json
```

### 3.4 `las serve` (Daemon & Gateway)
Starts the FastAPI backend gateway and WebSocket streaming hub:

```bash
las serve --host 127.0.0.1 --port 8000 --reload
```

### 3.5 `las status` (Health & Receipts)
Displays the active Git branch, head commit, clean/dirty state, detected stacks, and the latest benchmark scorecard:

```bash
las status
```

---

## 4. 5-Minute Tutorial: Connecting LAS to an Existing Project

### Step 1: Onboard Your Target Repository
Run `las onboard` pointing to your local repository directory:

```bash
las onboard ./my-api-service
```

This creates a lightweight `.agent/` folder in your project:
- `AGENTS.md`: Authoritative entry point defining Anti-Summary and Stop-and-Wait rules.
- `.agent/state.md`: Protocol v3.8.0 identity lock.
- `.agent/ownership.md`: Role boundaries and mutable scope restrictions.
- `.agent/task_environment.json`: Discovered test commands and protected paths.

### Step 2: Execute an Autonomous Feature Task
Trigger an autonomous task on your project:

```bash
las pipeline run \
  --target-dir ./my-api-service \
  --requirement "Add health check route at /healthz returning status ok" \
  --inspected-files "routes.py,tests/test_routes.py" \
  --target-files "routes.py,tests/test_routes.py"
```

### Step 3: Clear the Stop-and-Wait Architecture Gate
The CLI will display the generated `ScopedMutationPlan` containing the structural diff preview, edge cases, and test strategy:

```text
============================================================
 🛡️ Stop-and-Wait Architecture Gate (ADR-005)
============================================================
 Task ID     : TASK-HEALTH-CHECK-01
 Summary     : Adds GET /healthz endpoint and unit test
 Target Files: ['routes.py', 'tests/test_routes.py']
 Edge Cases  : Validates JSON response structure
============================================================
Approve this mutation plan? [y/N]: y
```

### Step 4: Review Verification Evidence & Draft PR
LAS spins up an isolated Git worktree, applies the modifications, executes your test suite (e.g. `pytest`), verifies canonical checkout preservation, and issues a Draft PR or verifiable local patch bundle (`.agent/patches/<branch>.patch.md`).

---

## 5. Web Cockpit Integration (`viewer/`)

For graphical real-time monitoring:

1. **Launch Daemon**:
   ```bash
   python scripts/start_las.py
   # Or via PowerShell on Windows:
   .\scripts\start_las.ps1
   ```

2. **Access Cockpit**: Open your browser at `http://localhost:5173/pipeline`.
   - **5-Stage Visual Stepper**: Real-time progress through `INTAKE` $\to$ `PRECHECK` $\to$ `PLAN_AND_GATE` $\to$ `ISOLATED_MUTATION` $\to$ `VERIFY_AND_EVIDENCE` $\to$ `DRAFT_PR_EXPORT`.
   - **Interactive Stop-and-Wait Modal**: Review diffs and confirm approval tokens.
   - **Verification Ladder Table**: Inspect each command's exit code, latency, and stdout/stderr output.
   - **Merkle Audit Trail Card**: Real-time cryptographic state proof and canonical preservation status.
   - **Golden Benchmark Modal**: Single-click trigger for running the 3-scenario benchmark and viewing the 6 ADR-006 KPI stat tiles.

---

## 6. Security & Invariants Checklist

| Invariant | Enforcement Mechanism | Failure Consequence |
|---|---|---|
| **Anti-Summary Invariant** | Preflight checks `inspected_files` | Unconditionally blocked (`400 Bad Request`) |
| **Stop-and-Wait Gate** | Human approval token required | Execution prohibited (`403 Forbidden`) |
| **Physical Scope Containment** | `ScopeGuard` path interception | Mutation blocked, raises `ScopeExpansionRequest` |
| **Zero Host Pollution** | `CanonicalPreservationReceipt` | Checked before and after every worktree run |
| **Review Freshness** | `IndependentReviewVerifier` | Fails if reviewed commit $\ne$ current HEAD |
| **No False PRs** | `LiveFeedbackRunner` | Any test failure immediately aborts PR export |

---

*Generated for LLM-Agent-System (LAS) v0.5.0 Developer Beta.*
