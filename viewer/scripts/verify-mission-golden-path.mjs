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

function startApi(portNumber, enableFixture) {
  return spawn(python, ["-m", "uvicorn", "agent_workspace.api:app", "--host", "127.0.0.1", "--port", String(portNumber)], {
    cwd: repo,
    stdio: "inherit",
    env: { ...process.env, OTEL_SDK_DISABLED: "true", AGENT_WORKSPACE_DIR: workspace, LAS_BOOTSTRAP_API_KEY: credential, LAS_JWT_SECRET: jwtSecret, LAS_BOOTSTRAP_TENANT_ID: "p1-e2e-tenant", LAS_BOOTSTRAP_SUBJECT: "p1-e2e-actor", LAS_BOOTSTRAP_ROLE: "tenant", LAS_ENABLE_REDIS_SWARM: "false", LAS_ENABLE_AUDIT_CONSENSUS: "false", LAS_ENABLE_STRIPE: "false", LAS_ENABLE_MISSION_TEST_FIXTURE: enableFixture ? "true" : "false" },
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
let disabledFixtureApiProcess;
let browser;
try {
  apiProcess = startApi(apiPort, true);
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
  assert((current.required_verification ?? []).includes("requirement"), "requirement gate was not required");
  await page.getByRole("heading", { name: "Record bounded evidence" }).waitFor();
  await page.getByLabel("Gate").selectOption("requirement");
  await page.getByLabel("Evidence type").selectOption("test");
  await page.getByLabel("Source").fill("golden-path-production");
  await page.getByLabel("Operation").fill("production evidence form submission");
  await page.getByLabel("Verification status").selectOption("passed");
  await page.getByLabel("Bounded output summary").fill("Production Viewer evidence form submitted a bounded passed record.");
  await page.getByLabel("Exit status (optional)").fill("0");
  const productionEvidenceResponse = page.waitForResponse((response) => response.url().endsWith(`/v1/missions/${missionId}/evidence`) && response.request().method() === "POST" && response.status() === 200);
  const productionVerificationResponse = page.waitForResponse((response) => response.url().endsWith(`/v1/missions/${missionId}/verification-gates`) && response.request().method() === "PUT" && response.status() === 200);
  await page.getByRole("button", { name: "Record bounded evidence", exact: true }).click();
  const [productionEvidence, productionVerification] = await Promise.all([productionEvidenceResponse, productionVerificationResponse]);
  assert(productionEvidence.ok && productionVerification.ok, "production evidence form did not complete both writes");
  current = await productionVerification.json();
  const productionRecord = current.evidence_records.find((record) => record.source === "golden-path-production");
  assert(productionRecord && productionRecord.source !== "test_fixture", "production evidence provenance was invalid");
  const productionGate = current.verification_gates.find((gate) => gate.gate === "requirement");
  assert(productionGate?.status === "passed" && productionGate.evidence_refs.includes(productionRecord.evidence_id), "production evidence was not linked to the requirement gate");
  for (const gate of (current.required_verification ?? []).filter((requiredGate) => requiredGate !== "requirement")) {
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
  const staleRevision = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/transitions`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ event: "close", idempotency_key: `e2e-stale-${randomUUID()}`, expected_revision: Math.max(0, current.revision - 1) }) });
  assert(staleRevision.status === 409, `stale revision did not return 409: ${staleRevision.status}`);
  assert((await staleRevision.json()).code === "stale_revision", "stale revision returned the wrong error code");
  const planApproval = current.approval_gates?.find((gate) => gate.gate_type === "plan");
  assert(planApproval, "plan approval gate was not retained");
  const immutableApproval = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/approvals`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ gate_id: `conflicting-plan-${randomUUID()}`, gate_type: "plan", subject: planApproval.subject, status: "rejected", evidence_refs: [], idempotency_key: `e2e-immutable-${randomUUID()}`, expected_revision: current.revision }) });
  assert(immutableApproval.status === 409, `immutable approval did not return 409: ${immutableApproval.status}`);
  assert((await immutableApproval.json()).code === "immutable_decision_conflict", "immutable approval returned the wrong error code");
  const missingEvidenceVerification = await fetch(`http://127.0.0.1:${apiPort}/v1/missions/${missionId}/verification-gates`, { method: "PUT", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ gate: { gate: current.required_verification[0], status: "passed", evidence_refs: [`missing-${randomUUID()}`] }, expected_revision: current.revision }) });
  assert(missingEvidenceVerification.status === 422, `nonexistent verification ref was accepted: ${missingEvidenceVerification.status}`);
  const disabledFixturePort = apiPort + 2;
  disabledFixtureApiProcess = startApi(disabledFixturePort, false);
  await waitFor(`http://127.0.0.1:${disabledFixturePort}/v1/system/capabilities`, apiHeaders);
  const fixtureDisabled = await fetch(`http://127.0.0.1:${disabledFixturePort}/v1/missions/${missionId}/test-fixture/evidence`, { method: "POST", headers: { ...apiHeaders, "content-type": "application/json" }, body: JSON.stringify({ evidence: { evidence_id: `disabled-${randomUUID()}`, evidence_type: "command", source: "test_fixture", operation: "disabled fixture probe", started_at: new Date().toISOString(), finished_at: new Date().toISOString(), producing_agent: "p1-e2e-actor", verification_status: "pending" }, expected_revision: current.revision }) });
  assert(fixtureDisabled.status === 404, `disabled fixture endpoint returned ${fixtureDisabled.status}`);
  disabledFixtureApiProcess.kill();
  disabledFixtureApiProcess = undefined;
  await page.goto(`http://127.0.0.1:${viewerPort}/#/system`, { waitUntil: "networkidle" });
  await page.getByLabel("Browser session credential").fill(credential);
  await page.getByRole("button", { name: "Check session" }).click();
  await page.getByRole("link", { name: "Continue to Missions" }).waitFor();
  await page.goto(`http://127.0.0.1:${viewerPort}/#/missions/${missionId}`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Verify the Developer Beta control plane Golden Path" }).waitFor();
  await page.goto(`http://127.0.0.1:${viewerPort}/#/review/${missionId}`, { waitUntil: "networkidle" });
  await page.getByText("Evidence-backed review").waitFor();
  await page.getByRole("heading", { name: "Evidence records" }).waitFor();
  const reviewText = await page.locator("body").textContent();
  assert(reviewText.includes("All linked evidence records are present, passed, and type-compatible."), "Review did not expose linked passed evidence");
  assert(reviewText.includes("Evidence ID:") && reviewText.includes("Started:") && reviewText.includes("Bounded output summary:"), "Review did not expose complete gate-level evidence metadata");
  assert(reviewText.includes("golden-path-production"), "Review did not expose production evidence source metadata");
  assert(reviewText.includes("test_fixture"), "Review did not retain fixture evidence metadata for remaining gates");
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
  console.log(JSON.stringify({ authenticatedGoldenPath: "passed", productionEvidenceSource: "golden-path-production", unauthorized: 401, ownershipIsolation: 404, staleRevision: 409, immutableApproval: 409, nonexistentVerificationRef: 422, fixtureDisabled: 404, fixtureProvenance: "test_fixture", reviewMetadata: "complete", browserCredentialCleared: true, tauri: "unavailable" }));
} finally {
  if (browser) await browser.close();
  if (viewerServer) await new Promise((resolveClose) => viewerServer.close(resolveClose));
  if (disabledFixtureApiProcess && !disabledFixtureApiProcess.killed) disabledFixtureApiProcess.kill();
  if (apiProcess && !apiProcess.killed) apiProcess.kill();
  rmSync(workspace, { recursive: true, force: true });
}
