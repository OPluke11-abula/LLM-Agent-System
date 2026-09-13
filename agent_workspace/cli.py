"""Unified Operations Developer CLI toolbelt for FindAi Studio LLM Agent System (LAS)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

# Configure UTF-8 for cross-platform and Windows terminal output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add workspace directory and repository root to path
workspace = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(workspace)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if workspace not in sys.path:
    sys.path.insert(0, workspace)

from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter
from agent_workspace.core.workflow_engine import WorkflowEngine
from agent_workspace.long_term_memory import LongTermMemoryStore
from agent_workspace.pap_validate import validate as run_pap_validate

def handle_list_skills(args):
    """List all registered tools including local and global overrides."""
    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine, session_id="cli-session")
    skills = router.list_skills()

    if not skills:
        print("No registered skills found.")
        return

    print(f"{'Skill ID':<25} | {'Version':<8} | {'Description':<50}")
    print("-" * 90)
    for skill in skills:
        name = skill.get("id", "unknown")
        version = skill.get("version", "1.0.0")
        desc = skill.get("description", "").strip().splitlines()[0] if skill.get("description") else ""
        desc_trunc = desc[:50] + "..." if len(desc) > 50 else desc
        print(f"{name:<25} | {version:<8} | {desc_trunc:<50}")

def handle_describe_skill(args):
    """Describe the specified skill contract."""
    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine, session_id="cli-session")
    try:
        desc = router.describe_skill(args.describe_skill)
        print(yaml.safe_dump(desc, allow_unicode=True, sort_keys=False))
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

def handle_validate(args):
    """Run structural gate validation checks."""
    project_root = Path(workspace).parent
    try:
        run_pap_validate(project_root)
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)

def handle_memory_read(args):
    """Read a memory record by key."""
    memory_dir = args.memory_dir or os.path.join(workspace, "memory")
    store = LongTermMemoryStore(memory_dir, backend_name=args.backend)
    session = args.session or "global_session"

    record = store._backend.read(session, args.memory_read)
    if not record:
        # Search all records across all sessions if not found in target session
        for r in store.all_records():
            if r.get("id") == args.memory_read:
                record = r
                break

    if record:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(f"Memory record '{args.memory_read}' not found.", file=sys.stderr)
        sys.exit(1)

def handle_memory_write(args):
    """Write a custom memory record by key and value."""
    key = args.memory_write[0]
    value = args.memory_write[1]

    memory_dir = args.memory_dir or os.path.join(workspace, "memory")
    store = LongTermMemoryStore(memory_dir, backend_name=args.backend)
    session = args.session or "global_session"

    domain = "semantic" if key.startswith("sem-") else ("preference" if key.startswith("pref-") else "episodic")

    record = {
        "id": key,
        "session_id": session,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "cli_write",
        "source_hash": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "summary": value,
        "keywords": LongTermMemoryStore._keywords(value),
        "message_count": 0,
        "payload": {"text": value},
        "domain": domain,
        "confidence": 1.0,
        "privacy_level": "project"
    }

    store._backend.write(session, key, record)
    print(f"Successfully wrote memory record '{key}' under session '{session}'.")

def handle_run_workflow(args):
    """Run or resume an asynchronous workflow."""
    workflow_id = args.run_workflow
    session = args.session or f"wf-session-{workflow_id}"

    engine = AgentEngine(workspace_path=workspace)
    workflow_engine = WorkflowEngine(engine)

    print(f"Executing workflow '{workflow_id}' (Session ID: {session})...")
    try:
        results = asyncio.run(workflow_engine.execute(
            workflow_id=workflow_id,
            session_id=session,
            resume=args.resume
        ))
        print("Workflow executed successfully!")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Workflow execution failed: {e}", file=sys.stderr)
        sys.exit(1)

SEMVER_REGEX = re.compile(r"^v?\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$")

def handle_init(args):
    """Bootstrap a standard Protocol v3.8.0 .agent/ folder structure."""
    target_dir = Path(getattr(args, "path", ".") or ".").resolve()
    from agent_workspace.core.onboarding import TargetRepoOnboarder

    onboarder = TargetRepoOnboarder(target_dir)
    rec = onboarder.analyze()

    if getattr(args, "dry_run", False):
        print(f"Dry run active: proposed bootstrapping operations for Protocol v3.8.0 at {target_dir}:")
        print("  [Directory] .agent")
        print("  [Directory] .agent/evidence")
        print("  [Directory] .agent/patches")
        print("  [File]      AGENTS.md")
        print("  [File]      .agent/state.md")
        print("  [File]      .agent/ownership.md")
        print("  [File]      .agent/test_policy.md")
        print("  [File]      .agent/task_environment.json")
        return

    force = getattr(args, "force", False)
    created = onboarder._scaffold_protocol_files(rec, force=force)
    print(f"Initialized Protocol v3.8.0 workspace at: {target_dir}")
    if created:
        print(f"Created {len(created)} configuration file(s):")
        for f in created:
            print(f"  + {f}")
    else:
        print("Configuration already exists. Use --force to overwrite.")


def handle_onboard(args):
    """Analyze target repository and generate TaskEnvironment configuration."""
    target = getattr(args, "path", ".") or "."
    scaffold = not getattr(args, "no_scaffold", False)
    force = getattr(args, "force", False)
    out_format = getattr(args, "format", "text")

    from agent_workspace.core.onboarding import TargetRepoOnboarder

    onboarder = TargetRepoOnboarder(target)
    result = onboarder.onboard(scaffold=scaffold, force=force)

    if out_format == "json":
        print(result.model_dump_json(indent=2))
        return

    print("=" * 70)
    print(" 🚀 LAS Target Repository Onboarding Profile (ADR-006)")
    print("=" * 70)
    print(f" Target Path       : {result.target_path}")
    print(f" Git Repository    : {'Yes' if result.is_git_repository else 'No (Warning: not a git repo)'}")
    print(f" Active Branch     : {result.current_branch}")
    print(f" Head Commit       : {result.head_commit[:8] if len(result.head_commit) >= 8 else result.head_commit}")
    print(f" Clean Checkout    : {'Yes' if result.is_clean else 'No (Dirty files detected)'}")
    print(f" Primary Ecosystem : {result.recommendation.primary_ecosystem.upper()}")
    print(f" Detected Stacks   : {', '.join(result.recommendation.detected_ecosystems) or 'None'}")
    print(f" Recommended Test  : {result.recommendation.recommended_test_command}")
    print(f" Mutable Scopes    : {', '.join(result.recommendation.default_mutable_scopes)}")
    print(f" Protected Scopes  : {', '.join(result.recommendation.protected_scopes[:4])}...")
    print(f" Assigned Role     : {result.recommendation.recommended_role}")
    print("-" * 70)
    if result.scaffolded_files:
        print(f" Scaffolded {len(result.scaffolded_files)} Protocol v3.8.0 configuration file(s):")
        for f in result.scaffolded_files:
            print(f"   + {f}")
    else:
        print(" Configuration files already exist (use --force to overwrite).")
    print("=" * 70)


def handle_benchmark(args):
    """Execute the official Golden Flow Benchmark suite and calculate 6 KPIs."""
    from agent_workspace.core.pipeline.benchmark import GoldenFlowBenchmarkEngine, BenchmarkScenarioId

    selected_scenarios = None
    if getattr(args, "scenarios", None):
        raw_list = [s.strip().upper() for s in args.scenarios.split(",")]
        selected_scenarios = []
        for name in raw_list:
            if hasattr(BenchmarkScenarioId, name):
                selected_scenarios.append(getattr(BenchmarkScenarioId, name))
            elif hasattr(BenchmarkScenarioId, f"SCENARIO_{name}"):
                selected_scenarios.append(getattr(BenchmarkScenarioId, f"SCENARIO_{name}"))
            else:
                print(f"Unknown scenario ID: {name}", file=sys.stderr)
                sys.exit(1)

    print("Running LAS Official Golden Flow Benchmark Suite...")
    engine = GoldenFlowBenchmarkEngine()
    scorecard = engine.run_benchmark()

    print("\n" + "=" * 80)
    print(" 🏆 LAS Golden Flow Benchmark Scorecard (ADR-006)")
    print("=" * 80)
    print(f" Overall Verdict              : {scorecard.advisory_verdict}")
    print(f" 1. Mission Completion Rate   : {scorecard.mission_completion_rate * 100:.1f}% ({scorecard.successful_scenarios}/{scorecard.total_scenarios})")
    print(f" 2. Time to Verified Latency  : {scorecard.avg_time_to_verified_completion_ms:.2f} ms")
    print(f" 3. Scope Containment Rate    : {scorecard.scope_containment_rate * 100:.1f}% ({scorecard.total_scope_violations_blocked} blocked)")
    print(f" 4. Review Freshness Invariant: {'VERIFIED' if scorecard.review_freshness_verified else 'STALE'}")
    print(f" 5. Canonical Preservation    : {'100% CLEAN' if scorecard.canonical_host_preservation_pass else 'DIRTY'}")
    print(f" 6. Context Token Efficiency  : ~{scorecard.context_token_efficiency_kb:.2f} KB")
    print("-" * 80)
    print(f" {'Scenario ID':<32} | {'Name':<24} | {'Stage Reached':<14} | {'Lat(ms)':<8}")
    print("-" * 80)
    for r in scorecard.scenario_receipts:
        print(f" {r.scenario_id:<32} | {r.name[:24]:<24} | {r.stage_reached:<14} | {r.duration_ms:<8.1f}")
    print("=" * 80)

    out_json = getattr(args, "output_json", None)
    if out_json:
        engine.export_receipt(scorecard, out_json)
        print(f"Persisted benchmark receipt to {out_json}")


def handle_pipeline_run(args):
    """Run an autonomous coding task through CodingPipelineManager."""
    target_dir = str(Path(getattr(args, "target_dir", ".") or ".").resolve())
    requirement = getattr(args, "requirement", None)
    if not requirement:
        print("Error: --requirement is required for pipeline run.", file=sys.stderr)
        sys.exit(1)

    from agent_workspace.core.pipeline.manager import CodingPipelineManager
    from agent_workspace.core.pipeline.models import CodingTaskRequest

    inspected_files = [f.strip() for f in args.inspected_files.split(",")] if getattr(args, "inspected_files", None) else ["AGENTS.md"]
    target_files = [f.strip() for f in args.target_files.split(",")] if getattr(args, "target_files", None) else ["src/"]
    allowed_roles = [getattr(args, "role", "DOMAIN_LOGIC_AGENT")]
    ladder_tests = [cmd.strip() for cmd in args.ladder_tests.split(",")] if getattr(args, "ladder_tests", None) else None
    enable_committee = getattr(args, "committee", False)
    debate_rounds = getattr(args, "debate_rounds", 1)
    committee_roles = [r.strip() for r in args.committee_roles.split(",")] if getattr(args, "committee_roles", None) else ["architect", "securityauditor", "qaengineer"]
    offline_mode = getattr(args, "offline", False) or getattr(args, "local", False)
    thinking_budget = getattr(args, "thinking_budget", None)
    reasoning_effort = getattr(args, "reasoning_effort", None)
    use_mesh = getattr(args, "mesh", False)
    mesh_peers = [p.strip() for p in args.mesh_peers.split(",")] if getattr(args, "mesh_peers", None) else []
    enable_self_healing = getattr(args, "self_healing", False)
    max_healing_attempts = getattr(args, "max_healing_attempts", 3)

    mesh_coordinator = None
    if use_mesh:
        from agent_workspace.core.federated_mesh import get_federated_coordinator, PeerCapability
        mesh_coordinator = get_federated_coordinator()
        for p_addr in mesh_peers:
            if ":" in p_addr:
                h, pt = p_addr.split(":", 1)
                mesh_coordinator.register_peer(
                    node_id=f"peer-{h}-{pt}",
                    role="worker",
                    host=h,
                    port=int(pt),
                    capabilities=[PeerCapability.REASONING_ENGINE, PeerCapability.TEST_RUNNER],
                )

    manager = CodingPipelineManager(
        workspace_path=target_dir,
        ladder_test_commands=ladder_tests,
        mesh_coordinator=mesh_coordinator,
    )
    req = CodingTaskRequest(
        requirement=requirement,
        inspected_files=inspected_files,
        target_files=target_files,
        allowed_roles=allowed_roles,
        enable_committee=enable_committee,
        debate_rounds=debate_rounds,
        committee_roles=committee_roles,
        offline_mode=offline_mode,
        thinking_budget=thinking_budget,
        reasoning_effort=reasoning_effort,
        use_mesh=use_mesh,
        mesh_peers=mesh_peers,
        enable_self_healing=enable_self_healing,
        max_healing_attempts=max_healing_attempts,
    )

    print(f"🚀 Initializing LAS Autonomous Coding Task: {requirement}")
    print(f"   Target Workspace : {target_dir}")
    print(f"   Assigned Role    : {allowed_roles[0]}")
    print(f"   Inspected Files  : {inspected_files}")
    print(f"   Target Files     : {target_files}")
    if enable_committee:
        print(f"   Committee Debate : ENABLED ({debate_rounds} round(s), roles: {', '.join(committee_roles)})")
    if offline_mode:
        print("   Execution Mode   : AIR-GAPPED OFFLINE (Ollama local inference)")
    if thinking_budget:
        print(f"   Thinking Budget  : {thinking_budget} tokens (Effort: {reasoning_effort or 'auto'})")
    if use_mesh:
        print(f"   Federated Mesh   : ENABLED (Peers: {len(mesh_coordinator.peers) if mesh_coordinator else 0})")
    if enable_self_healing:
        print(f"   Self-Healing     : ENABLED (Max attempts: {max_healing_attempts})")

    auto_approve = getattr(args, "auto_approve", False)
    if auto_approve:
        print("   Stop-and-Wait    : AUTO_APPROVED (--auto-approve active)")
        result = manager.run_convenience(req)
    else:
        state = manager.handle_intake(req)
        plan = manager.generate_plan(state.task_id)
        print("\n" + "=" * 60)
        print(" 🛡️ Stop-and-Wait Architecture Gate (ADR-005)")
        print("=" * 60)
        print(f" Task ID     : {state.task_id}")
        print(f" Summary     : {plan.plan_summary}")
        print(f" Target Files: {plan.target_files}")
        print(f" Edge Cases  : {plan.edge_cases}")
        print("=" * 60)
        try:
            confirm = input("Approve this mutation plan? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        if confirm not in ("y", "yes"):
            print("Execution halted: Plan was not approved by human operator.")
            sys.exit(1)
        manager.approve_plan(state.task_id, approval_token="CLI_INTERACTIVE_APPROVED")
        result = manager.execute_task(state.task_id)

    print("\n" + "=" * 60)
    print(f" Pipeline Terminal Status: {result.current_stage.value}")
    print("=" * 60)
    if result.draft_pr:
        print(f" Draft PR Title: {result.draft_pr.title}")
        if result.draft_pr.pr_url:
            print(f" PR URL       : {result.draft_pr.pr_url}")
        if result.draft_pr.patch_bundle_path:
            print(f" Patch Bundle : {result.draft_pr.patch_bundle_path}")
    if result.verification_receipts:
        print("\n Verification Ladder:")
        for v in result.verification_receipts:
            print(f"   [{v.status.value}] {v.command} (Exit: {v.exit_code}, {v.duration_ms:.0f}ms)")
    if result.self_healing_attempts:
        print(f"\n 🩺 Self-Healing Diagnostics ({len(result.self_healing_attempts)} attempt(s)):")
        for attempt in result.self_healing_attempts:
            status_icon = "✅" if attempt.healed else "❌"
            print(f"   [{status_icon}] Attempt #{attempt.attempt_number} (Strategy: {attempt.strategy}): {attempt.fix_description}")
            if attempt.error_symptom:
                print(f"       Failure: {attempt.error_symptom[:80]}")
    if result.rollback_receipt:
        print(f"\n ⏪ Auto-Rollback Executed (Status: {result.rollback_receipt.status}):")
        print(f"   Target Dir     : {result.rollback_receipt.target_dir}")
        print(f"   Rolled Back Git: {result.rollback_receipt.rolled_back_commit[:8] if result.rollback_receipt.rolled_back_commit else 'N/A'}")
        print(f"   Reason         : {result.rollback_receipt.reason}")


def handle_serve(args):
    """Launch the FastAPI REST server and WebSocket hub."""
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)
    from agent_workspace.server import run_server
    print(f"Starting LAS API Server on http://{host}:{port} ...")
    run_server(host=host, port=port)


def handle_status(args):
    """Inspect workspace health, git status, and latest benchmark receipts."""
    target = Path(getattr(args, "path", ".") or ".").resolve()
    from agent_workspace.core.repository import RepositoryInspector

    inspector = RepositoryInspector()
    profile = inspector.inspect(str(target))

    agent_dir = target / ".agent"
    has_agent = agent_dir.is_dir()
    protocol_version = "None"
    if has_agent and (agent_dir / "state.md").exists():
        for line in (agent_dir / "state.md").read_text(encoding="utf-8").splitlines():
            if ("Required Version" in line or "Protocol Baseline:" in line or "Loaded Version" in line) and ":" in line:
                protocol_version = line.split(":", 1)[1].strip().strip("`")
                break

    receipt_file = agent_dir / "evidence" / "golden_benchmark_receipt.json"
    last_benchmark = "No benchmark runs recorded"
    if receipt_file.exists():
        try:
            data = json.loads(receipt_file.read_text(encoding="utf-8"))
            last_benchmark = f"{data.get('overall_status')} ({data.get('mission_completion_rate', 0):.0f}% completion, {data.get('executed_at')})"
        except Exception:
            last_benchmark = "Corrupt receipt"

    print("=" * 60)
    print(" 📊 LAS Developer Control Plane Status")
    print("=" * 60)
    print(f" Workspace Path    : {target}")
    print(f" Protocol Baseline : {protocol_version}")
    print(f" Git Branch        : {profile.current_branch}")
    print(f" Head Commit       : {profile.head_commit[:8] if len(profile.head_commit) >= 8 else profile.head_commit}")
    print(f" Clean Checkout    : {'Yes' if profile.is_clean else 'No (Uncommitted files exist)'}")
    print(f" Ecosystems        : {', '.join(profile.detected_ecosystems) or 'None'}")
    print(f" Latest Benchmark  : {last_benchmark}")
    print("=" * 60)


def handle_mesh(args):
    """Manage Distributed P2P Mesh peering and worktree federation (Phase 87)."""
    sub = getattr(args, "mesh_action", "status")
    import urllib.request
    import urllib.error

    server_url = os.environ.get("LAS_SERVER_URL", "http://127.0.0.1:8000")

    if sub == "status":
        live_data = None
        try:
            req = urllib.request.Request(f"{server_url}/v1/mesh/status")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    live_data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        if live_data:
            local_prof = live_data["local_node"]
            peers = live_data["connected_peers"]
            print("=" * 75)
            print(" 🌐 LAS Federated P2P Mesh Topology Status (Live Daemon)")
            print("=" * 75)
            print(f" Local Node ID  : {local_prof['node_id']}")
            print(f" Role / Address : {local_prof['role']} ({local_prof['host']}:{local_prof['port']})")
            print(f" Capabilities   : {', '.join(local_prof['capabilities'])}")
            print(f" Connected Peers: {len(peers)} / {live_data['peer_count']}")
            print(f" Cluster Health : {live_data['cluster_health']} (Avg Latency: {live_data['avg_latency_ms']}ms)")
            print("-" * 75)
            if not peers:
                print(" No remote mesh peers registered. Operating in standalone local mode.")
            else:
                print(f" {'Peer Node ID':<22} | {'Role':<12} | {'Address':<20} | {'Latency':<9} | {'Load'}")
                print("-" * 75)
                for p in peers:
                    print(f" {p['node_id']:<22} | {p['role']:<12} | {p['host'] + ':' + str(p['port']):<20} | {p['latency_ms']:5.1f}ms  | {p['load_score']:.2f}")
            print("=" * 75)
            return

        from agent_workspace.core.federated_mesh import get_federated_coordinator, PeerCapability
        coordinator = get_federated_coordinator()
        local_prof = coordinator.get_local_profile()
        peers = coordinator.list_peers()
        print("=" * 75)
        print(" 🌐 LAS Federated P2P Mesh Topology Status (Local Node)")
        print("=" * 75)
        print(f" Local Node ID  : {local_prof.node_id}")
        print(f" Role / Address : {local_prof.role} ({local_prof.host}:{local_prof.port})")
        print(f" Capabilities   : {', '.join(c.value for c in local_prof.capabilities)}")
        print(f" Connected Peers: {len([p for p in peers if p.status == 'connected'])} / {len(peers)}")
        print("-" * 75)
        if not peers:
            print(" No remote mesh peers registered. Operating in standalone local mode.")
        else:
            print(f" {'Peer Node ID':<22} | {'Role':<12} | {'Address':<20} | {'Latency':<9} | {'Load'}")
            print("-" * 75)
            for p in peers:
                print(f" {p.node_id:<22} | {p.role:<12} | {p.host + ':' + str(p.port):<20} | {p.latency_ms:5.1f}ms  | {p.load_score:.2f}")
        print("=" * 75)

    elif sub == "join":
        seed = getattr(args, "seed", None)
        if not seed:
            print("Error: seed address required. Usage: las mesh join <host:port>", file=sys.stderr)
            sys.exit(1)
        if ":" not in seed:
            print("Error: Invalid address format. Expected host:port (e.g. 127.0.0.1:8001)", file=sys.stderr)
            sys.exit(1)

        try:
            req_data = json.dumps({"seed_address": seed}).encode("utf-8")
            req = urllib.request.Request(f"{server_url}/v1/mesh/join", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    print(f"Successfully joined mesh seed node '{data.get('node_id')}' ({seed}) via live daemon.")
                    return
        except Exception:
            pass

        host, port_str = seed.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            print("Error: Port must be an integer.", file=sys.stderr)
            sys.exit(1)

        from agent_workspace.core.federated_mesh import get_federated_coordinator, PeerCapability
        coordinator = get_federated_coordinator()
        prof = coordinator.register_peer(
            node_id=f"seed-{host}-{port}",
            role="worker",
            host=host,
            port=port,
            capabilities=[PeerCapability.REASONING_ENGINE, PeerCapability.TEST_RUNNER],
            latency_ms=10.0,
            load_score=0.1,
        )
        print(f"Successfully joined mesh seed node '{prof.node_id}' ({host}:{port}).")

    elif sub == "pki":
        live_cert = None
        try:
            req = urllib.request.Request(f"{server_url}/v1/mesh/pki/cert")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    live_cert = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        if not live_cert:
            from agent_workspace.core.federated_mesh import get_federated_coordinator
            import datetime
            coordinator = get_federated_coordinator()
            now = datetime.datetime.now(datetime.timezone.utc)
            rem = (coordinator.cert_expiry - now).total_seconds() if coordinator.cert_expiry else None
            live_cert = {
                "node_id": coordinator.node_id,
                "cert_fingerprint": coordinator.cert_fingerprint,
                "expires_at": coordinator.cert_expiry.isoformat() if coordinator.cert_expiry else None,
                "expires_in_sec": round(rem, 1) if rem is not None else None,
                "status": "ACTIVE" if (rem and rem > 300) else ("EXPIRING_SOON" if rem and rem > 0 else "EXPIRED"),
            }

        print("=" * 75)
        print(" 🔒 Zero-Trust mTLS PKI Identity & Node Attestation Status")
        print("=" * 75)
        print(f" Node ID         : {live_cert['node_id']}")
        print(f" Fingerprint     : {live_cert['cert_fingerprint']}")
        print(f" Certificate TTL : {live_cert.get('expires_in_sec', 'N/A')}s remaining ({live_cert.get('status', 'ACTIVE')})")
        print(f" Expires At      : {live_cert.get('expires_at')}")
        print("=" * 75)

    elif sub == "rotate":
        validity = getattr(args, "validity", 3600)
        live_cert = None
        try:
            req_data = json.dumps({"validity_seconds": validity}).encode("utf-8")
            req = urllib.request.Request(f"{server_url}/v1/mesh/pki/rotate", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    live_cert = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        if not live_cert:
            from agent_workspace.core.federated_mesh import get_federated_coordinator
            coordinator = get_federated_coordinator()
            coordinator.rotate_cert(validity_seconds=validity)
            live_cert = {
                "node_id": coordinator.node_id,
                "cert_fingerprint": coordinator.cert_fingerprint,
                "expires_at": coordinator.cert_expiry.isoformat() if coordinator.cert_expiry else None,
            }

        print("=" * 75)
        print(" 🔄 Zero-Trust PKI Certificate Rotated Successfully")
        print("=" * 75)
        print(f" Node ID         : {live_cert['node_id']}")
        print(f" New Fingerprint : {live_cert['cert_fingerprint']}")
        print(f" Validity        : {validity}s")
        print(f" New Expiry      : {live_cert.get('expires_at')}")
        print("=" * 75)

    elif sub == "attest":
        seed = getattr(args, "seed", None)
        if not seed:
            print("Error: Target peer address required. Usage: las mesh attest <host:port>", file=sys.stderr)
            sys.exit(1)

        from agent_workspace.core.federated_mesh import get_federated_coordinator
        coordinator = get_federated_coordinator()
        target_node_id = f"peer-{seed.replace(':', '-')}"
        chal = coordinator.generate_attestation_challenge(target_node_id=target_node_id)
        proof = coordinator.create_attestation_proof(chal)
        ok, msg = coordinator.verify_attestation_proof(proof)

        print("=" * 75)
        print(" 🛡️ Zero-Trust Mutual Attestation Handshake")
        print("=" * 75)
        print(f" Target Peer     : {seed}")
        print(f" Challenge Nonce : {chal.nonce[:16]}...")
        print(f" Status          : {'VERIFIED' if ok else 'REJECTED'}")
        print(f" Details         : {msg}")
        print("=" * 75)

    elif sub == "raft":
        raft_cmd = getattr(args, "raft_command", "status")
        from agent_workspace.core.federated_mesh import get_federated_coordinator
        coordinator = get_federated_coordinator()
        if raft_cmd == "elect":
            became_leader = coordinator.start_raft_election()
            print("=" * 75)
            print(" 🗳️ Raft Leader Election Triggered")
            print("=" * 75)
            print(f" Node ID         : {coordinator.node_id}")
            print(f" Current Role    : {coordinator.raft_node.role.value}")
            print(f" Current Term    : {coordinator.raft_node.current_term}")
            print(f" Leader Elected  : {became_leader}")
            print("=" * 75)
        elif raft_cmd == "log":
            limit = getattr(args, "limit", 20)
            log_entries = coordinator.get_raft_log()
            print("=" * 75)
            print(" 📜 Raft Replicated Committee Debate Ledger")
            print("=" * 75)
            print(f" Commit Index    : {coordinator.raft_node.commit_index}")
            print(f" Last Applied    : {coordinator.raft_node.last_applied}")
            print(f" Total Entries   : {len(log_entries)}")
            print("-" * 75)
            print(f" {'Idx':<5} | {'Term':<5} | {'Type':<18} | {'Author':<16} | {'Status'}")
            print("-" * 75)
            for entry in log_entries[-limit:]:
                status_str = "COMMITTED" if entry.index <= coordinator.raft_node.commit_index else "UNCOMMITTED"
                print(f" {entry.index:<5} | {entry.term:<5} | {entry.entry_type.value:<18} | {entry.author_node_id:<16} | {status_str}")
            print("=" * 75)
        else:
            st = coordinator.get_raft_status()
            print("=" * 75)
            print(" 🏛️ Distributed Committee Raft Consensus Status")
            print("=" * 75)
            print(f" Node ID         : {st['node_id']}")
            print(f" Current Role    : {st['role']}")
            print(f" Current Term    : {st['term']}")
            print(f" Leader ID       : {st['leader_id'] or 'None'}")
            print(f" Commit Index    : {st['commit_index']}")
            print(f" Last Applied    : {st['last_applied']}")
            print(f" Log Length      : {st['log_length']}")
            print(f" Quorum Size     : {st['quorum_size']} (Active Peers: {st['cluster_peers_count']})")
            print("=" * 75)

    elif sub == "memory":
        mem_cmd = getattr(args, "memory_command", "stats")
        from agent_workspace.core.federated_mesh import get_federated_coordinator
        coordinator = get_federated_coordinator()
        if mem_cmd == "query":
            q = getattr(args, "query", "") or "architecture"
            top_k = getattr(args, "top_k", 5)
            cat = getattr(args, "category", None)
            res = coordinator.query_vector_memory(q, top_k=top_k, category=cat)
            print("=" * 75)
            print(f" 🔍 Federated Vector Memory Search (Query: '{q}')")
            print("=" * 75)
            print(f" Results Found   : {len(res)}")
            print("-" * 75)
            print(f" {'Rank':<5} | {'Score':<7} | {'Category':<12} | {'Task':<10} | {'Content'}")
            print("-" * 75)
            for r in res:
                content_snip = r['content'][:35] + ("..." if len(r['content']) > 35 else "")
                print(f" {r['rank']:<5} | {r['similarity']:<7.4f} | {r['category']:<12} | {r['task_id']:<10} | {content_snip}")
            print("=" * 75)
        elif mem_cmd == "sync":
            peer = getattr(args, "peer", None) or "peer-remote"
            res = coordinator.sync_vector_memory(peer)
            print("=" * 75)
            print(f" 🔄 Federated Vector Memory Synchronized with {peer}")
            print("=" * 75)
            print(f" Status          : {res.get('status', 'unknown')}")
            print(f" Merkle Root     : {res.get('merkle_root', '')}")
            print(f" Total Entries   : {res.get('total_entries', 0)}")
            print("=" * 75)
        else:
            stats = coordinator.get_vector_memory_stats()
            print("=" * 75)
            print(" 🧠 Federated Vector Memory & Knowledge Topology Status")
            print("=" * 75)
            print(f" Node ID         : {stats['node_id']}")
            print(f" Total Vectors   : {stats['total_entries']}")
            print(f" Merkle Root     : {stats['merkle_root']}")
            print(f" Embedding Dim   : {stats['embedding_dimension']}")
            print(f" Categories      : {json.dumps(stats.get('category_breakdown', {}))}")
            print("=" * 75)


def handle_chaos(args):
    """Manage Federated Chaos Fault Injection (Phase 91)."""
    sub = getattr(args, "chaos_action", "list")
    import urllib.request
    import urllib.error
    server_url = os.environ.get("LAS_SERVER_URL", "http://127.0.0.1:8000")

    if sub == "list":
        faults = None
        try:
            req = urllib.request.Request(f"{server_url}/v1/mesh/chaos/faults")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    faults = data.get("faults", [])
        except Exception:
            pass

        if faults is None:
            from agent_workspace.core.chaos import MeshChaosManager
            chaos_mgr = MeshChaosManager.get_instance()
            faults = [f.model_dump() for f in chaos_mgr.list_active_faults()]

        print("=" * 80)
        print(" 🌪️ LAS Federated Mesh Chaos Fault Injection Status")
        print("=" * 80)
        print(f" Active Faults: {len(faults)}")
        print("-" * 80)
        if not faults:
            print(" No active chaos faults. Mesh network conditions are nominal.")
        else:
            print(f" {'Rule ID':<10} | {'Fault Type':<18} | {'Src -> Dst':<24} | {'Latency':<9} | {'Drop'}")
            print("-" * 80)
            for f in faults:
                srcs = ",".join(f.get("source_node_ids", [])) or "*"
                dsts = ",".join(f.get("target_node_ids", [])) or "*"
                src_dst = f"{srcs} -> {dsts}"
                lat = f"{f.get('latency_ms', 0):.0f}ms"
                drop = f"{f.get('probability', 0)*100:.0f}%"
                print(f" {f['rule_id']:<10} | {f['fault_type']:<18} | {src_dst:<24} | {lat:<9} | {drop}")
        print("=" * 80)

    elif sub == "inject":
        fault_type = getattr(args, "fault_type", "LATENCY_SPIKE")
        source = getattr(args, "source_node_id", "*")
        target = getattr(args, "target_node_id", "*")
        source_nodes = [s.strip() for s in source.split(",") if s.strip() and s.strip() != "*"]
        target_nodes = [t.strip() for t in target.split(",") if t.strip() and t.strip() != "*"]
        latency = getattr(args, "latency_ms", 0.0)
        drop = getattr(args, "drop_prob", 1.0)
        ttl = getattr(args, "ttl_seconds", 60.0)

        injected = None
        try:
            payload = {
                "fault_type": fault_type,
                "source_node_ids": source_nodes,
                "target_node_ids": target_nodes,
                "latency_ms": latency,
                "probability": drop,
                "duration_seconds": ttl,
            }
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(f"{server_url}/v1/mesh/chaos/inject", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    injected = data.get("rule", {})
        except Exception:
            pass

        if not injected:
            from agent_workspace.core.chaos import MeshChaosManager, ChaosFaultType
            chaos_mgr = MeshChaosManager.get_instance()
            rule = chaos_mgr.inject_fault(
                fault_type=ChaosFaultType(fault_type),
                source_node_ids=source_nodes,
                target_node_ids=target_nodes,
                latency_ms=latency,
                probability=drop,
                duration_seconds=ttl,
            )
            injected = rule.model_dump()

        print("=" * 80)
        print(" 💥 Chaos Fault Injected Successfully")
        print("=" * 80)
        print(f" Rule ID     : {injected.get('rule_id')}")
        print(f" Fault Type  : {injected.get('fault_type')}")
        src_str = ",".join(injected.get('source_node_ids', [])) or "*"
        dst_str = ",".join(injected.get('target_node_ids', [])) or "*"
        print(f" Scope       : {src_str} -> {dst_str}")
        print(f" Latency     : {injected.get('latency_ms', 0):.0f}ms")
        print(f" Drop Prob   : {injected.get('probability', 0)*100:.0f}%")
        print(f" Duration    : {injected.get('duration_seconds', 0)}s")
        print("=" * 80)

    elif sub == "partition":
        group_a = [n.strip() for n in args.group_a.split(",") if n.strip()]
        group_b = [n.strip() for n in args.group_b.split(",") if n.strip()]
        ttl = getattr(args, "ttl_seconds", 60.0)

        from agent_workspace.core.chaos import MeshChaosManager
        chaos_mgr = MeshChaosManager.get_instance()
        rules = chaos_mgr.create_partition(group_a, group_b, duration_seconds=ttl)

        print("=" * 80)
        print(" ⚡ Network Partition Injected")
        print("=" * 80)
        print(f" Partition A : {group_a}")
        print(f" Partition B : {group_b}")
        print(f" Rules Count : {len(rules)} partition rules created")
        print(f" Duration    : {ttl}s")
        print("=" * 80)

    elif sub == "isolate":
        node_id = getattr(args, "node", None)
        if not node_id:
            print("Error: --node is required for chaos isolate", file=sys.stderr)
            sys.exit(1)
        ttl = getattr(args, "ttl_seconds", 60.0)

        from agent_workspace.core.chaos import MeshChaosManager
        chaos_mgr = MeshChaosManager.get_instance()
        rules = chaos_mgr.isolate_node(node_id, duration_seconds=ttl)

        print("=" * 80)
        print(" 🔌 Node Isolation Injected")
        print("=" * 80)
        print(f" Isolated Node: {node_id}")
        print(f" Rules Count  : {len(rules)} ingress/egress drop rules created")
        print(f" Duration     : {ttl}s")
        print("=" * 80)

    elif sub == "clear":
        rule_id = getattr(args, "rule_id", None)
        clear_all = getattr(args, "all", False)
        if not rule_id and not clear_all:
            clear_all = True

        cleared_count = 0
        try:
            payload = {"rule_id": rule_id}
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(f"{server_url}/v1/mesh/chaos/clear", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    cleared_count = data.get("cleared_count", 1 if data.get("status") == "cleared" else 0)
        except Exception:
            pass

        if cleared_count == 0:
            from agent_workspace.core.chaos import MeshChaosManager
            chaos_mgr = MeshChaosManager.get_instance()
            if clear_all or not rule_id:
                cleared_count = chaos_mgr.clear_all_faults()
            elif rule_id:
                cleared_count = 1 if chaos_mgr.clear_fault(rule_id) else 0

        print(f"✅ Cleared {cleared_count} chaos fault rule(s). Mesh operating normally.")


def handle_cluster(args):
    """Manage Multi-Worker Cluster and E2E Demonstration (Phase 91)."""
    sub = getattr(args, "cluster_action", "demo")
    if sub == "demo":
        from agent_workspace.core.cluster_demo import MultiWorkerCluster
        print("=" * 80)
        print(" 🚀 Launching Production E2E Multi-Worker Cluster Demonstration")
        print("=" * 80)
        cluster = MultiWorkerCluster()
        receipt = cluster.run_full_demo()

        print("\n" + "=" * 80)
        print(" 📋 Cluster Demonstration Scorecard Receipt")
        print("=" * 80)
        print(f" Demo ID         : {receipt.demo_id}")
        print(f" Nodes in Mesh   : {', '.join(receipt.nodes_participating)}")
        print(f" Total Duration  : {receipt.duration_total_ms:.2f} ms")
        print(f" Steps Passed    : {receipt.passed_steps} / {receipt.total_steps}")
        print(f" Overall Status  : {'PASS' if receipt.success else 'FAIL'}")
        print("-" * 80)
        print(f" {'Step Name':<55} | {'Status':<8} | {'Duration':<10}")
        print("-" * 80)
        for s in receipt.step_receipts:
            status_icon = "✅ PASS" if s.status == "PASS" else "❌ FAIL"
            print(f" {s.step_name:<55} | {status_icon:<8} | {s.duration_ms:>6.2f} ms")
        print("=" * 80)

        save_receipt = getattr(args, "save_receipt", True)
        out_path = getattr(args, "output", None)
        if save_receipt or out_path:
            target_path = Path(out_path) if out_path else Path(".agent/evidence/cluster_demo_receipt.json")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
            print(f" 💾 Demonstration receipt saved to: {target_path}")
        print("=" * 80)


def handle_lint(args):
    """Statically lint the PAP workspace contracts."""
    project_root = Path(args.path).resolve()
    agent_dir = project_root / ".agent"

    errors = []
    warnings = []

    # 1. Check agent.md existence and keys
    agent_md = agent_dir / "agent.md"
    if not agent_md.is_file():
        errors.append("CRITICAL: .agent/agent.md is missing")
        print("\n".join(errors))
        sys.exit(1)

    try:
        raw_agent = agent_md.read_text(encoding="utf-8")
        from core.engine import AgentEngine
        frontmatter, _ = AgentEngine._split_frontmatter(raw_agent)
    except Exception as e:
        errors.append(f"CRITICAL: Failed to parse .agent/agent.md frontmatter: {e}")
        print("\n".join(errors))
        sys.exit(1)

    REQUIRED_KEYS = [
        "protocol_version",
        "min_runtime_version",
        "name",
        "version",
        "purpose",
        "language",
        "authorization_level",
        "use_case_tags",
        "tools"
    ]
    for key in REQUIRED_KEYS:
        if key not in frontmatter:
            errors.append(f"ERROR: agent.md is missing required manifest key '{key}'")

    # 2. Check semver formats
    for key in ["protocol_version", "min_runtime_version", "version"]:
        if key in frontmatter:
            val = str(frontmatter[key])
            if not SEMVER_REGEX.match(val):
                errors.append(f"ERROR: agent.md '{key}' has invalid semver format: '{val}'")

    # 3. Live skill contract alignment
    tools = frontmatter.get("tools", [])
    if not isinstance(tools, list):
        errors.append("ERROR: agent.md 'tools' key must be a list of tool names")
        tools = []

    skills_dir = agent_dir / "skills"

    for tool in tools:
        contract_path = skills_dir / f"{tool}.md"
        if not contract_path.is_file():
            errors.append(f"ERROR: Missing skill contract for tool '{tool}' at .agent/skills/{tool}.md")
            continue

        try:
            raw_contract = contract_path.read_text(encoding="utf-8")
            c_fm, _ = AgentEngine._split_frontmatter(raw_contract)

            required_contract_keys = ["id", "description", "inputs", "outputs", "safety_notes", "version"]
            for ck in required_contract_keys:
                if ck not in c_fm:
                    errors.append(f"ERROR: Contract skills/{tool}.md is missing required key '{ck}'")

            if c_fm.get("id") != tool:
                errors.append(f"ERROR: Contract skills/{tool}.md ID '{c_fm.get('id')}' does not match tool name '{tool}'")

            c_ver = c_fm.get("version")
            if c_ver and not SEMVER_REGEX.match(str(c_ver)):
                errors.append(f"ERROR: Contract skills/{tool}.md version '{c_ver}' is not valid semver")
        except Exception as e:
            errors.append(f"ERROR: Failed to parse skills/{tool}.md: {e}")

    if skills_dir.is_dir():
        for md_file in skills_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            if md_file.stem not in tools:
                warnings.append(f"WARNING: Orphan contract '.agent/skills/{md_file.name}' not declared in agent.md tools list")

    # 4. Workflow reference validation
    workflows_dir = agent_dir / "workflows"
    if workflows_dir.is_dir():
        for wf_file in workflows_dir.glob("*.md"):
            if wf_file.name.startswith("_"):
                continue
            try:
                raw_wf = wf_file.read_text(encoding="utf-8")
                wf_fm, _ = AgentEngine._split_frontmatter(raw_wf)

                wf_id = wf_fm.get("id", wf_file.stem)
                steps = wf_fm.get("steps", [])
                if not isinstance(steps, list):
                    errors.append(f"ERROR: Workflow '{wf_id}' 'steps' must be a list")
                    continue

                step_ids = {s.get("step_id") for s in steps if isinstance(s, dict) and s.get("step_id")}

                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(f"ERROR: Workflow '{wf_id}' step at index {idx} is not a valid dictionary")
                        continue

                    step_id = step.get("step_id")
                    skill_id = step.get("skill_id")

                    if not step_id:
                        errors.append(f"ERROR: Workflow '{wf_id}' step at index {idx} is missing 'step_id'")
                        continue

                    if not skill_id:
                        errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' is missing 'skill_id'")
                        continue

                    if skill_id not in tools:
                        errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' references undeclared tool/skill '{skill_id}'")

                    next_step = step.get("next_step")
                    if next_step and not ("{{" in next_step and "}}" in next_step):
                        if next_step not in step_ids:
                            errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' references non-existent next_step '{next_step}'")
            except Exception as e:
                errors.append(f"ERROR: Failed to parse workflow file '{wf_file.name}': {e}")

    # 5. Handle --fix if requested
    if args.fix:
        print("Auto-fix option requested. Resolving parity issues...")
        try:
            import tool_manifest
            engine = AgentEngine(workspace_path=str(project_root / "agent_workspace"))
            manifest = tool_manifest.ToolManifest.from_engine(engine)
            written = tool_manifest.sync_pap_contracts(manifest, project_root)
            tool_manifest.sync_skills_md(manifest, project_root)
            tool_manifest.sync_agent_md_tools(manifest, project_root)
            if written:
                print(f"Fixed: Scaffolded {len(written)} missing skill contracts.")

            # Remove orphan warnings from list and disk
            for warn in list(warnings):
                if "Orphan contract" in warn:
                    parts = warn.split("'")
                    if len(parts) >= 2:
                        orphan_rel = parts[1]
                        orphan_abs = project_root / orphan_rel
                        if orphan_abs.is_file():
                            orphan_abs.unlink()
                            print(f"Fixed: Removed orphan contract '{orphan_rel}'")
                            warnings.remove(warn)
            print("Parity alignment synchronized successfully.")
        except Exception as e:
            print(f"Auto-fix encountered an error: {e}", file=sys.stderr)

    if warnings:
        print(f"\nLint found {len(warnings)} non-blocking warning(s):")
        for warn in warnings:
            print(f"  {warn}")

    if errors:
        print(f"\nLint failed with {len(errors)} blocking error(s):")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("PAP Workspace contracts are 100% healthy and aligned! (0 blocking errors)")

def handle_run_debate(args):
    """Run a multi-agent consensus and debate room session."""
    if not args.topic:
        print("Error: --topic is required for running a debate.", file=sys.stderr)
        sys.exit(1)

    roles = [r.strip() for r in (args.agents or "analyst,programmer,architect").split(",")]
    agents_list = [{"role": r} for r in roles]

    from agent_workspace.core.discussion_room import DiscussionRoom

    room = DiscussionRoom(workspace_path=workspace)
    print(f"Initializing debate on: '{args.topic}'...")
    print(f"Participants: {', '.join(roles)}")
    print(f"Rounds: {args.rounds}")
    print("-" * 60)

    try:
        result = asyncio.run(room.run(
            topic=args.topic,
            agents=agents_list,
            max_rounds=args.rounds
        ))

        print("\n=== MEETING DIALOGUE TRANSCRIPT ===")
        for msg in result["transcript"]:
            print(f"\n[{msg['agent']} ({msg['role']})]:\n{msg['content']}")
            print("-" * 50)

        print("\n=== FINAL CONSENSUS SUMMARY ===")
        print(result["consensus_summary"])
        print("=" * 60)
    except Exception as e:
        print(f"Error running debate session: {e}", file=sys.stderr)
        sys.exit(1)


def handle_chat(args):
    """Run an interactive chat session with the agent."""
    engine = AgentEngine(workspace_path=workspace)
    session = args.session or f"chat-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    router = AgentRouter(engine, session_id=session)

    print(f"Starting chat session isolation: {session}")
    print("Type '/exit' or '/quit' to end the session.")
    print("-" * 60)

    async def chat_loop():
        while True:
            try:
                loop = asyncio.get_running_loop()
                user_input = await loop.run_in_executor(None, input, "\nUser: ")
                user_input = user_input.strip()
                if not user_input:
                    continue
                if user_input.lower() in ("/exit", "/quit"):
                    break

                print("Agent: ", end="", flush=True)
                async for event in router.stream_agent_loop(user_input):
                    event_type = event.get("type")
                    if event_type == "text_chunk":
                        print(event["content"], end="", flush=True)
                    elif event_type == "hitl_gate":
                        tool_name = event.get("name")
                        arguments = event.get("arguments")
                        print(f"\n[HITL Gate] Awaiting approval for execution of tool '{tool_name}' with arguments: {json.dumps(arguments, ensure_ascii=False)}")
                        choice = await loop.run_in_executor(None, input, f"Approve execution of tool '{tool_name}'? [y/N]: ")
                        approved = choice.strip().lower() in ("y", "yes")
                        router.resolve_approval(approved)
                        print(f"Approval {'granted' if approved else 'denied'}.\nAgent: ", end="", flush=True)
                    elif event_type == "error":
                        print(f"\nError: {event['content']}", flush=True)
                    elif event_type == "done":
                        print(flush=True)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError during run: {e}", flush=True)

    try:
        asyncio.run(chat_loop())
    finally:
        router.close()


def handle_stream(args):
    """Stream a single agent execution for a message."""
    engine = AgentEngine(workspace_path=workspace)
    session = args.session or "stream-session"
    router = AgentRouter(engine, session_id=session)

    async def stream_run():
        print(f"Streaming run (Session: {session})...")
        print(f"User: {args.stream}")
        print("Agent: ", end="", flush=True)

        loop = asyncio.get_running_loop()
        async for event in router.stream_agent_loop(args.stream):
            event_type = event.get("type")
            if event_type == "text_chunk":
                print(event["content"], end="", flush=True)
            elif event_type == "hitl_gate":
                tool_name = event.get("name")
                arguments = event.get("arguments")
                print(f"\n[HITL Gate] Awaiting approval for execution of tool '{tool_name}' with arguments: {json.dumps(arguments, ensure_ascii=False)}")
                choice = await loop.run_in_executor(None, input, f"Approve execution of tool '{tool_name}'? [y/N]: ")
                approved = choice.strip().lower() in ("y", "yes")
                router.resolve_approval(approved)
                print(f"Approval {'granted' if approved else 'denied'}.\nAgent: ", end="", flush=True)
            elif event_type == "error":
                print(f"\nError: {event['content']}", flush=True)
            elif event_type == "done":
                print(flush=True)

    try:
        asyncio.run(stream_run())
    finally:
        router.close()


def handle_sync_pap(args):
    """Validate schemas and automatically synchronize/bootstrap default skill templates."""
    project_root = Path(workspace).parent
    print("Running PAP v0.2.0 schema validation...")
    try:
        run_pap_validate(project_root)
    except Exception as e:
        print(f"Validation warning/error encountered: {e}")

    print("Synchronizing and bootstrapping PAP workspace contracts...")
    try:
        import tool_manifest
        engine = AgentEngine(workspace_path=str(project_root / "agent_workspace"), bypass_onboarding=True)
        manifest = tool_manifest.ToolManifest.from_engine(engine)
        written = tool_manifest.sync_pap_contracts(manifest, project_root)
        tool_manifest.sync_skills_md(manifest, project_root)
        tool_manifest.sync_agent_md_tools(manifest, project_root)
        if written:
            print(f"Synchronized: Scaffolded {len(written)} missing skill contract(s).")
            for w in written:
                print(f"  + {w}")
        else:
            print("All skill contracts are up-to-date.")
        print("Workspace synchronization completed successfully.")
    except Exception as err:
        print(f"Error during synchronization: {err}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    sys_args = sys.argv[1:]

    # Subcommands
    subcommands = {"init", "onboard", "benchmark", "pipeline", "serve", "status", "mesh", "chaos", "cluster"}

    if sys_args and sys_args[0] in subcommands:
        cmd = sys_args[0]

        if cmd == "init":
            sub_parser = argparse.ArgumentParser(prog="las init", description="Bootstrap Protocol v3.8.0 workspace.")
            sub_parser.add_argument("path", nargs="?", default=".", help="Target workspace path to initialize")
            sub_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration files")
            sub_parser.add_argument("--dry-run", action="store_true", help="Simulate initialization without writing files")
            args = sub_parser.parse_args(sys_args[1:])
            handle_init(args)
            return

        elif cmd == "onboard":
            sub_parser = argparse.ArgumentParser(prog="las onboard", description="Analyze target repository and generate TaskEnvironment configuration.")
            sub_parser.add_argument("path", nargs="?", default=".", help="Target repository directory to onboard")
            sub_parser.add_argument("--no-scaffold", action="store_true", help="Analyze repository without writing files")
            sub_parser.add_argument("--force", action="store_true", help="Overwrite existing .agent configuration")
            sub_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
            args = sub_parser.parse_args(sys_args[1:])
            handle_onboard(args)
            return

        elif cmd == "benchmark":
            sub_parser = argparse.ArgumentParser(prog="las benchmark", description="Execute the official Golden Flow Benchmark suite.")
            sub_parser.add_argument("--scenarios", type=str, help="Comma-separated scenario IDs (e.g. HAPPY_PATH_FEATURE)")
            sub_parser.add_argument("--output-json", type=str, help="Path to write JSON scorecard receipt")
            sub_parser.add_argument("--verbose", action="store_true", help="Enable verbose scenario logs")
            args = sub_parser.parse_args(sys_args[1:])
            handle_benchmark(args)
            return

        elif cmd == "pipeline":
            pipe_args = sys_args[1:]
            if not pipe_args or pipe_args[0] not in ("run",):
                print("Usage: las pipeline run [options]\n\nOptions:\n  --requirement REQ\n  --target-dir DIR\n  --inspected-files FILES\n  --target-files FILES\n  --role ROLE\n  --auto-approve\n  --ladder-tests TESTS")
                return
            pipe_sub = argparse.ArgumentParser(prog="las pipeline run", description="Run an autonomous coding task through CodingPipelineManager.")
            pipe_sub.add_argument("--requirement", type=str, required=True, help="Task requirement description")
            pipe_sub.add_argument("--target-dir", type=str, default=".", help="Target repository path")
            pipe_sub.add_argument("--inspected-files", type=str, help="Comma-separated inspected files for Anti-Summary check")
            pipe_sub.add_argument("--target-files", type=str, help="Comma-separated target mutation files")
            pipe_sub.add_argument("--role", type=str, default="DOMAIN_LOGIC_AGENT", help="Assigned Grounded Role")
            pipe_sub.add_argument("--auto-approve", action="store_true", help="Auto-approve Stop-and-Wait gate")
            pipe_sub.add_argument("--ladder-tests", type=str, help="Comma-separated custom verification ladder test commands")
            pipe_sub.add_argument("--committee", action="store_true", help="Enable multi-agent committee debate before architecture gate")
            pipe_sub.add_argument("--debate-rounds", type=int, default=1, help="Number of debate deliberation rounds (default: 1)")
            pipe_sub.add_argument("--committee-roles", type=str, help="Comma-separated specialist personas (e.g. architect,securityauditor,qaengineer)")
            pipe_sub.add_argument("--offline", action="store_true", help="Enforce air-gapped local model execution via Ollama")
            pipe_sub.add_argument("--local", action="store_true", help="Alias for --offline")
            pipe_sub.add_argument("--thinking-budget", type=int, default=None, help="Extended thinking token budget for reasoning roles (e.g. 4096, 8192)")
            pipe_sub.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default=None, help="Reasoning intensity level for o-series models")
            pipe_sub.add_argument("--mesh", action="store_true", help="Offload reasoning debate and test execution across federated P2P mesh peers")
            pipe_sub.add_argument("--mesh-peers", type=str, default=None, help="Comma-separated seed addresses of mesh peers (e.g. host:port)")
            pipe_sub.add_argument("--self-healing", action="store_true", help="Enable autonomous self-healing retry loop on verification failures")
            pipe_sub.add_argument("--max-healing-attempts", type=int, default=3, help="Maximum self-healing retry attempts (default: 3)")
            args = pipe_sub.parse_args(pipe_args[1:])
            handle_pipeline_run(args)
            return

        elif cmd == "serve":
            sub_parser = argparse.ArgumentParser(prog="las serve", description="Launch FastAPI REST server and WebSocket hub.")
            sub_parser.add_argument("--host", default=os.environ.get("LAS_BIND_HOST", "127.0.0.1"), help="Host to bind")
            sub_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
            sub_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
            sub_parser.add_argument("--offline", action="store_true", help="Run server in air-gapped offline mode via Ollama")
            args = sub_parser.parse_args(sys_args[1:])
            handle_serve(args)
            return

        elif cmd == "status":
            sub_parser = argparse.ArgumentParser(prog="las status", description="Inspect workspace health, git status, and latest receipts.")
            sub_parser.add_argument("path", nargs="?", default=".", help="Workspace path to check")
            args = sub_parser.parse_args(sys_args[1:])
            handle_status(args)
            return

        elif cmd == "mesh":
            mesh_args = sys_args[1:]
            action = mesh_args[0] if mesh_args and not mesh_args[0].startswith("-") else "status"
            mesh_sub = argparse.ArgumentParser(prog=f"las mesh {action}", description="Manage Distributed P2P Mesh peering.")
            if action == "join":
                mesh_sub.add_argument("seed", help="Seed node address in host:port format")
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "join"
            elif action == "attest":
                mesh_sub.add_argument("seed", help="Target peer address in host:port format")
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "attest"
            elif action == "rotate":
                mesh_sub.add_argument("--validity", type=int, default=3600, help="Certificate validity in seconds (default 3600)")
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "rotate"
            elif action == "pki":
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "pki"
            elif action == "raft":
                mesh_sub.add_argument("raft_command", nargs="?", default="status", choices=["status", "elect", "log"], help="Raft operation")
                mesh_sub.add_argument("--limit", type=int, default=20, help="Limit number of log entries")
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "raft"
            elif action == "memory":
                mesh_sub.add_argument("memory_command", nargs="?", default="stats", choices=["stats", "query", "sync", "list"], help="Vector memory operation")
                mesh_sub.add_argument("--query", type=str, help="Search query string")
                mesh_sub.add_argument("--top-k", type=int, default=5, help="Max results to return")
                mesh_sub.add_argument("--category", type=str, help="Filter category (DECISION, LESSON, PATTERN, ERROR)")
                mesh_sub.add_argument("--peer", type=str, help="Peer node ID or address for sync")
                args = mesh_sub.parse_args(mesh_args[1:])
                args.mesh_action = "memory"
            else:
                args = mesh_sub.parse_args(mesh_args[1:] if mesh_args and mesh_args[0] == "status" else mesh_args)
                args.mesh_action = "status"
            handle_mesh(args)
            return

        elif cmd == "chaos":
            chaos_args = sys_args[1:]
            action = chaos_args[0] if chaos_args and not chaos_args[0].startswith("-") else "list"
            chaos_sub = argparse.ArgumentParser(prog=f"las chaos {action}", description="Manage Federated Chaos Fault Injection (Phase 91).")
            if action == "inject":
                chaos_sub.add_argument("--type", dest="fault_type", default="LATENCY_SPIKE", choices=["NETWORK_PARTITION", "LATENCY_SPIKE", "PACKET_DROP", "NODE_ISOLATION", "BYZANTINE_TAMPER"], help="Fault type")
                chaos_sub.add_argument("--source", dest="source_node_id", default="*", help="Source node ID pattern or *")
                chaos_sub.add_argument("--target", dest="target_node_id", default="*", help="Target node ID pattern or *")
                chaos_sub.add_argument("--latency-ms", type=float, default=0.0, help="Artificial latency in ms")
                chaos_sub.add_argument("--drop-prob", type=float, default=1.0, help="Packet drop probability (0.0 to 1.0)")
                chaos_sub.add_argument("--ttl", type=float, default=60.0, dest="ttl_seconds", help="Fault duration in seconds")
                args = chaos_sub.parse_args(chaos_args[1:])
                args.chaos_action = "inject"
            elif action == "partition":
                chaos_sub.add_argument("--group-a", required=True, help="Comma-separated node IDs in Group A")
                chaos_sub.add_argument("--group-b", required=True, help="Comma-separated node IDs in Group B")
                chaos_sub.add_argument("--ttl", type=float, default=60.0, dest="ttl_seconds", help="Partition duration in seconds")
                args = chaos_sub.parse_args(chaos_args[1:])
                args.chaos_action = "partition"
            elif action == "isolate":
                chaos_sub.add_argument("--node", required=True, help="Node ID to isolate from the mesh")
                chaos_sub.add_argument("--ttl", type=float, default=60.0, dest="ttl_seconds", help="Isolation duration in seconds")
                args = chaos_sub.parse_args(chaos_args[1:])
                args.chaos_action = "isolate"
            elif action == "clear":
                chaos_sub.add_argument("--rule-id", type=str, default=None, help="Specific fault rule ID to remove")
                chaos_sub.add_argument("--all", action="store_true", help="Clear all active chaos faults")
                args = chaos_sub.parse_args(chaos_args[1:])
                args.chaos_action = "clear"
            else:
                args = chaos_sub.parse_args(chaos_args[1:] if chaos_args and chaos_args[0] in ("list", "status") else chaos_args)
                args.chaos_action = "list"
            handle_chaos(args)
            return

        elif cmd == "cluster":
            cluster_args = sys_args[1:]
            action = cluster_args[0] if cluster_args and not cluster_args[0].startswith("-") else "demo"
            cluster_sub = argparse.ArgumentParser(prog=f"las cluster {action}", description="Multi-Worker Cluster Orchestration and E2E Demo (Phase 91).")
            if action == "demo":
                cluster_sub.add_argument("--save-receipt", action="store_true", default=True, help="Save ClusterDemoReceipt to .agent/evidence/")
                cluster_sub.add_argument("--output", type=str, default=None, help="Custom output JSON path for receipt")
                args = cluster_sub.parse_args(cluster_args[1:])
                args.cluster_action = "demo"
            else:
                args = cluster_sub.parse_args(cluster_args[1:])
                args.cluster_action = action
            handle_cluster(args)
            return

    # If no args or standard help
    if not sys_args or sys_args in (["-h"], ["--help"]):
        print("""LAS: Governed Autonomous Multi-Agent Development Control Plane under Protocol v3.8.0

Usage:
  las <command> [options]

Core Subcommands:
  init [path]        Bootstrap Protocol v3.8.0 workspace (.agent/, AGENTS.md)
  onboard [path]     Analyze target repository and generate TaskEnvironment configuration
  pipeline run ...   Execute an autonomous coding task with Anti-Summary preflight & Stop-and-Wait gate
  benchmark          Run the official Golden Flow Benchmark suite and calculate 6 KPIs
  serve              Launch FastAPI REST API server and WebSocket telemetry hub
  status [path]      Inspect repository branch, worktree status, and latest verification receipt
  mesh [status|join|pki|rotate|attest|raft|memory] Manage Distributed P2P Mesh, PKI, Raft & Vector Memory
  chaos [list|inject|partition|isolate|clear] Manage Federated Chaos Fault Injection
  cluster [demo]     Production E2E Multi-Worker Cluster Demonstration

Developer Tools & Legacy Flags:
  --list-skills      List all registered tools
  --validate         Run structural validation
  --chat             Interactive chat session
  --run-debate       Multi-agent debate and consensus loop
  --sync-pap         Synchronize workspace contracts

Run 'las <command> --help' for more information on a specific command.""")
        return

    parser = argparse.ArgumentParser(description="Unified Operations Developer CLI toolbelt for LAS.")

    # Global flags
    parser.add_argument("--session", type=str, help="Isolation session ID for memory or workflow runs.")
    parser.add_argument("--memory-dir", type=str, help="Override long-term memory directory.")
    parser.add_argument("--backend", type=str, default="sqlite", help="Memory backend (sqlite, redis, file).")

    group = parser.add_mutually_exclusive_group(required=True)

    # Flags
    group.add_argument("--list-skills", action="store_true", help="List all registered tools.")
    group.add_argument("--describe-skill", type=str, metavar="SKILL_ID", help="Display details for a specific skill contract.")
    group.add_argument("--validate", action="store_true", help="Run PAP structural validation.")
    group.add_argument("--memory-read", type=str, metavar="KEY", help="Read memory record by key.")
    group.add_argument("--memory-write", type=str, nargs=2, metavar=("KEY", "VALUE"), help="Write a memory record by key and value.")
    group.add_argument("--run-workflow", type=str, metavar="WORKFLOW_ID", help="Execute or resume declarative workflow.")
    group.add_argument("--init", action="store_true", help="Bootstrap a standard skeletal .agent/ folder structure.")
    group.add_argument("--lint", action="store_true", help="Statically check the .agent/ workspace integrity.")
    group.add_argument("--run-debate", action="store_true", help="Orchestrate a multi-agent debate and consensus loop.")
    group.add_argument("--chat", action="store_true", help="Run an interactive, closed-loop chat session with the agent.")
    group.add_argument("--stream", type=str, metavar="MESSAGE", help="Stream a single agent run execution for a message.")
    group.add_argument("--sync-pap", action="store_true", help="Validate local schemas and automatically synchronize or bootstrap default skill templates in the workspace.")

    parser.add_argument("--resume", action="store_true", help="Resume workflow execution from last failed step.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate init subcommand without creating files.")
    parser.add_argument("--fix", action="store_true", help="Automatically correct linting anomalies if possible.")
    parser.add_argument("path", nargs="?", default=".", help="Target path for bootstrap or lint (for init/lint subcommands).")

    # Debate-specific parameters
    parser.add_argument("--topic", type=str, help="Topic for the multi-agent debate.")
    parser.add_argument("--agents", type=str, help="Comma-separated list of agent roles (e.g. analyst,programmer).")
    parser.add_argument("--rounds", type=int, default=2, help="Number of discussion rounds per agent.")

    # Map legacy word commands if present
    if "lint" in sys_args:
        idx = sys_args.index("lint")
        sys_args[idx] = "--lint"
    elif "run-debate" in sys_args:
        idx = sys_args.index("run-debate")
        sys_args[idx] = "--run-debate"
    elif "chat" in sys_args:
        idx = sys_args.index("chat")
        sys_args[idx] = "--chat"
    elif "stream" in sys_args:
        idx = sys_args.index("stream")
        sys_args[idx] = "--stream"
    elif "sync-pap" in sys_args:
        idx = sys_args.index("sync-pap")
        sys_args[idx] = "--sync-pap"

    args = parser.parse_args(sys_args)

    if args.list_skills:
        handle_list_skills(args)
    elif args.describe_skill:
        handle_describe_skill(args)
    elif args.validate:
        handle_validate(args)
    elif args.memory_read:
        handle_memory_read(args)
    elif args.memory_write:
        handle_memory_write(args)
    elif args.run_workflow:
        handle_run_workflow(args)
    elif args.init:
        handle_init(args)
    elif args.lint:
        handle_lint(args)
    elif args.run_debate:
        handle_run_debate(args)
    elif args.chat:
        handle_chat(args)
    elif args.stream:
        handle_stream(args)
    elif args.sync_pap:
        handle_sync_pap(args)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if hasattr(e, "HANDOFF_EXIT_CODE"):
            sys.exit(e.HANDOFF_EXIT_CODE)
        if e.__class__.__name__ == "HandoffRequired":
            sys.exit(42)
        raise e
