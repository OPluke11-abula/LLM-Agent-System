import React from "react";
import { Network } from "lucide-react";

interface JoinPeerModalProps {
  isOpen: boolean;
  onClose: () => void;
  seedAddress: string;
  setSeedAddress: (addr: string) => void;
  joining: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

export const JoinPeerModal: React.FC<JoinPeerModalProps> = ({
  isOpen,
  onClose,
  seedAddress,
  setSeedAddress,
  joining,
  onSubmit,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--border-c)] bg-[#131722] p-6 shadow-2xl">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Network className="h-5 w-5 text-cyan-400" />
          Join P2P Mesh Seed Node
        </h3>
        <p className="mt-1 text-xs text-[var(--t3)]">
          Enter the host and port of an existing LAS cluster node to establish encrypted ECDH peering.
        </p>

        <form onSubmit={onSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor="seed-node-address" className="block text-xs font-semibold uppercase tracking-wider text-[var(--t2)] mb-1">
              Seed Node Address (host:port)
            </label>
            <input
              id="seed-node-address"
              type="text"
              aria-label="Seed Node Address (host:port)"
              value={seedAddress}
              onChange={(e) => setSeedAddress(e.target.value)}
              placeholder="e.g. 192.168.1.120:8000"
              className="w-full rounded-lg border border-[var(--border-c)] bg-[var(--bg)] px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={joining}
              className="rounded-lg border border-[var(--border-c)] px-4 py-2 text-xs font-medium text-[var(--t2)] hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={joining}
              className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50"
            >
              {joining ? "Connecting..." : "Connect & Peer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
