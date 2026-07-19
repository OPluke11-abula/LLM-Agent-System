import { createServer } from "node:http";
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { spawn } from "node:child_process";
import { createHmac, randomUUID } from "node:crypto";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const repo = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const dist = resolve(repo, "viewer", "dist");
const apiPort = Number(process.env.MISSION_E2E_API_PORT || 8765);
const viewerPort = Number(process.env.MISSION_E2E_VIEWER_PORT || 8766);
const credential = `p1-e2e-${randomUUID()}`;
const jwtSecret = `p1-e2e-secret-${randomUUID()}-with-enough-length`;
const workspace = mkdtempSync(join(tmpdir(), "las-mission-e2e-"));
const python = process.env.PYTHON || "python";
const contentTypes = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css", ".svg": "image/svg+xml" };

if (!existsSync(dist)) throw new Error("viewer/dist does not exist; run npm run build first");

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
    env: { ...process.env, OTEL_SDK_DISABLED: "true", AGENT_WORKSPACE_DIR: workspace, LAS_BOOTSTRAP_API_KEY: credential, LAS_JWT_SECRET: jwtSecret, LAS_BOOTSTRAP_TENANT_ID: "p1-e2e-tenant", LAS_BOOTSTRAP_SUBJECT: "p1-e2e-actor", LAS_BOOTSTRAP_ROLE: "tenant", LAS_ENABLE_REDIS_SWARM: "false", LAS_ENABLE_AUDIT_CONSENSUS: "false", LAS_ENABLE_STRIPE: "false", LAS_ENABLE_MISSION_TEST_FIXTURE: "true" },
  });
}

function makeJwt(subject) {
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const header = encode({ alg: "HS256", typ: "JWT" });
  const payload = encode({ iss: "las-api", aud: "las-api", sub: subject, tenant: subject, role: "tenant", scope: "tenant:read", iat: now, nbf: now, exp: now + 600, jti: randomUUID() });
  const input = `${header}.${payload}`;
  return `${input}.${createHmac("sha256", jwtSecret).update(input).digest("base64url")}`;
}

async function waitFor(url, headers = {}, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url, { headers });
      if (response.status !== 503) return response;
    } catch {}
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function assert(condition, message) { if (!condition) throw new Error(message); }

const apiHeaders = { "x-api-key": credential };
const fixtureTypes = { requirement: "command", scope: "scope", architecture: "architecture", tests: "test", security: "security", quality: "quality", ci: "ci", cost: "cost" };
let viewerServer;
let apiProcess;
let browser;
try {
  apiProcess = startApi();
  const authenticatedCapabilities = await waitFor(`http://127.0.0.1:${apiPort}/v1/system/capabilities`, apiHeaders);
  assert(authenticatedCapabilities.ok, `system preflight failed: ${authenticatedCapabilities.status}`);
  viewerServer = await startViewer();
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript(() => { window.__LAS_API_BASE_URL__ = "http://127.0.0.1:8765"; });
  const page = await context.newPage();

  await page.goto(`http://127.0.0.1:${viewerPort}/`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "System Check" }).waitFor();
  const credentialField = page.getByLabel("Browser session credential");
  assert(await credentialField.count() === 1, "first-run browser credential field was not shown");
  await credentialField.fill(credential);
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByRole("link", { name: "Continue to Missions" }).waitFor();
  await page.getByRole("link", { name: "Continue to Missions" }).click();
  await page.getByRole("heading", { name: "Missions" }).waitFor();
  await page.getByRole("link", { name: "New mission", exact: true }).click();
  await page.getByRole("heading", { name: "New mission" }).waitFor();
  await page.getByLabel("Requirement").fill("Verify the Developer Beta control plane Golden Path");
  await page.getByLabel("Repository reference ID").fill("local/p1-product-contract");
  await page.getByRole("button", { name: "Create mission" }).click();
  await page.getByRole("heading", { name: "Verify the Developer Beta control plane Golden Path" }).waitFor();
  await page.getByRole("button", { name: "Start planning" }).first().click();
  await page.getByRole("button", { name: "Attach plan" }).click();
  const submitPlan = page.getByRole("button", { name: "Submit plan" });
  if (await submitPlan.count()) await submitPlan.click();
  await page.getByRole("button", { name: "Approve exact plan subject" }).click();

  const missionId = new URL(page.url()).hash.split("/").pop();
  assert(missionId, "mission ID was not present in the detail route");
  let current = await (await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}`, { headers: apiHeaders })).json();
  for (let attempt = 0; attempt < 20 && current.current_state !== "running"; attempt += 1) {
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 100));
    current = await (await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}`, { headers: apiHeaders })).json();
  }
  assert(current.current_state === "running", `plan approval did not reach running state: ${current.current_state}`);
  for (const gate of current.required_verification ?? []) {
    const timestamp = new Date().toISOString();
    const evidence = { evidence_id: `fixture-${gate}-${randomUUID()}`, evidence_type: fixtureTypes[gate] || "command", source: "test_fixture", operation: `fixture verification ${gate}`, started_at: timestamp, finished_at: timestamp, exit_status: 0, bounded_output_summary: `Bounded test fixture evidence for ${gate}.`, producing_agent: "p1-e2e-actor", requirement_links: [current.requirement], task_links: current.execution_plan?.tasks.map((task) => task.task_id) ?? [], plan_revision: current.plan_revision ?? 1, verification_status: "passed" };
    const evidenceResponse = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/test-fixture/evidence`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ evidence, expected_revision: current.revision }) });
    const evidenceBody = await evidenceResponse.text();
    assert(evidenceResponse.ok, `fixture evidence failed for ${gate}: ${evidenceResponse.status} ${evidenceBody}`);
    current = JSON.parse(evidenceBody);
    const evidenceId = current.evidence_records.at(-1).evidence_id;
    const verificationResponse = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/verification-gates`, { method: "PUT", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ gate: { gate, status: "passed", evidence_refs: [evidenceId] }, expected_revision: current.revision }) });
    assert(verificationResponse.ok, `verification failed for ${gate}: ${verificationResponse.status}`);
    current = await verificationResponse.json();
  }
  for (const event of ["begin_verification", "complete_verification"]) {
    const response = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/transitions`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ event, idempotency_key: `e2e-${event}-${randomUUID()}`, expected_revision: current.revision }) });
    assert(response.ok, `${event} failed: ${response.status}`);
    current = (await response.json()).mission;
  }
  await page.goto(`http://127.0.0.1:${viewerPort}/#/system`, { waitUntil: "networkidle" });
  await page.getByLabel("Browser session credential").fill(credential);
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByRole("link", { name: "Continue to Missions" }).waitFor();
  await page.goto(`http://127.0.0.1:${viewerPort}/#/missions/${missionId}`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Verify the Developer Beta control plane Golden Path" }).waitFor();
  await page.goto(`http://127.0.0.1:${viewerPort}/#/review/${missionId}`, { waitUntil: "networkidle" });
  await page.getByText("Evidence-backed review").waitFor();
  await page.getByRole("heading", { name: "Evidence records" }).waitFor();
  assert((await page.locator("body").textContent()).includes("All linked evidence records are present and passed."), "Review did not expose linked passed evidence");
  await page.goto(`http://127.0.0.1:${viewerPort}/#/system`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Clear session" }).click();
  await page.reload({ waitUntil: "networkidle" });
  assert(await page.getByLabel("Browser session credential").count() === 1, "cleared session did not return to credential entry");
  assert(await page.getByRole("link", { name: "Continue to Missions" }).count() === 0, "cleared session remained authenticated after reload");

  const unauthorized = await fetch(`http://127.0.0.1:${apiPort}/v1/system/capabilities`);
  assert(unauthorized.status === 401, `unauthenticated system check returned ${unauthorized.status}`);
  const ownership = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}`, { headers: { authorization: `Bearer ${makeJwt("p1-other-actor")}` } });
  assert(ownership.status === 404, `cross-owner mission read returned ${ownership.status}`);
  const fixtureEnabled = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/test-fixture/evidence`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ evidence: { evidence_id: `enabled-${randomUUID()}`, evidence_type: "command", source: "test_fixture", operation: "enabled fixture probe", started_at: new Date().toISOString(), finished_at: new Date().toISOString(), producing_agent: "p1-e2e-actor", verification_status: "pending" }, expected_revision: current.revision }) });
  assert(fixtureEnabled.status === 200, `enabled fixture was not available in the E2E process: ${fixtureEnabled.status}`);
  await context.close();
  console.log(JSON.stringify({ authenticatedGoldenPath: "passed", unauthorized: 401, ownershipIsolation: 404, fixtureProvenance: "test_fixture", browserCredentialCleared: true, tauri: "unavailable" }));
} finally {
  if (browser) await browser.close();
  if (viewerServer) await new Promise((resolveClose) => viewerServer.close(resolveClose));
  if (apiProcess && !apiProcess.killed) apiProcess.kill();
  rmSync(workspace, { recursive: true, force: true });
}
