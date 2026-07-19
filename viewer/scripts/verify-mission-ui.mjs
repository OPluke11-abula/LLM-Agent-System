import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)), "dist");
const outputRoot = resolve(process.env.UI_VERIFY_OUTPUT_DIR || resolve(root, "..", "output", "ui-mission"));
const port = Number(process.env.UI_VERIFY_PORT || 5176);
const mismatchPort = port + 1;
const takeScreenshots = process.argv.includes("--screenshots");
const contentTypes = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml" };

if (!existsSync(root)) throw new Error("viewer/dist does not exist; run npm run build first");
if (takeScreenshots) mkdirSync(outputRoot, { recursive: true });

const server = createServer((request, response) => {
  let pathname = decodeURIComponent(new URL(request.url || "/", `http://127.0.0.1:${port}`).pathname);
  if (pathname === "/") pathname = "/index.html";
  let filePath = resolve(root, `.${pathname}`);
  if (!filePath.startsWith(root) || !existsSync(filePath) || statSync(filePath).isDirectory()) filePath = join(root, "index.html");
  response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
  response.end(readFileSync(filePath));
});
const mismatchServer = createServer((request, response) => {
  const headers = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type,x-api-key", "Access-Control-Allow-Methods": "GET,OPTIONS" };
  if (request.method === "OPTIONS") {
    response.writeHead(204, headers);
    response.end();
    return;
  }
  response.writeHead(200, headers);
  response.end(JSON.stringify({ api_reachable: true, authentication_valid: true, workspace_root_available: true, mission_store_available: true, contract_schema_version: "0.9", schema_compatible: false, provider_configuration: "not_configured", git_integration: "not_implemented", github_integration: "not_implemented", repository_inspection: "not_implemented", agent_execution: "not_implemented", draft_pr_delivery: "not_implemented" }));
});

await new Promise((resolveListen) => server.listen(port, "127.0.0.1", resolveListen));
await new Promise((resolveListen) => mismatchServer.listen(mismatchPort, "127.0.0.1", resolveListen));
const browser = await chromium.launch({ headless: true });
try {
  const browserContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await browserContext.newPage();
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "System Check" }).waitFor();
  if (await page.getByLabel("Browser session credential").count() !== 1) throw new Error("first-run credential field is missing");
  const browserSecrets = await page.evaluate(() => ({ global: "__LAS_BROWSER_SESSION_CREDENTIAL__" in window, storage: `${localStorage} ${sessionStorage}`.includes("LAS_BROWSER_SESSION_CREDENTIAL") }));
  if (browserSecrets.global || browserSecrets.storage) throw new Error(`browser credential boundary failed ${JSON.stringify(browserSecrets)}`);
  if ((await page.locator("body").innerText()).includes("Record deterministic evidence + gates")) throw new Error("production UI still exposes fabricated evidence control");
  if (takeScreenshots) await page.screenshot({ path: join(outputRoot, "system-first-run.png"), fullPage: true });
  console.log(`system-first-run ${JSON.stringify(browserSecrets)}`);
  await browserContext.close();

  const mismatchContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await mismatchContext.addInitScript((baseUrl) => { window.__LAS_API_BASE_URL__ = baseUrl; }, `http://127.0.0.1:${mismatchPort}`);
  const mismatchPage = await mismatchContext.newPage();
  await mismatchPage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await mismatchPage.getByLabel("Browser session credential").fill("schema-mismatch-test");
  await mismatchPage.getByRole("button", { name: "Check session" }).click();
  await mismatchPage.getByText("schema mismatch", { exact: true }).waitFor();
  console.log("schema-mismatch blocked");
  await mismatchContext.close();

  const tauriContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await tauriContext.addInitScript(() => { window.__TAURI_INTERNALS__ = {}; });
  const tauriPage = await tauriContext.newPage();
  await tauriPage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await tauriPage.getByText("Tauri Mission authentication unavailable").waitFor();
  if (await tauriPage.getByRole("link", { name: "Continue to Missions" }).count() !== 0) throw new Error("Tauri entered the authenticated journey");
  console.log("tauri-unavailable passed");
  await tauriContext.close();
} finally {
  await browser.close();
  await new Promise((resolveClose) => server.close(resolveClose));
  await new Promise((resolveClose) => mismatchServer.close(resolveClose));
}
