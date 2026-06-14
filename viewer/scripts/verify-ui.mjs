import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { tmpdir } from "node:os";

const root = resolve("dist");
const outputRoot = resolve("output", "ui-regression");
const port = Number(process.env.UI_VERIFY_PORT || 5175);
const takeScreenshots = process.env.UI_VERIFY_SCREENSHOTS === "1" || process.argv.includes("--screenshots");
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
    const userDataDir = join(tmpdir(), `las-ui-${scenario.name}-${Date.now()}`);
    const screenshotPath = join(outputRoot, `${scenario.name}.png`);
    const url = `http://127.0.0.1:${port}/__seed?route=${encodeURIComponent(scenario.route)}&onboarded=${scenario.onboarded}`;
    const commonArgs = [
      "--hide-scrollbars",
      "--no-first-run",
      "--disable-background-networking",
      "--disable-extensions",
      "--disable-sync",
      `--user-data-dir=${userDataDir}`,
      `--window-size=${scenario.width},${scenario.height}`,
      "--virtual-time-budget=3000",
      `--screenshot=${screenshotPath}`,
      url,
    ];
    const attempts = [
      [
        "--headless=new",
        "--use-angle=swiftshader",
        "--use-gl=swiftshader",
        "--enable-unsafe-swiftshader",
        "--disable-gpu-sandbox",
        "--disable-features=VizDisplayCompositor",
        ...commonArgs,
      ],
      [
        "--headless",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-gpu-compositing",
        ...commonArgs,
      ],
    ];
    let lastError;
    for (const args of attempts) {
      try {
        execFileSync(edgePath, args, { stdio: "pipe", timeout: 8_000, windowsHide: true });
        lastError = null;
        break;
      } catch (error) {
        lastError = error;
      }
    }
    if (lastError) {
      if (process.env.UI_VERIFY_STRICT_SCREENSHOTS === "1") {
        throw lastError;
      }
      console.warn(`warning: skipped ${scenario.name} screenshot because Edge headless did not finish within 8s`);
      rmSync(userDataDir, { recursive: true, force: true });
      continue;
    }
    rmSync(userDataDir, { recursive: true, force: true });
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
} finally {
  await new Promise((resolveClose) => server.close(resolveClose));
}
