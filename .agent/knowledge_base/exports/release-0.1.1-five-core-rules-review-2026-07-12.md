# Release 0.1.1 Five Core Rules Review

Date: 2026-07-12
Scope: release wrap-up, repository hygiene, documentation, and Windows viewer
installer.

## Result

The release changes conform to the five operating rules in `.agent/agent.md`.
No incomplete item remains in the approved Phase 0-71 queue, and the repository
had no open GitHub issues at review time.

## Rule 1: Keep Runtime Core Separate

- A structural code-graph search found no imports from `agent_workspace/core/`
  into route or service adapter layers.
- The only core edit removes the standalone debug/demo harness from
  `agent_workspace/core/engine.py`; runtime behavior is unchanged.
- The focused AgentEngine, skill-discovery, and skill-synthesis tests passed:
  19 tests passed.

## Rule 2: Keep Runtime Skills and PAP Contracts in Parity

- `python -m agent_workspace.tool_manifest validate` reported all 25 runtime
  tools matched their PAP contracts.
- The same validation reported that the secrets scan passed.
- `python -m agent_workspace.cli --validate` reported the PAP workspace valid.

## Rule 3: Prefer Structural Lookup

- Code discovery used the ready Codebase Memory graph before bounded source
  reads.
- Broad text scans were reserved for README content, ignore rules, literal
  debug markers, and local-development artifacts.

## Rule 4: Keep Context Compact

- The stale queue pointer in `.agent/agent.md` now states that no implementation
  phase is pending.
- The accidental `tmp_MEMORY_patch.md` export and tracked empty test-session
  artifact were removed.
- Release evidence is summarized here and in the compact knowledge log instead
  of being left in temporary notes.

## Rule 5: Verify Before Claiming Success

- Focused Python tests: 19 passed.
- Viewer production build: passed.
- Tauri NSIS bundle: passed for version 0.1.1.
- Installer SHA-256:
  `18448AB860EAA2BD795CA4DE5BA2F80682E1150369C0212423A1BCFE752BABA5`.
- `scripts\verify.cmd`: passed, including Python compilation, full pytest,
  PAP validation, 25 tool contracts, secrets scan, viewer build, UI checks, and
  swarm UI tests.
- README files decoded as strict UTF-8 with no replacement characters or known
  mojibake markers, and their documented read-only CLI commands were exercised.
- MSI packaging is not claimed: WiX ICE validation could not access Windows
  Installer correctly. The verified release artifact is the NSIS executable.

## Deferred and Local-Only Items

- The whole-tree AI-slop scan reported 706 historical findings across 175
  files. They are architectural debt outside this bounded release cleanup, not
  newly introduced release findings.
- Approved build caches, local account files, and obsolete 0.1.0 installers
  were removed. One malformed recursively copied pytest tree remains under the
  ignored `agent_workspace/scratch/` path because Windows could not traverse
  its nested paths even after ownership repair; it cannot enter the commit.
- The 0.1.1 executable is the current verified release artifact.
