# Repository Knowledge Base

For work in this workspace, use the compact local knowledge base before broad repository exploration.

1. Read `@AGENTS.md`.
2. For a non-trivial task, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\.agent\knowledge_base\tools\start_agent_preflight.ps1 -Query "<task focus>" -Top 5
```

3. Read the generated context pack and only then its ranked candidate notes.
4. Verify current source, configuration, Git state, and relevant tests live; wiki notes are orientation, not proof.
5. When the task yields durable project knowledge, update only a concise relevant note or handoff. Never record secrets, credentials, cookies, private keys, or `.env` values.

The shared local wiki is `@.agent/knowledge_base/index.md`. Do not load the entire knowledge base by default.
