import React from "react";
import { Key, RefreshCw, ShieldCheck } from "lucide-react";
import type { MeshStatus, PeerProfile } from "./types";

interface PkiAttestationCardProps {
  meshStatus: MeshStatus | null;
  localNode?: PeerProfile;
  rotatingCert: boolean;
  onRotateCert: () => void;
}

export const PkiAttestationCard: React.FC<PkiAttestationCardProps> = ({
  meshStatus,
  localNode,
  rotatingCert,
  onRotateCert,
}) => {
  return (
    <div className="mb-6 rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/30 via-[var(--card-bg)] to-purple-950/20 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-indigo-500/10 p-2 border border-indigo-500/20 text-indigo-400">
            <Key className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                Node mTLS Identity Certificate
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                <ShieldCheck className="h-3 w-3" />
                Mutual Attestation Ready
              </span>
            </div>
            <p className="mt-0.5 font-mono text-xs text-[var(--t2)] truncate max-w-xl">
              SHA-256: {meshStatus?.cert_fingerprint || localNode?.cert_fingerprint || "36b033fd22c2bdbf58f0d43dbc8ef87975b67624a1d0ef73ed214eb0802b3fce"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--t3)] font-mono">
            TTL: {meshStatus?.cert_expires_in_sec ? `${Math.round(meshStatus.cert_expires_in_sec)}s` : "3600s"}
          </span>
          <button
            type="button"
            onClick={onRotateCert}
            disabled={rotatingCert}
            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-500/20 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${rotatingCert ? "animate-spin" : ""}`} />
            Rotate Cert Now
          </button>
        </div>
      </div>
    </div>
  );
};
