# Governed Memory Skill Contract

**Version:** 0.1.0  
**Format:** PAP Capability Contract v1

## Identity
- **id:** `governed-memory`
- **name:** Governed Memory Operations
- **description:** 允許 Agent 主動搜尋長期記憶，並將有價值的經驗提煉為語意知識儲存，實現跨對話的自我演進能力。

## Capabilities

### `memory_query`
- **description:** 透過自然語言關鍵字搜尋長期記憶。可選定 `domain` 來限縮範圍（如 `semantic` 或 `episodic`）。
- **inputs:**
  - `query_text` (string): 要搜尋的關鍵字或短語。
  - `domain` (string, optional): 指定記憶領域（例如 `semantic` 代表事實知識，`episodic` 代表歷史對話）。
- **outputs:** (list of objects)
  - 每個物件包含 `id`, `summary`, `domain`, `created_at` 等欄位。

### `memory_store_knowledge`
- **description:** 將任務中學到的經驗、解決方案或事實，提煉為長期保留的 `semantic` 知識。
- **inputs:**
  - `knowledge_text` (string): 提煉出的知識描述（必須簡潔且具備高度重用價值）。
  - `citations` (list of strings): 參考來源的任務 ID、連結或檔案路徑。
- **outputs:** (string)
  - 成功儲存的確認訊息與記憶 ID。

### `memory_store_preference`
- **description:** 儲存使用者的特定偏好（例如程式碼風格、常用工具），以便未來的對話或任務中自動套用。
- **inputs:**
  - `preference_text` (string): 偏好設定的描述。
- **outputs:** (string)
  - 成功儲存的確認訊息。

## Guidelines
1. **何時使用 `memory_query`**：當您面臨未知問題、需要確認架構設計歷史、或尋找過去類似 Bug 的解法時，請優先搜尋 `semantic` domain。
2. **何時使用 `memory_store_knowledge`**：當您剛把一個複雜任務（尤其是包含 Troubleshooting 的任務）標記為 `Done` 時，請主動將解決方案摘要後儲存。
3. **避免冗餘**：在儲存之前先使用 `memory_query` 確認是否已有類似知識存在。
