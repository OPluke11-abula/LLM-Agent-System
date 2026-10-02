import React from "react";
import { Brain, CheckCircle2, Cpu, Server, Shield } from "lucide-react";
import type { PeerProfile } from "./types";

interface LocalCapabilitiesBannerProps {
  localNode?: PeerProfile;
}

export const LocalCapabilitiesBanner: React.FC<LocalCapabilitiesBannerProps> = ({ localNode }) => {
  return (
    <div className="mb-6 rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
        <Cpu className="h-4 w-4" />
        Local Advertised Capabilities
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {localNode?.capabilities.map((cap) => (
          <span
            key={cap}
            className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300"
          >
            {cap === "REASONING_ENGINE" && <Brain className="h-3.5 w-3.5 text-purple-400" />}
            {cap === "TEST_RUNNER" && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
            {cap === "SANDBOX_MUTATION" && <Shield className="h-3.5 w-3.5 text-amber-400" />}
            {cap === "COCKPIT_LEADER" && <Server className="h-3.5 w-3.5 text-blue-400" />}
            {cap}
          </span>
        ))}
      </div>
    </div>
  );
};
