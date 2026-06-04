from typing import Any, Dict, List, Optional
from core.ledger import FinancialLedger

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
        billed_total_cost = raw_total_cost * markup_multiplier

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
        for r in filtered_records:
            br = dict(r)
            br["raw_cost"] = r["cost"]
            br["billed_cost"] = r["cost"] * markup_multiplier
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
