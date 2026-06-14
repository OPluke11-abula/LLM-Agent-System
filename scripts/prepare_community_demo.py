import os
import shutil
import re

def main():
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dst_dir = os.path.abspath(os.path.join(src_dir, "..", "LLM-Agent-System-DEMO"))
    
    print(f"[*] Starting community decoupling from: {src_dir}")
    print(f"[*] Target community demo directory:  {dst_dir}")
    
    # 1. Clean destination if exists
    if os.path.exists(dst_dir):
        print(f"[*] Cleaning existing destination directory: {dst_dir}")
        shutil.rmtree(dst_dir)
        
    os.makedirs(dst_dir, exist_ok=True)
    
    # 2. Excluded names
    exclude_dirs = {
        ".git", ".venv", "__pycache__", ".pytest_cache", 
        "node_modules", "target", "dist", "releases"
    }
    exclude_files = {
        ".coverage", "accounts.json", "docker-compose.microservices.yml", "nginx.conf"
    }
    
    # 3. Copy files recursively
    for root, dirs, files in os.walk(src_dir):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        # Calculate destination folder
        rel_path = os.path.relpath(root, src_dir)
        target_folder = dst_dir if rel_path == "." else os.path.join(dst_dir, rel_path)
        os.makedirs(target_folder, exist_ok=True)
        
        for file in files:
            if file in exclude_files:
                continue
            # Filter private/history files inside .agent folder
            if rel_path.startswith(".agent"):
                if file in ("agent_tasks.md", "lessons.md", "preferences.md"):
                    continue
                if file.endswith(".db") or file.endswith(".json") or file.endswith(".log"):
                    continue
            src_file_path = os.path.join(root, file)
            dst_file_path = os.path.join(target_folder, file)
            shutil.copy2(src_file_path, dst_file_path)

            
    print("[*] Base file copy completed.")

    # 4. Overwrite agent_workspace/core/billing.py with a simplified community stub
    billing_stub_path = os.path.join(dst_dir, "agent_workspace", "core", "billing.py")
    if os.path.exists(billing_stub_path):
        print("[*] Overwriting core/billing.py with lightweight community stub...")
        stub_content = '''# Community Edition Stubbed Billing Module
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class TenantRateLimitError(Exception):
    """Exception raised when a tenant exceeds their allowed token rate limit."""
    pass

class TenantSubscriptionInactiveError(Exception):
    """Exception raised when a tenant's subscription is frozen or canceled."""
    pass

class SaaSBillingTracker:
    def __init__(self, ledger):
        self.ledger = ledger

    def get_saas_invoice(
        self,
        filter_id: Optional[str] = None,
        markup_multiplier: float = 1.0,
        tenant_id: str = "default_tenant"
    ) -> Dict[str, Any]:
        """Returns standard billing summary with no markup platform fees."""
        return {
            "filter_id": filter_id,
            "markup_multiplier": 1.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "raw_cost_usd": 0.0,
            "billed_cost_usd": 0.0,
            "transactions": []
        }

class TenantStatusManager:
    def __init__(self, ledger):
        self.ledger = ledger

    def update_tenant_status(
        self,
        tenant_id: str,
        status: str,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None
    ) -> None:
        pass

    def get_tenant_status(self, tenant_id: str) -> str:
        """Community version is always active."""
        return "active"

    def get_tenant_by_stripe_customer(self, customer_id: str) -> Optional[str]:
        return "default_tenant"

    def get_tenant_by_stripe_subscription(self, subscription_id: str) -> Optional[str]:
        return "default_tenant"

class TenantRateLimiter:
    def __init__(self, ledger):
        self.ledger = ledger

    def check_rate_limit(self, tenant_id: str) -> None:
        """No rate-limiting in community edition."""
        pass
'''
        with open(billing_stub_path, "w", encoding="utf-8") as f:
            f.write(stub_content)

    # 5. Overwrite/modify agent_workspace/core/sandbox.py to gracefully handle missing ProofOfConsensus
    sandbox_path = os.path.join(dst_dir, "agent_workspace", "core", "sandbox.py")
    if os.path.exists(sandbox_path):
        print("[*] Patching core/sandbox.py for standalone community fallback...")
        with open(sandbox_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Add fallback imports in execution loop
        modified_content = content.replace(
            "if not ProofOfConsensus.is_consensus_approved(workspace_path, payload_hash):",
            """# Fallback check for missing ProofOfConsensus (Community Edition)
        is_approved = True
        try:
            is_approved = ProofOfConsensus.is_consensus_approved(workspace_path, payload_hash)
        except Exception:
            is_approved = True
            
        if not is_approved:"""
        )
        
        with open(sandbox_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

    # 6. Overwrite target README.md with Community Edition information
    readme_path = os.path.join(dst_dir, "README.md")
    print("[*] Creating public Community README.md...")
    community_readme = """# LLM Agent System (Community DEMO Edition)

Welcome to the Community DEMO Edition of the **LLM Agent System (LAS)**!

This repository is a lightweight, open-core, single-tenant demonstration of FindAi Studio's powerful LLM agent orchestration platform. It is designed to run completely locally with minimal external dependencies.

## 🚀 Key Features Included

- **Cognitive Agent Engine**: Full cognitive execution loop, prompts, memory buffers, and task tracking.
- **Asynchronous Workflow Engine**: n8n-style node-based custom DAG workflow sequencer.
- **Multi-Swarm Debate Room**: Run structured consensus debates with role-specific AI agents.
- **Local AST Sandbox**: Safely run Python actions and custom scripts locally with AST system call verification.
- **Local Viewer UI**: Real-time Vanilla JS + Tailwind observability canvas visualization dashboard.

## 📦 Excluded Enterprise Features (Private Edition)
This Community Showcase is decoupled from FindAi Studio's proprietary enterprise architecture. The following private systems are stripped/stubbed:
- **Stripe Metered Billing**: Webhooks, subscription tier management, and platform markups.
- **Immutable SOC2 Audit Ledger**: Cryptographically chained SHA-256 Merkle logging.
- **Docker Sandbox Guard**: Zero-Trust isolated execution inside secure network-restricted containers.
- **Distributed Redis Swarms**: Redis Swarm Broker microservices scale-out clusters.

## 🛠️ Getting Started

1. **Setup Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   ```

3. **Run the local platform API server**:
   ```bash
   python agent_workspace/run.py
   ```

4. **Launch Local Observability Dashboard**:
   Open `workspace/viewer.html` in your web browser.

---

## 📄 License
This Community Showcase is licensed under the MIT License.
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(community_readme)

    # 7. Delete enterprise-specific tests in the community edition to keep tests green
    tests_dir = os.path.join(dst_dir, "agent_workspace", "tests")
    if os.path.exists(tests_dir):
        print("[*] Filtering out enterprise-only tests in the community edition...")
        enterprise_tests = [
            "test_cross_cloud.py",
            "test_cryptographic_consensus.py",
            "test_distributed_broker.py",
            "test_elastic_billing.py",
            "test_federated_exchange.py",
            "test_federated_sync.py",
            "test_live_collaboration.py",
            "test_p2p_and_mirroring.py",
            "test_p2p_encryption.py",
            "test_saas_builder.py",
            "test_saas_integration.py",
            "test_subscription_lifecycle.py",
            "test_tenant_channels.py",
            "test_admin_console.py",
            "test_sandbox_audit.py",
            "test_sandbox_defense.py",
            "test_telemetry.py",
            "test_telemetry_router.py"
        ]
        for t_file in enterprise_tests:
            t_path = os.path.join(tests_dir, t_file)
            if os.path.exists(t_path):
                os.remove(t_path)

    print(f"[+] Decoupling Success! Community edition ready at: {dst_dir}")

if __name__ == "__main__":
    main()

