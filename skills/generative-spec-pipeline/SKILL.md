---
name: generative-spec-pipeline
description: Transforms vague creative ideas or product requests into production-grade, engineering-specification prompts with strict constraints, state/timeline definitions, and critic-and-correction loops. Supports 3D (Blender/Three.js/WebGL), UI (React 19/Tailwind/Radix), and 2D (Sprites/SVG/Canvas).
triggers:
  - 3d-spec
  - ui-spec
  - 2d-spec
  - 規格提示詞
  - 工程規格書
  - spec prompt
  - 3D prompt
  - UI prompt
---

# Generative Specification Pipeline (跨模態工程規格化 Prompt 引擎)

將模糊的創意思想轉化為 AI 可 100% 確定性執行的**「工程規格書（Technical Specification）」**。
徹底根除 AI 在生成 3D、UI、2D 資產時常見的偷懶（2D 冒充 3D、TODO 佔位符、破面撕裂、UI 跑版、AI 紫粉髒色）。

---

## 核心心法：四步工程規格書公式

$$\text{1. 角色與情境} \longrightarrow \text{2. 硬性幾何與資產限制} \longrightarrow \text{3. 互動、狀態與時間軸} \longrightarrow \text{4. 驗收標準與 Critic 迴圈}$$

| 階段 | 3D (Blender / Three.js / WebGL) | UI (React 19 / Tailwind / Desktop) | 2D (Sprite Sheets / SVG / Canvas) |
| :--- | :--- | :--- | :--- |
| **1. 角色／情境** | 世界觀、主體特徵、空間景深、攝影機焦段、主次層次 | 用戶 Persona、業務場景、視覺基調 (Minimalist / Dark Glassmorphism) | 角色背景、透視視角 (Top-down / 2.5D Isometric / Side-scroller) |
| **2. 硬性限制** | 拓撲面數、PBR 材質、**嚴禁 2D 貼圖冒充**、**鎖定 Hex 色碼** | 8px 基準網格、Design Tokens、**禁止自造任意 class**、純 SVG/Lucide | 像素格大小 (如 32x32)、調色盤 (如 16色)、純洋紅 `#FF00FF` Chroma-key 去背 |
| **3. 行為與時間軸** | 精確到秒的分鏡 (Directed Beats)、單一鐘軸同步 | 完整 5 大狀態機 (Loading, Empty, Error, Active, Action)、微互動動畫 | 幀序列時間軸 (Idle 4幀, Walk 6幀)、Hitbox 碰撞盒、節奏彈性 |
| **4. 驗收與 Critic** | 4~6 台檢驗相機渲染圖、比對參考圖、**線性旋轉即判定失敗** | 多視口截圖 (375/768/1440)、Console 0 Warnings、**文字溢出即失敗** | 像素對齊基準線檢驗、去背純淨度檢驗、循環幀無縫對齊 |

---

## 模態規格書模板庫

### 1. 3D 模態規格模板 (Blender / Three.js)

```markdown
# 任務目標
構建 [專案/資產名稱]，使用 [Headless Blender Python (bpy) / Three.js 單檔 WebGL]，呈現 [具體藝術基調]。

# 幾何與資產限制 (Hard Constraints)
1. 幾何本體：必須是真實且可編輯的 3D 幾何結構。嚴禁使用 2D Billboard、視差深度圖或影片生成取代實體模型。
2. 拓撲分級：遵循「解剖粗模 (Blockout) -> 附屬零件 -> 表面微細節」管線，嚴禁面重疊、法線撕裂或非流形幾何。
3. 材質與調色：
   - 物理 PBR 材質（Base Color, Roughness, Metallic, Normal）。
   - 鎖定調色盤：主色 [Hex], 輔色 [Hex], 環境 [Hex]。嚴禁未受約束的 AI 紫黑霓虹色彩。
4. 交付形式：[單一自包含 HTML 檔案 / 獨立 .blend 檔案與完整 reproducible bpy 腳本]。

# 運動節奏與時間軸 (Timeline Beats)
驅動源：所有動畫必須綁定單一時間時鐘軸 (Elapsed Time)，嚴禁散亂的 Math.random()。
- [0.0s - 4.0s]：[相機機位與運鏡動作，如低角度緩慢推進特寫]
- [4.0s - 10.0s]：[主體關鍵動作展開，次級物理或粒子跟隨]
- [10.0s - 15.0s]：[高潮呈現，平滑銜接回第 0 幀達成無縫循環]

# 驗收標準與自檢迴圈 (Critic-and-Correction Loop)
1. 多視角相機配置：設立 [正面、側面、頂部、45度主視角] 驗收相機，在背景渲染檢驗圖。
2. 自主比對與修復：檢驗是否有浮空物件、破面或材質過曝，至少進行 2 輪修復。
3. 嚴格失敗判定 (Fail Conditions)：
   - 留有任何 `// TODO` 或未完成佔位符即判定失敗。
   - 線性相機無加減速旋轉即判定失敗。
   - 幀率低於 60 FPS 即判定失敗。
```

---

### 2. UI 前端模態規格模板 (React 19 / Tailwind / Radix)

```markdown
# 任務目標
構建企業級 [組件/視圖名稱]（React 19 + Radix UI + Tailwind CSS），符合 [專案名稱] 控制台規範。

# 視覺基調與 Design Tokens (Context & Constraints)
- 排版網格：嚴格遵守 8px 基準網格系統（margin/padding 必須為 8/16/24/32px）。
- 嚴格色票：
  - 背景色：[Hex]、容器卡片：[Hex]、邊框：[Hex]
  - 主文字：[Hex]、次文字：[Hex]
  - 語意狀態色：Success [Hex], Warning [Hex], Error [Hex]
- 圖標規範：嚴禁外部 CDN 圖片，所有圖標純用 lucide-react 具名匯入。
- 響應式：支援 Desktop (1440px) 與 Mobile (375px)，嚴禁出現非預期的水平滾動條 (overflow-x: hidden)。

# 狀態機與互動 (State Machine & Behavior)
必須完整實作 5 大狀態分支，不允許任何狀態缺漏：
1. `loading`：Skeleton 骨架屏脈衝動畫（嚴禁單純放文字或單一 Spinner）。
2. `empty`：空資料時的插畫或友善引導動作。
3. `error`：具備錯誤分類顯示與重試 (Retry) 行為。
4. `active`：即時數據更新時的數值微高亮動畫。
5. `action`：支援無障礙鍵盤方向鍵選擇與焦點環 (Focus Ring)。

# 驗收標準 (Acceptance & Critic Loop)
- 代碼品質：0 TypeScript `any`、0 未使用變數、0 臨時註解。
- 視覺檢核：調用 Playwright 於 375px 與 1440px 進行真機截圖驗收。
- 控制台乾淨度：瀏覽器 Console 必須 0 Error、0 Warning、0 React Missing Key。
```

---

### 3. 2D 資產模態規格模板 (Sprites / Vectors / Tiles)

```markdown
# 任務目標
構建 [角色/物件名稱] 的 2D 動作幀序列圖 (Sprite Sheet) 或向量 SVG。

# 幾何與資產硬約束 (Asset Constraints)
- 網格尺寸：單幀嚴格鎖定 [如 32x32 / 64x64] 像素，整體圖集為 [Rows] 行 × [Cols] 列。
- 調色盤限制：嚴格限制於指定色盤（如 16 色 DB16），禁止產生半透明抗鋸齒髒色。
- 去背標準：採用純洋紅色 `#FF00FF` 作為 Chroma-key 背景色，確保邊緣 0 溢色。

# 動態節奏 (Motion & Animation)
- 動畫分段：
  - Row 1: Idle (4 幀循環)
  - Row 2: Walk (6 幀循環，包含明確的抬腿高點與著地受力緩衝)
  - Row 3: Action / Impact (釋放與收招節奏)
- 重量感：角色在動作循環中需有基準線上下位移 (Bobbing)，體現真實動能。

# 驗收標準 (Critic Criteria)
- 基準線對齊：腳底陰影在動作循環中必須錨定於同一水平參考線，禁止上下浮動。
- 像素檢核：自動化色彩統計檢查，扣除背景後不允許出現色盤外的過渡像素。
```

---

## 呼叫此技能時的 Agent 工作規範

當用戶要求撰寫 Prompt、設計組件或構建 3D/2D 資產時：
1. **先出規格書，不出程式碼**：先產出結構化規格書確認邊界與條件。
2. **消滅形容詞，注入邊界值**：把「精美、好看、科技感」替換為精確 Hex、網格數值、狀態機列表與幀率指標。
3. **注入自我檢查指令**：促使下游模型必須自主截圖、比對缺陷、自我修復後才准宣告完成。
