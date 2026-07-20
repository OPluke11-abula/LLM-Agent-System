import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)), "dist");
const outputRoot = resolve(process.env.UI_VERIFY_OUTPUT_DIR || resolve(root, "..", "output", "ui-mission"));
const port = Number(process.env.UI_VERIFY_PORT || 5176);
const mismatchPort = port + 1;
const storeUnavailablePort = port + 2;
const slowPort = port + 3;
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

function capabilityServer(portNumber, capabilities, delayMs = 0) {
  return createServer((request, response) => {
    const headers = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type,x-api-key", "Access-Control-Allow-Methods": "GET,OPTIONS" };
    if (request.method === "OPTIONS") { response.writeHead(204, headers); response.end(); return; }
    response.writeHead(200, headers);
    setTimeout(() => response.end(JSON.stringify({ api_reachable: true, authentication_valid: true, workspace_root_available: true, ...capabilities, provider_configuration: "not_configured", git_integration: "not_implemented", github_integration: "not_implemented", repository_inspection: "not_implemented", agent_execution: "not_implemented", draft_pr_delivery: "not_implemented" })), delayMs);
  });
}

const mismatchServer = capabilityServer(mismatchPort, { mission_store_available: true, contract_schema_version: "0.9" });
const storeUnavailableServer = capabilityServer(storeUnavailablePort, { mission_store_available: false, contract_schema_version: "1.0" });
const slowServer = capabilityServer(slowPort, { mission_store_available: true, contract_schema_version: "1.0" }, 10000);
const listen = (instance, portNumber) => new Promise((resolveListen) => instance.listen(portNumber, "127.0.0.1", resolveListen));
const close = (instance) => new Promise((resolveClose) => instance.close(resolveClose));

await Promise.all([listen(server, port), listen(mismatchServer, mismatchPort), listen(storeUnavailableServer, storeUnavailablePort), listen(slowServer, slowPort)]);
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
  if (await mismatchPage.getByRole("link", { name: "Continue to Missions" }).count() !== 0) throw new Error("schema mismatch allowed continuation");
  if (!(await mismatchPage.locator("body").innerText()).includes("0.9 / Viewer 1.0")) throw new Error("schema versions were not shown");
  console.log("schema-mismatch blocked");
  await mismatchContext.close();

  const storeContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await storeContext.addInitScript((baseUrl) => { window.__LAS_API_BASE_URL__ = baseUrl; }, `http://127.0.0.1:${storeUnavailablePort}`);
  const storePage = await storeContext.newPage();
  await storePage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await storePage.getByLabel("Browser session credential").fill("store-unavailable-test");
  await storePage.getByRole("button", { name: "Check session" }).click();
  await storePage.getByText("authenticated storage unavailable", { exact: true }).waitFor();
  if (await storePage.getByRole("link", { name: "Continue to Missions" }).count() !== 0) throw new Error("unavailable store allowed continuation");
  console.log("store-unavailable blocked");
  await storeContext.close();

  const offlineContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await offlineContext.addInitScript((baseUrl) => { window.__LAS_API_BASE_URL__ = baseUrl; }, `http://127.0.0.1:${port + 4}`);
  const offlinePage = await offlineContext.newPage();
  await offlinePage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await offlinePage.getByLabel("Browser session credential").fill("offline-test");
  await offlinePage.getByRole("button", { name: "Check session" }).click();
  await offlinePage.getByText("unreachable", { exact: true }).waitFor();
  if (await offlinePage.getByRole("link", { name: "Continue to Missions" }).count() !== 0) throw new Error("offline backend allowed continuation");
  console.log("backend-offline blocked");
  await offlineContext.close();

  const abortedContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await abortedContext.addInitScript((baseUrl) => { window.__LAS_API_BASE_URL__ = baseUrl; }, `http://127.0.0.1:${slowPort}`);
  const abortedPage = await abortedContext.newPage();
  await abortedPage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await abortedPage.getByLabel("Browser session credential").fill("abort-test");
  await abortedPage.getByRole("button", { name: "Check session" }).click();
  await abortedPage.getByRole("button", { name: "Cancel check" }).click();
  await abortedPage.getByText("aborted", { exact: true }).waitFor();
  if (await abortedPage.getByRole("link", { name: "Continue to Missions" }).count() !== 0) throw new Error("aborted request allowed continuation");
  console.log("aborted-request blocked");
  await abortedContext.close();

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
  await Promise.all([close(server), close(mismatchServer), close(storeUnavailableServer), close(slowServer)]);
}
