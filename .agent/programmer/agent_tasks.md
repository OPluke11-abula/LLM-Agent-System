# Programmer Agent Task Queue

> Purpose: Track implementation-level work that supports the LAS viewer and agent runtime but is outside pure UI polish.
> Status legend: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## Phase P1 — UI Verification Infrastructure

- [ ] Add deterministic visual verification fixtures for the viewer's Rules, MODs, and Settings surfaces.
  - English: Provide stable seeded state for policy rules, active skills, LLM config, and workspace paths so visual QA can render meaningful screens without relying on live user data.
  - 中文：提供穩定的 seeded state，涵蓋 policy rules、active skills、LLM config 與 workspace paths，讓視覺 QA 不依賴使用者即時資料也能渲染有效畫面。

- [ ] Extend `viewer/scripts/verify-ui.mjs` to capture desktop and mobile screenshots when a local preview server is available.
  - English: Replace the current `screenshots skipped` path with an optional Playwright-backed screenshot gate that fails on blank screens, missing route chunks, or obvious render crashes.
  - 中文：將目前的 `screenshots skipped` 路徑升級為可選的 Playwright screenshot gate，遇到空白畫面、route chunk 遺失或明顯 render crash 時失敗。

- [ ] Add a lightweight rendered-copy audit for operational UI strings.
  - English: Flag new visible emoji prefixes, neon color utilities, and hardcoded English labels in translated viewer surfaces.
  - 中文：偵測新增的可見 emoji 前綴、霓虹色 utility，以及已翻譯 viewer surface 裡的硬編碼英文 label。

---

## Progress Summary

| Phase | Total Tasks | Completed Tasks | Status |
|---|---:|---:|---|
| **P1** | 3 | 0 | Pending |

