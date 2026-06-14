import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

const componentPath = resolve("src", "components", "SwarmGovernanceConsole.tsx");
const componentSource = readFileSync(componentPath, "utf8");

const requiredExports = [
  "SwarmNodeMonitor",
  "SessionFailoverDashboard",
  "P2PMeshNetworkMap",
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
  "/v1/swarm/replays/",
  "/v1/audit/proof/",
  "/v1/audit/verify-proof",
];

const offlineRenderMarkers = [
  "data-testid=\"swarm-node-monitor\"",
  "data-testid=\"session-failover-dashboard\"",
  "data-testid=\"p2p-mesh-network-map\"",
  "data-testid=\"billing-policy-controls\"",
  "data-testid=\"cryptographic-proof-inspector\"",
  "local-ceo-01",
  "recovery-ops-184",
  "peer-tpe-01",
  "fallback-sibling-left",
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

for (const marker of offlineRenderMarkers) {
  assertIncludes(componentSource, marker, "offline render marker");
}

const distAssets = resolve("dist", "assets");
if (existsSync(distAssets)) {
  const adminChunk = readdirSync(distAssets).find((name) => name.startsWith("AdminDashboardView-") && name.endsWith(".js"));
  if (!adminChunk) {
    throw new Error("AdminDashboardView production chunk missing. Run `npm run build` first.");
  }
  const chunkSource = readFileSync(join(distAssets, adminChunk), "utf8");
  for (const marker of ["swarm-node-monitor", "local-ceo-01", "peer-tpe-01", "strict_limit", "fallback-sibling-left"]) {
    assertIncludes(chunkSource, marker, "production offline render marker");
  }
}

console.log("swarm governance UI mock-service verification passed");
