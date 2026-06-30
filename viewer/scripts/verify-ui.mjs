import { createServer } from "node:http";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const viewerRoot = fileURLToPath(new URL("..", import.meta.url));
const root = resolve(viewerRoot, "dist");
const outputRoot = resolve(viewerRoot, "output", "ui-regression");
const topologyViewPath = resolve(viewerRoot, "src", "components", "TopologyView.tsx");
const topologyViewSource = readFileSync(topologyViewPath, "utf8");
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
    const html = `<!doctype html><html><body><script>
      localStorage.setItem("has_onboarded", JSON.stringify(${JSON.stringify(onboarded)}));
      localStorage.setItem("app_lang", JSON.stringify("en"));
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
  { name: "dashboard-desktop", route: "/", onboarded: true, width: 1440, height: 950 },
  { name: "dashboard-mobile", route: "/", onboarded: true, width: 390, height: 844 },
  { name: "settings-desktop", route: "/#/settings", onboarded: true, width: 1440, height: 950 },
  { name: "admin-desktop", route: "/#/admin", onboarded: true, width: 1440, height: 950 },
  { name: "onboarding-desktop", route: "/", onboarded: false, width: 1440, height: 950 },
];

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
      });
      const page = await context.newPage();
      page.setDefaultTimeout(screenshotTimeoutMs);
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: screenshotTimeoutMs });
      await page.locator("body").waitFor({ state: "visible", timeout: screenshotTimeoutMs });
      await page.waitForTimeout(1000);
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
