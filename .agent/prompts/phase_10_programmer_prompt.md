# PAP Programmer Job Prompt: Phase 10 — UI/UX Polish, Multi-Language & Tauri Standalone Packaging

請先閱讀並理解 `ai_programmer_learning_guide.md` 手冊。剩下的引導詞如下：

---

## 📌 任務背景與目標
你是一位資深的前端與桌面系統工程師 (Senior Frontend & Desktop Systems Engineer)。你的目標是實現並打磨 **Portable Agent Protocol (PAP)** 任務規格中的 **Phase 10 — UI/UX Polish, Multi-Language & Executable Packaging (UI/UX 打磨、多國語言與可執行檔打包)**。

目前所有後端 API、數據合約與單元測試 (91/91 通過) 均已在 `agent_workspace` 下完美就緒，你的工作範圍將集中在 `viewer/` 目錄下的 React Flow + TypeScript + Tauri 桌面客戶端。

---

## 🗂️ 核心關聯檔案與路徑
- **應用程式入口點**：[App.tsx](file:///d:/GitHub/LLM-Agent-System/viewer/src/App.tsx)
- **多語系辭典**：[constants.ts](file:///d:/GitHub/LLM-Agent-System/viewer/src/constants.ts)
- **設定面板元件**：[SettingsView.tsx](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/SettingsView.tsx)
- **導覽側邊欄**：[Sidebar.tsx](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/Sidebar.tsx)
- **新手引導精靈**：[OnboardingWizard.tsx](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/OnboardingWizard.tsx)
- **視覺樣式表**：[index.css](file:///d:/GitHub/LLM-Agent-System/viewer/src/index.css)
- **Tauri 配置檔**：`viewer/src-tauri/tauri.conf.json`
- **合約任務清單**：[agent_tasks.md](file:///d:/GitHub/LLM-Agent-System/.agent/agent_tasks.md)

---

## 🛠️ 具體執行步驟與驗收標準

### 1️⃣ Task 10-01: Localized Language Extensions (日法多國語言擴展)
- **核心實作**：
  - 開啟 `viewer/src/constants.ts`，在多語系辭典 `T` (目前僅包含 `zh` 與 `en`) 中新增完整的**日語 (`ja`)** 與**法語 (`fr`)** 翻譯字典。
  - 確保翻譯內容涵蓋：新手引導精靈的說明與模擬節點、一般設定的 LLM 設定表單、提示詞自動產生器文字，以及對話操作技巧提示。
- **UI 元件更新**：
  - 開啟 `viewer/src/components/SettingsView.tsx` 中的語言切換器，更新為支援 `["zh", "en", "ja", "fr"]` 動態渲染。
  - 必要時更新 `viewer/src/types.ts` 中的 `Lang` 型別宣告以支援新語系。
- **驗收要求**：切換為任何新語系時，介面文字須在 0 毫秒內即時重新渲染，且無任何漏譯的罐頭佔位符。

### 2️⃣ Task 10-02: Relaunchable Onboarding Wizard (重新啟動新手教學)
- **核心實作**：
  - 在 `viewer/src/components/SettingsView.tsx`（一般設定中）或 `viewer/src/components/Sidebar.tsx`（側邊欄底部）新增一個高質感的「重啟新手引導」或「Relaunch Tutorial」按鈕。
  - 點擊按鈕後，應將反應式持久化狀態 `hasOnboarded` 暫時重設為 `false`，即時卸載主視圖並掛載 `OnboardingWizard` 教學精靈。
- **驗收要求**：使用者能流暢重走「動態 SVG 拓撲圖 -> 工作區建立 -> Prompt 複製」新手引導，並能在完成時安全重返主儀表板，且不影響已配置的其他工作區。

### 3️⃣ Task 10-03: Tauri Standalone Executable Packaging (Standalone .exe 打包)
- **核心實作**：
  - 檢查 `viewer/src-tauri/tauri.conf.json` 中配置的靜態資產路徑 (`dist`)、應用程式套件標識符與編譯選項。
  - 執行本地編譯指令，將 React Flow 前端與 Rust 監聽後端打包編譯為單一可移植、免安裝的 Windows `.exe` 執行檔：
    ```bash
    cd viewer
    npm run tauri build
    ```
- **驗收要求**：編譯須 100% 成功，打包後的 `.exe` 檔案大小應保持在 Tauri 的超輕量極限 (約 3~5 MB)，雙擊可立即在 Windows 10/11 上加載完整視覺效果。

### 4️⃣ Task 10-04: Escaping AI-vibe Premium Styling Polishes (視覺美學極致雕琢)
- **核心實作**：
  - 精修 `viewer/src/index.css` 以徹底破除 generic AI boilerplates：
    - 加強**玻璃擬態面板 (Glassmorphic panel)** 的邊框質感 (`border-white/10`)、背板模糊濾鏡 (`backdrop-blur-2xl`)。
    - 微調點狀背景網格 (`bg-grid`) 的縮放比，確保在寬螢幕下視覺依舊和諧。
    - 精雕連線的動態流動粒子動畫 (`animate-flow-particles`) 與運行中節點的呼吸燈，呈現高度手工客製感。
- **驗收要求**：各視覺指標無鋸齒、無生硬邊緣，過渡動畫流暢，呈現殿堂級軟體控制台的工藝品質。

---

## 🚦 自動化與合約維護
1. 完成所有實作後，請開啟並更新 [agent_tasks.md](file:///d:/GitHub/LLM-Agent-System/.agent/agent_tasks.md) 中的 `PHASE 10` 任務勾選狀態與底部的 Progress 摘要表。
2. 在 `viewer` 目錄下執行靜態靜態語法檢查與測試，確保無 TypeScript 或 Vite 編譯期 Error。
