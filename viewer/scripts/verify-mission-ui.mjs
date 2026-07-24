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
const missionFixturePort = port + 5;
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
const fixtureMission = {
  mission_id: "ui-fixture-running",
  requirement: "UI verifier Running Mission",
  repository_id: "fixture/repository",
  current_state: "running",
  revision: 0,
  execution_policy: { preset: "balanced", scope: { allowed_paths: [], protected_paths: [], draft_pr_permission: false } },
  required_verification: ["requirement"],
  verification_gates: [{ gate: "requirement", status: "not_applicable", evidence_refs: [] }],
  evidence_records: [],
  transition_audit: [],
  usage_summary: { provider_calls: 0, retries: 0, healing_calls: 0, input_tokens: 0, output_tokens: 0, currency: "USD", accounting_revision: 0 },
};
const fixtureMissionNaEvidence = {
  ...fixtureMission,
  mission_id: "ui-fixture-na-explanatory",
  current_state: "review_ready",
  verification_gates: [{ gate: "requirement", status: "not_applicable", evidence_refs: ["na-explanation"] }],
  evidence_records: [{ evidence_id: "na-explanation", evidence_type: "security", source: "manual-review", operation: "documented non-applicability", started_at: "2026-01-01T00:00:00Z", finished_at: "2026-01-01T00:00:00Z", bounded_output_summary: "Requirement is outside this mission's bounded scope.", producing_agent: "reviewer", verification_status: "pending" }],
};
const fixtureMissionIncompatiblePassed = {
  ...fixtureMission,
  mission_id: "ui-fixture-incompatible-passed",
  current_state: "review_ready",
  verification_gates: [{ gate: "requirement", status: "passed", evidence_refs: ["incompatible-passed"] }],
  evidence_records: [{ evidence_id: "incompatible-passed", evidence_type: "security", source: "manual-review", operation: "incompatible passed evidence", started_at: "2026-01-01T00:00:00Z", finished_at: "2026-01-01T00:00:00Z", exit_status: 0, bounded_output_summary: "Passed evidence with the wrong type.", producing_agent: "reviewer", verification_status: "passed" }],
};
const fixtureMissions = new Map([
  [fixtureMission.mission_id, fixtureMission],
  [fixtureMissionNaEvidence.mission_id, fixtureMissionNaEvidence],
  [fixtureMissionIncompatiblePassed.mission_id, fixtureMissionIncompatiblePassed],
]);
const fixtureCapabilities = {
  mission_id: fixtureMission.mission_id,
  revision: 0,
  current_state: "running",
  allowed_events: [],
  plan_approval_required: false,
  verification_incomplete: false,
  draft_pr_permission_disabled: false,
};
let productionEvidenceRequests = 0;
const fixtureSystemCapabilities = {
  api_reachable: true,
  authentication_valid: true,
  workspace_root_available: true,
  mission_store_available: true,
  contract_schema_version: "1.0",
  provider_configuration: "not_configured",
  git_integration: "not_implemented",
  github_integration: "not_implemented",
  repository_inspection: "not_implemented",
  agent_execution: "not_implemented",
  draft_pr_delivery: "not_implemented",
};
const missionFixtureServer = createServer((request, response) => {
  const headers = { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type,x-api-key", "Access-Control-Allow-Methods": "GET,OPTIONS" };
  if (request.method === "OPTIONS") { response.writeHead(204, headers); response.end(); return; }
  const pathname = new URL(request.url || "/", `http://127.0.0.1:${missionFixturePort}`).pathname;
  if (request.method === "POST" || request.method === "PUT") {
    if (pathname.endsWith("/evidence") || pathname.endsWith("/verification-gates")) productionEvidenceRequests += 1;
    response.writeHead(500, headers);
    response.end(JSON.stringify({ code: "unexpected_network_request" }));
    return;
  }
  const missionId = pathname.match(/^\/v1\/missions\/([^/]+)/)?.[1];
  const body = pathname === "/v1/system/capabilities" ? fixtureSystemCapabilities
    : pathname === "/v1/missions" ? { items: [...fixtureMissions.values()], limit: 50, offset: 0, next_offset: null }
      : missionId && fixtureMissions.has(missionId) && pathname.endsWith("/capabilities") ? fixtureCapabilities
        : missionId && fixtureMissions.has(missionId) && pathname.endsWith("/transitions") ? { items: [], limit: 50, offset: 0, next_offset: null }
          : missionId ? fixtureMissions.get(missionId)
            : undefined;
  if (body === undefined) { response.writeHead(404, headers); response.end(JSON.stringify({ code: "mission_not_found", message: "Mission does not exist" })); return; }
  response.writeHead(200, headers);
  response.end(JSON.stringify(body));
});
const listen = (instance, portNumber) => new Promise((resolveListen) => instance.listen(portNumber, "127.0.0.1", resolveListen));
const close = (instance) => new Promise((resolveClose) => instance.close(resolveClose));

await Promise.all([listen(server, port), listen(mismatchServer, mismatchPort), listen(storeUnavailableServer, storeUnavailablePort), listen(slowServer, slowPort), listen(missionFixtureServer, missionFixturePort)]);
const browser = await chromium.launch({ headless: true });
try {
  const browserContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await browserContext.newPage();
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "System Check" }).waitFor();
  if (await page.getByLabel("Browser session credential").count() !== 1) throw new Error("first-run credential field is missing");
  const browserSecrets = await page.evaluate(() => ({ global: "__LAS_BROWSER_SESSION_CREDENTIAL__" in window, storage: `${localStorage} ${sessionStorage}`.includes("LAS_BROWSER_SESSION_CREDENTIAL") }));
  if (browserSecrets.global || browserSecrets.storage) throw new Error(`browser credential boundary failed ${JSON.stringify(browserSecrets)}`);
  if (takeScreenshots) await page.screenshot({ path: join(outputRoot, "system-first-run.png"), fullPage: true });
  console.log(`system-first-run ${JSON.stringify(browserSecrets)}`);
  await browserContext.close();

  const fixtureContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await fixtureContext.addInitScript((baseUrl) => { window.__LAS_API_BASE_URL__ = baseUrl; }, `http://127.0.0.1:${missionFixturePort}`);
  const fixturePage = await fixtureContext.newPage();
  await fixturePage.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  await fixturePage.getByLabel("Browser session credential").fill("ui-fixture-test");
  await fixturePage.getByRole("button", { name: "Check session" }).click();
  await fixturePage.getByRole("link", { name: "Continue to Missions" }).click();
  await fixturePage.goto(`http://127.0.0.1:${port}/#/missions/${fixtureMission.mission_id}`, { waitUntil: "networkidle" });
  await fixturePage.getByRole("heading", { name: "Record bounded evidence" }).waitFor();
  const fixtureText = await fixturePage.locator("body").innerText();
  const removedHeading = ["Record", "deterministic", "evidence", "+ gates"].join(" ");
  if (fixtureText.includes(removedHeading)) throw new Error("production Running Mission still exposes the removed evidence heading");
  const requiredLabels = ["Gate", "Evidence type", "Source", "Operation", "Verification status", "Bounded output summary", "Artifact ref (optional)", "Exit status (optional)"];
  for (const label of requiredLabels) {
    const control = fixturePage.getByLabel(label);
    if (await control.count() !== 1 || !(await control.isVisible())) throw new Error(`production evidence control is not accessible: ${label}`);
    if (await control.evaluate((element) => element instanceof HTMLElement && element.tabIndex < 0)) throw new Error(`production evidence control is not keyboard accessible: ${label}`);
  }
  const submitEvidence = fixturePage.getByRole("button", { name: "Record bounded evidence", exact: true });
  if (await submitEvidence.count() !== 1 || !(await submitEvidence.isVisible())) throw new Error("production evidence submission control is not accessible");
  if (await submitEvidence.evaluate((element) => element instanceof HTMLElement && element.tabIndex < 0)) throw new Error("production evidence submission control is not keyboard accessible");
  await fixturePage.getByLabel("Source").fill("test_fixture");
  await fixturePage.getByLabel("Operation").fill("reserved provenance validation");
  await fixturePage.getByLabel("Bounded output summary").fill("The production form must reject fixture provenance.");
  await submitEvidence.click();
  await fixturePage.getByText("test_fixture provenance is reserved for the test-fixture endpoint.", { exact: true }).waitFor();
  if (productionEvidenceRequests !== 0) throw new Error("reserved fixture provenance issued a production network request");
  console.log("production-form-provenance blocked");
  await fixturePage.goto(`http://127.0.0.1:${port}/#/review/${fixtureMission.mission_id}`, { waitUntil: "networkidle" });
  await fixturePage.getByText("Evidence-backed review").waitFor();
  if (await fixturePage.getByText("not applicable", { exact: true }).count() === 0) throw new Error("Review did not display not applicable distinctly");
  if ((await fixturePage.locator("body").innerText()).includes("Residual uncertainty")) throw new Error("not applicable gate appeared unresolved in Review");
  await fixturePage.goto(`http://127.0.0.1:${port}/#/review/${fixtureMissionNaEvidence.mission_id}`, { waitUntil: "networkidle" });
  await fixturePage.getByText("Evidence-backed review").waitFor();
  await fixturePage.getByText("na-explanation", { exact: true }).click();
  const explanatoryText = await fixturePage.locator("body").innerText();
  if (!explanatoryText.includes("manual-review") || explanatoryText.includes("Evidence type is incompatible with this gate") || explanatoryText.includes("Residual uncertainty")) throw new Error("N/A explanatory evidence was rendered with an incorrect warning or unresolved state");
  await fixturePage.goto(`http://127.0.0.1:${port}/#/review/${fixtureMissionIncompatiblePassed.mission_id}`, { waitUntil: "networkidle" });
  await fixturePage.getByText("Evidence-backed review").waitFor();
  await fixturePage.getByText("requirement", { exact: true }).click();
  const incompatibleText = await fixturePage.locator("body").innerText();
  if (!incompatibleText.includes("Evidence type is incompatible with this gate") || !incompatibleText.includes("Residual uncertainty")) throw new Error("incompatible PASSED evidence was not rendered as unresolved");
  console.log("review-na-semantics passed");
  console.log("production-form-boundary passed");
  await fixtureContext.close();

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
  await Promise.all([close(server), close(mismatchServer), close(storeUnavailableServer), close(slowServer), close(missionFixtureServer)]);
}
