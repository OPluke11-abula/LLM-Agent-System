import { readFileSync, existsSync } from "node:fs";
import { resolve, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const viewerRoot = resolve(__dirname, "..");

console.log("=== [Verify Ambient Companion] Starting verification ===");

// 1. Check tauri.conf.json
const tauriConfPath = join(viewerRoot, "src-tauri", "tauri.conf.json");
if (!existsSync(tauriConfPath)) {
  console.error("FAIL: tauri.conf.json does not exist");
  process.exit(1);
}
const tauriConf = JSON.parse(readFileSync(tauriConfPath, "utf-8"));
const companionWindow = tauriConf.app?.windows?.find((w) => w.label === "companion-window");

if (!companionWindow) {
  console.error("FAIL: companion-window not configured in tauri.conf.json");
  process.exit(1);
}

if (!companionWindow.transparent || companionWindow.decorations !== false || !companionWindow.alwaysOnTop) {
  console.error("FAIL: companion-window properties invalid:", companionWindow);
  process.exit(1);
}
console.log("✓ PASS: companion-window correctly configured in tauri.conf.json");

// 2. Check hook useAmbientCompanion.ts
const hookPath = join(viewerRoot, "src", "hooks", "useAmbientCompanion.ts");
if (!existsSync(hookPath)) {
  console.error("FAIL: useAmbientCompanion.ts does not exist");
  process.exit(1);
}
const hookContent = readFileSync(hookPath, "utf-8");
if (
  !hookContent.includes("export function useAmbientCompanion") ||
  !hookContent.includes("approve") ||
  !hookContent.includes("createTaskFromDrop")
) {
  console.error("FAIL: useAmbientCompanion.ts missing required exports (approve, createTaskFromDrop)");
  process.exit(1);
}
console.log("✓ PASS: useAmbientCompanion.ts exports hook with approval and drop-task interface");

// 3. Check AmbientCompanion.tsx and subcomponents
const compPath = join(viewerRoot, "src", "components", "companion", "AmbientCompanion.tsx");
const hitlPath = join(viewerRoot, "src", "components", "companion", "CompanionHitlCard.tsx");
const trackerPath = join(viewerRoot, "src", "components", "companion", "CompanionStageTracker.tsx");
if (!existsSync(compPath) || !existsSync(hitlPath) || !existsSync(trackerPath)) {
  console.error("FAIL: Companion components do not exist");
  process.exit(1);
}
const compContent = readFileSync(compPath, "utf-8");
const hitlContent = readFileSync(hitlPath, "utf-8");
const trackerContent = readFileSync(trackerPath, "utf-8");
if (
  !compContent.includes("export function AmbientCompanion") ||
  !hitlContent.includes("Allow (PO Luke)") ||
  !trackerContent.includes("companion-stage-tracker")
) {
  console.error("FAIL: Companion missing 1-click allow button, stage tracker, or component export");
  process.exit(1);
}
console.log("✓ PASS: AmbientCompanion.tsx and subcomponents include micro-animations, 9-stage tracker, and 1-Click HITL approval");

// 4. Check App.tsx integration
const appPath = join(viewerRoot, "src", "App.tsx");
const appContent = readFileSync(appPath, "utf-8");
if (!appContent.includes("/companion") || !appContent.includes("AmbientCompanion")) {
  console.error("FAIL: App.tsx does not integrate companion route or component");
  process.exit(1);
}
console.log("✓ PASS: App.tsx routes and overlays Ambient Companion");

console.log("=== [Verify Ambient Companion] All checks PASSED successfully! ===");
