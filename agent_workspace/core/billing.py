from datetime import datetime, timezone, timedelta
import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional
from core.ledger import FinancialLedger

logger = logging.getLogger(__name__)


class TenantRateLimitError(Exception):
    """Exception raised when a tenant exceeds their allowed token rate limit."""
    pass


class TenantSubscriptionInactiveError(Exception):
    """Exception raised when a tenant's subscription is frozen or canceled."""
    pass


class QuotaExceededError(Exception):
    """Exception raised when a tenant's credit budget or token quota is exceeded."""
    pass


class TenantQuotaStateUnavailable(RuntimeError):
    pass


class SaaSBillingTracker:
    """
    Platform billing tracker linked to the sqlite3 financial ledger.
    Tracks active token usage and calculates platform billing invoices
    applying a configurable SaaS markup platform fee.
    """
    def __init__(self, ledger: FinancialLedger):
        self.ledger = ledger

    def get_saas_invoice(
        self,
        filter_id: Optional[str] = None,
        markup_multiplier: float = 1.5,
        tenant_id: str = "default_tenant"
    ) -> Dict[str, Any]:
        """
        Calculates itemized invoicing, total token usage, raw cost,
        and platform-markup adjusted billing summaries.
        """
        raw_total_cost = self.ledger.get_total_cost(filter_id, tenant_id=tenant_id)

        raw_records = self.ledger.get_all_records(tenant_id=tenant_id)
        
        # Filter records by session_id or account_id in python if filter_id is supplied
        filtered_records = []
        for r in raw_records:
            if filter_id:
                if r["session_id"] == filter_id or r["account_id"] == filter_id:
                    filtered_records.append(r)
            else:
                filtered_records.append(r)

        total_prompt_tokens = sum(r["prompt_tokens"] for r in filtered_records)
        total_completion_tokens = sum(r["completion_tokens"] for r in filtered_records)
        total_tokens = sum(r["total_tokens"] for r in filtered_records)

        billed_transactions = []
        billed_total_cost = 0.0
        for r in filtered_records:
            br = dict(r)
            br["raw_cost"] = r["cost"]
            # Use transaction's markup_multiplier if recorded, otherwise default parameter
            tx_markup = r.get("markup_multiplier")
            if tx_markup is None:
                tx_markup = markup_multiplier
            br["markup_multiplier"] = tx_markup
            br["billed_cost"] = r["cost"] * tx_markup
            billed_total_cost += br["billed_cost"]
            billed_transactions.append(br)

        return {
            "filter_id": filter_id,
            "markup_multiplier": markup_multiplier,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "raw_cost_usd": raw_total_cost,
            "billed_cost_usd": billed_total_cost,
            "transactions": billed_transactions
        }


class TenantStatusManager:
    """Manages secure reading/writing of subscription status for multi-tenant isolation."""
    def __init__(self, ledger: FinancialLedger):
        self.ledger = ledger

    def update_tenant_status(
        self,
        tenant_id: str,
        status: str,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None
    ) -> None:
        """Stores or updates tenant's subscription status in the SQLite database and logs to AuditLedger."""
        now = datetime.now(timezone.utc).isoformat()
        
        # 1. Fetch old status for change audit comparison
        old_status = "unknown"
        conn = sqlite3.connect(str(self.ledger.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT status FROM tenant_subscription_status WHERE tenant_id = ?", (tenant_id,))
            row = cursor.fetchone()
            if row:
                old_status = row["status"]
            
            # 2. Insert or replace status row
            conn.execute(
                """
                INSERT OR REPLACE INTO tenant_subscription_status (
                    tenant_id, status, stripe_customer_id, stripe_subscription_id, last_updated
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (tenant_id, status, stripe_customer_id, stripe_subscription_id, now)
            )
            conn.commit()
        finally:
            conn.close()

        # 3. Log event to AuditLedger
        from agent_workspace.core.audit_ledger import AuditLedger
            
        try:
            audit = AuditLedger(self.ledger.workspace_path)
            audit.record_event("system_call", {
                "event": "subscription_status_changed",
                "tenant_id": tenant_id,
                "old_status": old_status,
                "new_status": status,
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id
            }, tenant_id="admin_tenant")
        except Exception as e:
            logger.error(f"Failed to record status change to audit ledger: {e}")

    def get_tenant_status(self, tenant_id: str) -> str:
        """Retrieves tenant status. Defaults to 'active' for backward compatibility and onboarding."""
        conn = sqlite3.connect(str(self.ledger.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT status FROM tenant_subscription_status WHERE tenant_id = ?", (tenant_id,))
            row = cursor.fetchone()
            if row:
                return row["status"]
        except sqlite3.Error as e:
            logger.error(f"Error querying tenant status: {e}")
            raise TenantQuotaStateUnavailable("tenant subscription state is unavailable") from e
        finally:
            conn.close()
        return "active"

    def get_tenant_by_stripe_customer(self, customer_id: str) -> Optional[str]:
        """Resolves tenant ID by Stripe customer ID."""
        conn = sqlite3.connect(str(self.ledger.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT tenant_id FROM tenant_subscription_status WHERE stripe_customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            if row:
                return row["tenant_id"]
        finally:
            conn.close()
        return None

    def get_tenant_by_stripe_subscription(self, subscription_id: str) -> Optional[str]:
        """Resolves tenant ID by Stripe subscription ID."""
        conn = sqlite3.connect(str(self.ledger.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT tenant_id FROM tenant_subscription_status WHERE stripe_subscription_id = ?", (subscription_id,))
            row = cursor.fetchone()
            if row:
                return row["tenant_id"]
        finally:
            conn.close()
        return None


class TenantRateLimiter:
    """Enforces token consumption rate limiting per tenant based on subscription status."""
    def __init__(self, ledger: FinancialLedger):
        self.ledger = ledger
        self.status_mgr = TenantStatusManager(ledger)

    def check_rate_limit(self, tenant_id: str) -> None:
        """
        Verifies subscription status and checks dynamic token consumption limit.
        Capped at 5,000 tokens per minute for active tier, 0 for frozen/canceled tiers.
        """
        status = self.status_mgr.get_tenant_status(tenant_id)
        if status in ("frozen", "canceled"):
            raise TenantSubscriptionInactiveError(
                f"Subscription is {status}. Access restricted."
            )

        # Active status - query FinancialLedger for token sum of last 60 seconds
        now = datetime.now(timezone.utc)
        one_minute_ago = (now - timedelta(seconds=60)).isoformat()
        
        conn = sqlite3.connect(str(self.ledger.db_path))
        try:
            cursor = conn.execute(
                "SELECT SUM(total_tokens) FROM financial_ledger WHERE tenant_id = ? AND timestamp >= ?",
                (tenant_id, one_minute_ago)
            )
            row = cursor.fetchone()
            tokens_sum = row[0] if row and row[0] is not None else 0
        except sqlite3.Error as e:
            logger.error(f"Error querying tokens sum for rate limiting: {e}")
            raise TenantQuotaStateUnavailable("tenant token quota state is unavailable") from e
        finally:
            conn.close()

        if tokens_sum >= 5000:
            raise TenantRateLimitError(
                f"Rate Limit Exceeded: Tenant '{tenant_id}' has consumed {tokens_sum} tokens in the last minute. "
                f"Maximum allowed is 5000 tokens/minute."
            )
