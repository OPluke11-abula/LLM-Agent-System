import React from "react";
import { Brain, Database, RefreshCw, Search } from "lucide-react";
import type {
  VectorMemoryEntryItem,
  VectorMemoryStats,
  VectorQueryResultItem,
} from "./types";

interface VectorMemoryCardProps {
  vectorStats: VectorMemoryStats | null;
  vectorEntries: VectorMemoryEntryItem[];
  queryInput: string;
  setQueryInput: (val: string) => void;
  searching: boolean;
  searchResults: VectorQueryResultItem[];
  onSearch: () => void;
}

export const VectorMemoryCard: React.FC<VectorMemoryCardProps> = ({
  vectorStats,
  vectorEntries,
  queryInput,
  setQueryInput,
  searching,
  searchResults,
  onSearch,
}) => {
  return (
    <div className="mb-6 rounded-xl border border-purple-500/30 bg-gradient-to-r from-purple-950/20 via-[var(--card-bg)] to-indigo-950/20 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-c)] pb-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-purple-500/10 p-2 border border-purple-500/20 text-purple-400">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-300">
                Federated Vector Memory & RAG Knowledge Topology
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 px-2 py-0.5 text-[10px] font-semibold text-purple-300">
                <Brain className="h-3 w-3" />
                {vectorStats?.total_entries || 0} Vectors Indexed
              </span>
            </div>
            <p className="mt-0.5 text-xs text-[var(--t2)]">
              Decentralized cosine similarity retrieval with deterministic Merkle root integrity & Raft experience replication
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="rounded-lg border border-[var(--border-c)] bg-white/5 px-2.5 py-1 text-right">
            <span className="text-[10px] uppercase text-[var(--t3)] block">Merkle Topology Root</span>
            <span className="font-mono text-xs text-purple-300 font-semibold" title={vectorStats?.merkle_root || "None"}>
              {vectorStats?.merkle_root ? `${vectorStats.merkle_root.slice(0, 12)}...` : "Empty"}
            </span>
          </div>
        </div>
      </div>

      {/* Interactive Query Search Bar */}
      <div className="mb-4 flex flex-col md:flex-row gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--t3)]" />
          <input
            type="text"
            aria-label="Query federated experiences"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearch()}
            placeholder="Query federated experiences (e.g. modular architecture, security sanitization, consensus rules)..."
            className="w-full rounded-lg border border-[var(--border-c)] bg-[var(--input-bg)] py-2 pl-9 pr-3 text-xs text-[var(--t1)] placeholder:text-[var(--t3)] focus:border-purple-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={onSearch}
          disabled={searching}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-500/10 px-4 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${searching ? "animate-spin" : ""}`} />
          Cosine Search
        </button>
      </div>

      {/* Search Results Grid */}
      {searchResults.length > 0 && (
        <div className="mb-4 rounded-lg border border-purple-500/20 bg-black/20 p-3">
          <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-purple-300">
            Ranked Semantic Matches ({searchResults.length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {searchResults.map((res) => (
              <div key={res.entry_id} className="rounded-md border border-[var(--border-c)] bg-[var(--card-bg)]/80 p-2.5">
                <div className="flex items-center justify-between mb-1">
                  <span className="inline-flex items-center gap-1 rounded bg-purple-500/20 px-1.5 py-0.5 text-[10px] font-bold text-purple-300">
                    #{res.rank} {res.category}
                  </span>
                  <span className="font-mono text-[10px] text-emerald-400 font-semibold">
                    Sim: {(res.similarity * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-xs text-[var(--t1)] line-clamp-2 leading-relaxed">
                  {res.content}
                </p>
                <div className="mt-2 flex items-center justify-between text-[10px] text-[var(--t3)] font-mono">
                  <span>Task: {res.task_id}</span>
                  <span>Node: {res.author_node_id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Synchronized Replicated Experience Ledger Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[var(--border-c)] text-[var(--t3)] uppercase tracking-wider text-[10px]">
              <th className="pb-2 font-mono">ID</th>
              <th className="pb-2">Category</th>
              <th className="pb-2 font-mono">Task</th>
              <th className="pb-2 font-mono">Author</th>
              <th className="pb-2">Synchronized Experience Summary</th>
              <th className="pb-2 text-right font-mono">Merkle Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-c)] font-mono text-[11px]">
            {vectorEntries.slice(0, 5).map((e) => (
              <tr key={e.entry_id} className="hover:bg-white/5 transition-colors">
                <td className="py-2 text-purple-300 font-bold">{e.entry_id}</td>
                <td className="py-2 font-sans">
                  <span className="inline-flex items-center gap-1 rounded bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-[var(--t2)]">
                    {e.category}
                  </span>
                </td>
                <td className="py-2 text-[var(--t2)]">{e.task_id}</td>
                <td className="py-2 text-[var(--t3)]">{e.author_node_id}</td>
                <td className="py-2 font-sans text-[var(--t1)] text-xs truncate max-w-sm" title={e.content}>
                  {e.content}
                </td>
                <td className="py-2 text-right text-[var(--t3)] font-mono text-[10px]" title={e.content_hash}>
                  {e.content_hash ? `${e.content_hash.slice(0, 8)}...` : "none"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
