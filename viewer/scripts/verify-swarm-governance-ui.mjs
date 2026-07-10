import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const viewerRoot = fileURLToPath(new URL("..", import.meta.url));
const componentPath = resolve(viewerRoot, "src", "components", "SwarmGovernanceConsole.tsx");
const componentSource = readFileSync(componentPath, "utf8");
const calibrationPath = resolve(viewerRoot, "src", "components", "PromptCalibrationDashboard.tsx");
const calibrationSource = readFileSync(calibrationPath, "utf8");

const requiredExports = [
  "SwarmNodeMonitor",
  "SessionFailoverDashboard",
  "P2PMeshNetworkMap",
  "MTLSTunnelingStatusPanel",
  "BillingPolicyControls",
  "CryptographicProofInspector",
  "ReplayPlaybackWidget",
];

const requiredEndpoints = [
  "/v1/swarm/nodes",
  "/v1/swarm/scale",
  "/v1/swarm/health",
  "/v1/swarm/sessions",
  "/v1/swarm/sessions/resume",
  "/v1/swarm/peers",
  "/v1/swarm/billing/status",
  "/v1/swarm/billing/policy",
  "/v1/swarm/telemetry/ws",
  "/v1/swarm/replays/",
  "/v1/cross-cloud/cert/status",
  "/v1/cross-cloud/cert/rotate",
  "/v1/cross-cloud/revoke",
  "/v1/cross-cloud/revoked",
  "/v1/cross-cloud/reinstate",
  "/v1/audit/proof/",
  "/v1/audit/verify-proof",
];

const requiredCalibrationEndpoints = [
  "/v1/swarm/governance/rules",
  "/v1/swarm/governance/vote",
];

const offlineRenderMarkers = [
  "data-testid=\"swarm-node-monitor\"",
  "data-testid=\"session-failover-dashboard\"",
  "data-testid=\"p2p-mesh-network-map\"",
  "data-testid=\"mtls-tunneling-status-panel\"",
  "data-testid=\"billing-policy-controls\"",
  "data-testid=\"cryptographic-proof-inspector\"",
  "local-ceo-01",
  "recovery-ops-184",
  "peer-tpe-01",
  "fallback-sibling-left",
  "fallback-cert-sha-256",
  "Revoked Certificates Ledger",
  "revoked-fallback-sha-256",
  "Force Rotate Keys",
  "Metered Token Usage (Real-time)",
  "credits-ring-gradient",
  "Revoke",
  "strict_limit",
  "auto_downscale",
];

function assertIncludes(source, token, label) {
  if (!source.includes(token)) {
    throw new Error(`${label} missing: ${token}`);
  }
}

for (const exportName of requiredExports) {
  assertIncludes(componentSource, `export function ${exportName}`, "component export");
}

for (const endpoint of requiredEndpoints) {
  assertIncludes(componentSource, endpoint, "API endpoint");
}

for (const endpoint of requiredCalibrationEndpoints) {
  assertIncludes(calibrationSource, endpoint, "calibration API endpoint");
}

for (const token of ["generateMemberSignature", "payload_hash", "VALIDATOR_ROLES"]) {
  assertIncludes(calibrationSource, token, "cryptographic vote binding");
}

for (const token of ["billing_tier", "credits_remaining", "billing_status", "apiCostUsd", "setMeteredUsage"]) {
  assertIncludes(componentSource, token, "billing telemetry binding");
}

for (const marker of offlineRenderMarkers) {
  assertIncludes(componentSource, marker, "offline render marker");
}

const distAssets = resolve(viewerRoot, "dist", "assets");
if (existsSync(distAssets)) {
  const adminChunk = readdirSync(distAssets).find((name) => name.startsWith("AdminDashboardView-") && name.endsWith(".js"));
  if (!adminChunk) {
    throw new Error("AdminDashboardView production chunk missing. Run `npm run build` first.");
  }
  const chunkSource = readFileSync(join(distAssets, adminChunk), "utf8");
  for (const marker of ["swarm-node-monitor", "mtls-tunneling-status-panel", "local-ceo-01", "peer-tpe-01", "strict_limit", "fallback-sibling-left", "fallback-cert-sha-256", "Revoked Certificates Ledger", "Metered Token Usage"]) {
    assertIncludes(chunkSource, marker, "production offline render marker");
  }
}

console.log("swarm governance UI mock-service verification passed");
