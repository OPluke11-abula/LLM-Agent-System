#!/usr/bin/env python3
"""
LAS Multi-Worker Cluster Demonstration CLI Runner (Phase 91).
Executes the reproducible 3-node federated mesh demo under Zero-Trust mTLS,
Raft consensus, Chaos network partition, and Autonomous Self-Healing.
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agent_workspace.core.cluster_demo import MultiWorkerCluster


def main():
    print("=" * 80)
    print(" [*] LAS Multi-Worker Cluster Demonstration (Phase 91)")
    print("     - Zero-Trust mTLS Dynamic Node Attestation")
    print("     - Replicated Raft Committee Quorum Consensus")
    print("     - Federated Vector Memory & Merkle Convergence")
    print("     - Chaos Network Partition & Leader Failover")
    print("     - Autonomous Self-Healing Loop & Auto-Rollback Engine")
    print("=" * 80)

    cluster = MultiWorkerCluster()
    try:
        receipt = cluster.run_full_demo()

        print("\n" + "=" * 80)
        print(f" [OK] Cluster Demonstration Summary (Demo ID: {receipt.demo_id})")
        print("=" * 80)
        print(f" Participating Nodes : {', '.join(receipt.nodes_participating)}")
        print(f" Total Duration      : {receipt.duration_total_ms} ms")
        print(f" Steps Passed        : {receipt.passed_steps} / {receipt.total_steps}")
        print(f" Overall Status      : {'PASS' if receipt.success else 'FAIL'}")
        print("-" * 80)
        print(f"{'Step Name':<55} | {'Status':<8} | {'Duration':<10}")
        print("-" * 80)
        for s in receipt.step_receipts:
            print(f"{s.step_name:<55} | {s.status:<8} | {s.duration_ms:>6.2f} ms")
        print("=" * 80)

        evidence_dir = repo_root / ".agent" / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        receipt_file = evidence_dir / "cluster_demo_receipt.json"
        receipt_file.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nSaved cluster demonstration receipt to:\n  {receipt_file}\n")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Error executing cluster demonstration: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
