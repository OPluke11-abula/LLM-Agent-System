import { createServer } from "node:http";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { spawn } from "node:child_process";
import { createHmac } from "node:crypto";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const repo = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const dist = resolve(repo, "viewer", "dist");
const apiPort = Number(process.env.MISSION_E2E_API_PORT || 8765);
const viewerPort = Number(process.env.MISSION_E2E_VIEWER_PORT || 8766);
const credential = `p1-e2e-${crypto.randomUUID()}`;
const jwtSecret = `p1-e2e-secret-${crypto.randomUUID()}-with-enough-length`;
const workspace = resolve(repo, ".e2e-mission-workspace");
const python = process.env.PYTHON || "python";
const edgePath = process.env.EDGE_PATH || ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe"].find((candidate) => existsSync(candidate));
const contentTypes = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css", ".svg": "image/svg+xml" };

if (!existsSync(dist)) throw new Error("viewer/dist does not exist; run npm run build first");
mkdirSync(workspace, { recursive: true });

function startViewer() {
  const server = createServer((request, response) => {
    let pathname = decodeURIComponent(new URL(request.url || "/", `http://127.0.0.1:${viewerPort}`).pathname);
    if (pathname === "/") pathname = "/index.html";
    let filePath = resolve(dist, `.${pathname}`);
    if (!filePath.startsWith(dist) || !existsSync(filePath) || statSync(filePath).isDirectory()) filePath = join(dist, "index.html");
    response.writeHead(200, { "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream" });
    response.end(readFileSync(filePath));
  });
  return new Promise((resolveServer) => server.listen(viewerPort, "127.0.0.1", () => resolveServer(server)));
}

function startApi() {
  return spawn(python, ["-m", "uvicorn", "agent_workspace.api:app", "--host", "127.0.0.1", "--port", String(apiPort)], {
    cwd: repo,
    stdio: "inherit",
    env: {
      ...process.env,
      AGENT_WORKSPACE_DIR: workspace,
      LAS_BOOTSTRAP_API_KEY: credential,
      LAS_JWT_SECRET: jwtSecret,
      LAS_BOOTSTRAP_TENANT_ID: "p1-e2e-tenant",
      LAS_BOOTSTRAP_SUBJECT: "p1-e2e-actor",
      LAS_BOOTSTRAP_ROLE: "tenant",
      LAS_ENABLE_REDIS_SWARM: "false",
      LAS_ENABLE_AUDIT_CONSENSUS: "false",
      LAS_ENABLE_STRIPE: "false",
    },
  });
}

function makeJwt(subject) {
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const header = encode({ alg: "HS256", typ: "JWT" });
  const payload = encode({ iss: "las-api", aud: "las-api", sub: subject, tenant: subject, role: "tenant", scope: "tenant:read", iat: now, nbf: now, exp: now + 600, jti: crypto.randomUUID() });
  const input = `${header}.${payload}`;
  const signature = createHmac("sha256", jwtSecret).update(input).digest("base64url");
  return `${input}.${signature}`;
}

async function waitFor(url, headers = {}, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url, { headers });
      if (response.status !== 503) return response;
    } catch { /* server is still starting */ }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function assert(condition, message) { if (!condition) throw new Error(message); }

const apiHeaders = { "x-api-key": credential };
let viewerServer;
let apiProcess;
let browser;
try {
  apiProcess = startApi();
  const authenticatedCapabilities = await waitFor(`http://127.0.0.1:${apiPort}/v1/system/capabilities`, apiHeaders);
  assert(authenticatedCapabilities.ok, `system preflight failed: ${authenticatedCapabilities.status}`);
  viewerServer = await startViewer();
  if (!edgePath) throw new Error("Microsoft Edge was not found; set EDGE_PATH to a Chromium-compatible browser");
  browser = await chromium.launch({ headless: true, executablePath: edgePath });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript((sessionCredential) => {
    window.__LAS_BROWSER_SESSION_CREDENTIAL__ = sessionCredential;
    window.__LAS_API_BASE_URL__ = "http://127.0.0.1:8765";
    localStorage.setItem("app_lang", JSON.stringify("en"));
    localStorage.setItem("app_theme", JSON.stringify("dark"));
  }, credential);
  const page = await context.newPage();

  await page.goto(`http://127.0.0.1:${viewerPort}/#/system`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "System Check" }).waitFor();
  const continueButton = page.getByRole("link", { name: "Continue to Missions" });
  if (await continueButton.count() === 0) throw new Error(`System Check did not reach authenticated-compatible state:\n${await page.locator("body").innerText()}`);
  await continueButton.click();
  await page.getByRole("heading", { name: "Missions" }).waitFor();
  await page.getByRole("link", { name: "New mission", exact: true }).click();
  await page.getByRole("heading", { name: "New mission" }).waitFor();
  await page.getByLabel("Requirement").fill("Verify the Developer Beta control plane Golden Path");
  await page.getByLabel("Repository reference ID").fill("local/p1-product-contract");
  await page.getByRole("button", { name: "Create mission" }).click();
  await page.getByRole("heading", { name: "Verify the Developer Beta control plane Golden Path" }).waitFor();
  await page.getByRole("button", { name: "Start planning" }).click();
  await page.getByRole("button", { name: "Attach deterministic P1 plan" }).click();
  await page.getByRole("button", { name: "Submit plan" }).click();
  await page.getByRole("button", { name: "Approve exact plan" }).first().click();
  await page.getByRole("button", { name: "Record deterministic evidence + gates" }).click();
  await page.getByText("review ready", { exact: false }).waitFor();

  const missionId = new URL(page.url()).hash.split("/").pop();
  assert(missionId, "mission ID was not present in the detail route");
  await page.getByRole("link", { name: "Open evidence-backed Review" }).click();
  await page.getByRole("heading", { name: "Verify the Developer Beta control plane Golden Path" }).waitFor();
  await page.getByText("Canonical SHA-256").waitFor();
  await page.getByText("Transition history").waitFor();
  await page.reload({ waitUntil: "networkidle" });
  await page.getByText("Evidence records").waitFor();

  const unauthorized = await fetch(`http://127.0.0.1:${apiPort}/v1/system/capabilities`);
  assert(unauthorized.status === 401, `unauthenticated system check returned ${unauthorized.status}`);
  const ownership = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}`, { headers: { authorization: `Bearer ${makeJwt("p1-other-actor")}` } });
  assert(ownership.status === 404, `cross-owner mission read returned ${ownership.status}`);
  const currentResponse = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}`, { headers: apiHeaders });
  const current = await currentResponse.json();
  const stale = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/transitions`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ event: "close", idempotency_key: `stale-${crypto.randomUUID()}`, expected_revision: 0 }) });
  assert(stale.status === 409, `stale revision returned ${stale.status}`);
  const approval = current.approval_gates?.[0];
  if (approval) {
    const conflict = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/approvals`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ gate_id: `conflict-${crypto.randomUUID()}`, gate_type: approval.gate_type, subject: approval.subject, status: "rejected", evidence_refs: [], idempotency_key: `conflict-${crypto.randomUUID()}`, expected_revision: current.revision }) });
    assert(conflict.status === 409, `conflicting approval returned ${conflict.status}`);
  }
  await context.close();
  console.log(JSON.stringify({ authenticatedGoldenPath: "passed", unauthorized: 401, ownershipIsolation: 404, staleRevision: 409, conflictingApproval: approval ? 409 : "not-applicable" }));
} finally {
  if (browser) await browser.close();
  if (viewerServer) await new Promise((resolveClose) => viewerServer.close(resolveClose));
  if (apiProcess && !apiProcess.killed) apiProcess.kill();
}
