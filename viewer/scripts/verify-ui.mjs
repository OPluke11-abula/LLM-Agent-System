import { createServer } from "node:http";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const viewerRoot = fileURLToPath(new URL("..", import.meta.url));
const root = resolve(viewerRoot, "dist");
const outputRoot = resolve(process.env.UI_VERIFY_OUTPUT_DIR || resolve(viewerRoot, "output", "ui-regression"));
const topologyViewPath = resolve(viewerRoot, "src", "components", "TopologyView.tsx");
const topologyViewSource = readFileSync(topologyViewPath, "utf8");
const tokenModePanelPath = resolve(viewerRoot, "src", "components", "TokenModePanel.tsx");
const tokenModePanelSource = readFileSync(tokenModePanelPath, "utf8");
const port = Number(process.env.UI_VERIFY_PORT || 5175);
const takeScreenshots = process.env.UI_VERIFY_SCREENSHOTS === "1" || process.argv.includes("--screenshots");
const screenshotTimeoutMs = Number(process.env.UI_VERIFY_SCREENSHOT_TIMEOUT_MS || 20_000);
const strictScreenshots = takeScreenshots && process.env.UI_VERIFY_STRICT_SCREENSHOTS !== "0";
const edgePath = process.env.EDGE_PATH || [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
].find((candidate) => existsSync(candidate));

if (!existsSync(root)) {
  throw new Error("dist/ does not exist. Run `npm run build` before `npm run verify:ui`.");
}

if (takeScreenshots && !edgePath) {
  throw new Error("Microsoft Edge was not found. Set EDGE_PATH to a Chromium-compatible browser executable.");
}

mkdirSync(outputRoot, { recursive: true });

const visualFixtureState = {
  workspaces: [
    {
      id: "visual-qa-workspace",
      name: "Visual QA Workspace",
      lang: "TypeScript",
      path: "D:\\GitHub\\LLM-Agent-System\\agent_workspace",
    },
  ],
  active_ws_id: "visual-qa-workspace",
  ai_rules_arr: [
    "Verify generated plans against live repository state before marking work complete.",
    "Keep UI evidence bounded to the routes and breakpoints named in the active task.",
    "Report failed gates with the exact command and first actionable error.",
  ],
  mods_agents_enabled: true,
  mods_skills: {
    "backend-architect": true,
    "ui-ux-pro-max-skill": true,
    "qa-auto-tester-pro": true,
    "code-review-ai-ai-review": true,
  },
  memory_map: {
    "visual-qa-workspace": {
      tasks: [
        {
          id: "task-001",
          description: "Initialize desktop topology viewer scaffold",
          status: "completed",
          dependencies: [],
          ai_feedback: "Production build and route shell verified.",
          tasks: [],
        },
        {
          id: "task-002",
          description: "Render DAG from agent memory with deterministic layout",
          status: "in_progress",
          dependencies: ["task-001"],
          ai_feedback: "Visual QA fixture keeps the active mission populated.",
          tasks: [],
        },
        {
          id: "task-003",
          description: "Close visual QA evidence with screenshots and copy audit",
          status: "pending",
          dependencies: ["task-002"],
          ai_feedback: null,
          tasks: [],
        },
      ],
    },
  },
};

const fixtureScript = Object.entries(visualFixtureState)
  .map(([key, value]) => `localStorage.setItem(${JSON.stringify(key)}, ${JSON.stringify(JSON.stringify(value))});`)
  .join("\n");

const topologyStructuralMemoryMarkers = [
  "data-testid=\"structural-memory-surface\"",
  "Structural Memory",
  "code_graph_refs",
  "impact_summary",
  "security_relevant_paths",
];

function assertIncludes(source, token, label) {
  if (!source.includes(token)) {
    throw new Error(`${label} missing: ${token}`);
  }
}

for (const marker of topologyStructuralMemoryMarkers) {
  assertIncludes(topologyViewSource, marker, "topology structural memory source marker");
}

const tokenModeSourceMarkers = [
  "data-testid=\"token-mode-panel\"",
  "Largest contributors",
  "Recommended next action",
  "Verification profile",
  "handoffRecommended",
];

for (const marker of tokenModeSourceMarkers) {
  assertIncludes(tokenModePanelSource, marker, "token mode source marker");
}

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

const server = createServer((request, response) => {
  const url = new URL(request.url || "/", `http://127.0.0.1:${port}`);

  if (url.pathname === "/__seed") {
    const route = url.searchParams.get("route") || "/";
    const onboarded = url.searchParams.get("onboarded") !== "false";
    const lang = url.searchParams.get("lang") || "en";
    const html = `<!doctype html><html><body><script>
      ${fixtureScript}
      localStorage.setItem("has_onboarded", JSON.stringify(${JSON.stringify(onboarded)}));
      localStorage.setItem("app_lang", JSON.stringify(${JSON.stringify(lang)}));
      localStorage.setItem("app_theme", JSON.stringify("dark"));
      window.location.replace(${JSON.stringify(route)});
    </script></body></html>`;
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    response.end(html);
    return;
  }

  let pathname = decodeURIComponent(url.pathname);
  if (pathname === "/") pathname = "/index.html";
  let filePath = resolve(root, `.${pathname}`);

  if (!filePath.startsWith(root)) {
    response.writeHead(403);
    response.end("forbidden");
    return;
  }

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(root, "index.html");
  }

  response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
  response.end(readFileSync(filePath));
});

await new Promise((resolveListen) => server.listen(port, "127.0.0.1", resolveListen));

const scenarios = [
  { name: "dashboard-desktop", route: "/", onboarded: true, width: 1280, height: 900, nextActionRail: true, interactionProbe: true },
  { name: "dashboard-tablet", route: "/", onboarded: true, width: 768, height: 1024, nextActionRail: true },
  { name: "dashboard-mobile", route: "/", onboarded: true, width: 375, height: 812, nextActionRail: true },
  { name: "next-action-rail-mobile", route: "/", onboarded: true, width: 375, height: 812, nextActionRail: true, scrollToRail: true },
  { name: "task-flow-desktop", route: "/#/tasks", onboarded: true, width: 1280, height: 900, taskFlow: true },
  { name: "task-flow-tablet", route: "/#/tasks", onboarded: true, width: 768, height: 1024, taskFlow: true },
  { name: "task-flow-mobile", route: "/#/tasks", onboarded: true, width: 375, height: 812, taskFlow: true },
  { name: "intelligence-map-desktop", route: "/#/intelligence", onboarded: true, width: 1280, height: 900, intelligenceMap: true },
  { name: "intelligence-map-mobile", route: "/#/intelligence", onboarded: true, width: 375, height: 812, intelligenceMap: true },
  { name: "command-palette-desktop", route: "/", onboarded: true, width: 1280, height: 900, commandPalette: true },
  { name: "rules-desktop", route: "/#/rules", onboarded: true, width: 1280, height: 900 },
  { name: "mods-desktop", route: "/#/mods", onboarded: true, width: 1280, height: 900 },
  { name: "settings-desktop", route: "/#/settings", onboarded: true, width: 1280, height: 900 },
  { name: "settings-mobile", route: "/#/settings", onboarded: true, width: 375, height: 812 },
  { name: "admin-desktop", route: "/#/admin", onboarded: true, width: 1280, height: 900 },
  { name: "governance-cockpit-desktop", route: "/#/admin", onboarded: true, width: 1280, height: 900, governanceCockpit: true },
  { name: "governance-cockpit-mobile", route: "/#/admin", onboarded: true, width: 375, height: 812, governanceCockpit: true },
  { name: "onboarding-desktop", route: "/", onboarded: false, width: 1280, height: 900 },
  { name: "dashboard-reduced-motion", route: "/", onboarded: true, width: 1280, height: 900, nextActionRail: true, reducedMotion: true },
];

const copyAuditScenarios = [
  {
    name: "rules-zh-copy",
    route: "/#/rules",
    requiredText: ["AI 指令規則", "政策層", "移除"],
    forbiddenText: ["Policy Layer", "AI Instruction Rules", "Remove"],
  },
  {
    name: "mods-zh-copy",
    route: "/#/mods",
    requiredText: ["技能登錄", "寫回開啟", "後端架構師"],
    forbiddenText: ["Skill Registry", "Writeback Off", "Backend Architect"],
  },
  {
    name: "settings-zh-copy",
    route: "/#/settings",
    requiredText: ["控制偏好", "設定", "介面語言"],
    forbiddenText: ["Control Preferences", "UI Language", "Save LLM Config"],
  },
];

async function auditRenderedCopy(page, scenario) {
  const text = await page.locator("body").innerText({ timeout: screenshotTimeoutMs });
  if (!text.trim()) {
    throw new Error(`${scenario.name} rendered-copy audit found an empty page`);
  }
  for (const token of scenario.requiredText) {
    assertIncludes(text, token, `${scenario.name} rendered-copy audit`);
  }
  for (const token of scenario.forbiddenText) {
    if (text.includes(token)) {
      throw new Error(`${scenario.name} rendered-copy audit found untranslated text: ${token}`);
    }
  }
  if (/(^|\n)\s*\p{Extended_Pictographic}\s+/u.test(text)) {
    throw new Error(`${scenario.name} rendered-copy audit found a visible emoji prefix`);
  }
}

try {
  if (!takeScreenshots) {
    console.log("screenshots skipped");
  }

  for (const scenario of takeScreenshots ? scenarios : []) {
    const screenshotPath = join(outputRoot, `${scenario.name}.png`);
    const url = `http://127.0.0.1:${port}/__seed?route=${encodeURIComponent(scenario.route)}&onboarded=${scenario.onboarded}`;

    let browser;
    try {
      browser = await chromium.launch({
        executablePath: edgePath,
        headless: true,
        timeout: screenshotTimeoutMs,
        args: [
          "--hide-scrollbars",
          "--disable-background-networking",
          "--disable-extensions",
          "--disable-sync",
          "--use-angle=swiftshader",
          "--use-gl=swiftshader",
          "--enable-unsafe-swiftshader",
        ],
      });
      const context = await browser.newContext({
        viewport: { width: scenario.width, height: scenario.height },
        deviceScaleFactor: 1,
        reducedMotion: scenario.reducedMotion ? "reduce" : "no-preference",
      });
      const page = await context.newPage();
      page.setDefaultTimeout(screenshotTimeoutMs);
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: screenshotTimeoutMs });
      await page.locator("body").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
      await page.waitForTimeout(1000);
      if (scenario.nextActionRail) {
        const rail = page.getByTestId("next-action-rail");
        await rail.waitFor({ state: "visible", timeout: screenshotTimeoutMs });
        if (scenario.scrollToRail) {
          await rail.scrollIntoViewIfNeeded({ timeout: screenshotTimeoutMs });
          await page.waitForTimeout(300);
        }
      }
      if (scenario.taskFlow) {
        await page.getByTestId("task-flow-timeline").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
        await page.getByTestId("task-intelligence-panel").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
      }
      if (scenario.intelligenceMap) {
        await page.getByTestId("intelligence-map").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
      }
      if (scenario.governanceCockpit) {
        const cockpit = page.getByTestId("governance-security-cockpit");
        await cockpit.waitFor({ state: "visible", timeout: screenshotTimeoutMs });
        await cockpit.evaluate((node) => node.scrollIntoView({ block: "start", inline: "nearest" }));
        await page.waitForTimeout(300);
      }
      if (scenario.commandPalette) {
        await page.keyboard.press("Control+K");
        await page.getByRole("dialog", { name: "Command Palette" }).waitFor({ state: "visible", timeout: screenshotTimeoutMs });
        await page.getByRole("textbox", { name: /type verify/i }).fill("verify");
        await page.getByRole("option", { name: /Verify workspace/i }).waitFor({ state: "visible", timeout: screenshotTimeoutMs });
      }
      if (scenario.interactionProbe) {
        const paletteButton = page.getByRole("button", { name: /command palette/i });
        await paletteButton.focus({ timeout: screenshotTimeoutMs });
        await page.keyboard.press("Tab");
        await page.getByRole("link", { name: "Task Flow Flow" }).hover({ timeout: screenshotTimeoutMs });
      }
      await page.screenshot({ path: screenshotPath, fullPage: true, timeout: screenshotTimeoutMs });
      await context.close();
    } catch (error) {
      if (strictScreenshots) {
        throw error;
      }
      console.warn(`warning: skipped ${scenario.name} screenshot: ${error.message}`);
      continue;
    } finally {
      await browser?.close();
    }

    if (!existsSync(screenshotPath) || statSync(screenshotPath).size === 0) {
      throw new Error(`Edge exited without writing a screenshot: ${screenshotPath}`);
    }

    console.log(`captured ${scenario.name}: ${screenshotPath}`);
  }

  if (takeScreenshots) {
    for (const scenario of copyAuditScenarios) {
      const url = `http://127.0.0.1:${port}/__seed?route=${encodeURIComponent(scenario.route)}&onboarded=true&lang=zh`;
      let browser;
      try {
        browser = await chromium.launch({
          executablePath: edgePath,
          headless: true,
          timeout: screenshotTimeoutMs,
          args: [
            "--hide-scrollbars",
            "--disable-background-networking",
            "--disable-extensions",
            "--disable-sync",
            "--use-angle=swiftshader",
            "--use-gl=swiftshader",
            "--enable-unsafe-swiftshader",
          ],
        });
        const context = await browser.newContext({
          viewport: { width: 1280, height: 900 },
          deviceScaleFactor: 1,
        });
        const page = await context.newPage();
        page.setDefaultTimeout(screenshotTimeoutMs);
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: screenshotTimeoutMs });
        await page.locator("body").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
        await page.waitForTimeout(500);
        await auditRenderedCopy(page, scenario);
        await context.close();
      } finally {
        await browser?.close();
      }
      console.log(`audited rendered copy: ${scenario.name}`);
    }
  }

  const assetsDir = join(root, "assets");
  const jsChunks = readdirSync(assetsDir)
    .filter((name) => name.endsWith(".js"))
    .map((name) => {
      const sizeKb = statSync(join(assetsDir, name)).size / 1024;
      return { name, sizeKb };
    })
    .sort((a, b) => b.sizeKb - a.sizeKb);
  const largest = jsChunks[0];
  console.log(`largest js chunk: ${largest.name} ${largest.sizeKb.toFixed(2)} kB`);
  if (largest.sizeKb > 500) {
    throw new Error(`Largest JS chunk exceeds 500 kB: ${largest.sizeKb.toFixed(2)} kB`);
  }

  const topologyChunk = jsChunks.find((chunk) => chunk.name.startsWith("TopologyView-"));
  if (!topologyChunk) {
    throw new Error("TopologyView production chunk missing. Run `npm run build` first.");
  }
  const topologyChunkSource = readFileSync(join(assetsDir, topologyChunk.name), "utf8");
  for (const marker of ["structural-memory-surface", "Structural Memory", "code_graph_refs", "impact_summary"]) {
    assertIncludes(topologyChunkSource, marker, "topology structural memory production marker");
  }
} finally {
  await new Promise((resolveClose) => server.close(resolveClose));
}
