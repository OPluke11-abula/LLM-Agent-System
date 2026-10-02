---
tags:
  - architecture/leaf
  - frontend/admin
  - multi_tenant/audit
  - layer/l1
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.AdminDashboardView
file_path: viewer/src/components/AdminDashboardView.tsx
sync_status: verified
---

# Module: AdminDashboardView (Multi-Tenant Management & Interceptor Console)

## 1. Three-Line Architectural Annotation
- **Responsibility**: System administration portal managing multi-tenant billing tiers, live event interceptors, RBAC policy assignments, and audit ledger inspections.
- **Invariant**: Admin actions (tenant suspension, credit override, certificate revocation) require explicit confirmation modals with typed password authentication.
- **Data Flow**: Connects to `SaaSBillingTracker`, `AuditLedger`, and `UnifiedPolicyGate`, rendering real-time metrics and audit table logs.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`AdminDashboardView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/AdminDashboardView.tsx) (1150 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `AdminDashboardView` | `function` | L792-L796 | Top-level administration dashboard component. |
| `useAdminDashboardController` | `hook` | L346-L790 | Controller fetching tenant usage statistics, interceptor rules, and audit logs. |
| `TenantBillingSection` | `component` | L853-L965 | Invoices table, Stripe subscription status cards, and credit quota management. |
| `LiveInterceptorSection` | `component` | L968-L1090 | Real-time packet inspector intercepting agent-to-agent messages and tool payloads. |
| `AuditLedgerSection` | `component` | L1092-L1150 | Searchable event ledger table displaying SHA256 hashes, timestamps, and proof links. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **CSRF Protection**: All mutating admin operations send custom anti-CSRF request headers verified by the backend gateway.
2. **Audit Trail of Admin Actions**: Any admin modification automatically writes an immutable event into `AuditLedger`.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite build validated clean exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Backend Counterparts**:
  - [[core-billing]]
  - [[core-audit-ledger]]
  - [[core-policy-gate]]
