import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)), "dist");
const outputRoot = resolve(process.env.UI_VERIFY_OUTPUT_DIR || resolve(root, "..", "output", "ui-mission"));
const port = Number(process.env.UI_VERIFY_PORT || 5176);
const takeScreenshots = process.argv.includes("--screenshots");
const edgePath = process.env.EDGE_PATH || ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe"].find((candidate) => existsSync(candidate));
const contentTypes = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml" };

if (!existsSync(root)) throw new Error("viewer/dist does not exist; run npm run build first");
if (takeScreenshots && !edgePath) throw new Error("Microsoft Edge was not found");
if (takeScreenshots) mkdirSync(outputRoot, { recursive: true });

const server = createServer((request, response) => {
  let pathname = decodeURIComponent(new URL(request.url || "/", `http://127.0.0.1:${port}`).pathname);
  if (pathname === "/") pathname = "/index.html";
  let filePath = resolve(root, `.${pathname}`);
  if (!filePath.startsWith(root) || !existsSync(filePath) || statSync(filePath).isDirectory()) filePath = join(root, "index.html");
  response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
  response.end(readFileSync(filePath));
});

await new Promise((resolveListen) => server.listen(port, "127.0.0.1", resolveListen));
const browser = await chromium.launch({ headless: true, executablePath: edgePath });
const routes = ["missions", "missions/new", "review", "knowledge", "system"];
const viewports = [{ name: "desktop", width: 1280, height: 900 }, { name: "mobile", width: 390, height: 844 }];
for (const viewport of viewports) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  await context.addInitScript(() => {
    localStorage.setItem("has_onboarded", JSON.stringify(true));
    localStorage.setItem("app_lang", JSON.stringify("en"));
    localStorage.setItem("app_theme", JSON.stringify("dark"));
  });
  const page = await context.newPage();
  for (const route of routes) {
    await page.goto(`http://127.0.0.1:${port}/#/${route}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const checks = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      heading: Boolean(document.querySelector("h1")),
      nestedControls: document.querySelectorAll("a button, button a").length,
      activeLinks: document.querySelectorAll('[aria-current="page"]').length,
    }));
    if (checks.overflow || !checks.heading || checks.nestedControls > 0 || checks.activeLinks > 1) throw new Error(`${route}/${viewport.name} failed ${JSON.stringify(checks)}`);
    if (takeScreenshots) await page.screenshot({ path: join(outputRoot, `${route.replaceAll("/", "-")}-${viewport.name}.png`), fullPage: true });
    console.log(`${route} ${viewport.name} ${JSON.stringify(checks)}`);
  }
  await context.close();
}
await browser.close();
await new Promise((resolveClose) => server.close(resolveClose));
