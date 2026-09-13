---
tags:
  - architecture/leaf
  - security/mtls
  - pki/certificates
  - layer/l5
type: module_leaf
layer: L5-Security-Sandbox-and-Merkle
module: agent_workspace.core.cert_manager
file_path: agent_workspace/core/cert_manager.py
sync_status: verified
---

# Module: SwarmCertManager (mTLS Public Key Infrastructure & Rotations)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Provisions self-signed X.509 certificates, computes cryptographic fingerprints, signs inter-node payloads, and validates mutual TLS (mTLS) identities.
- **Invariant**: Expired certificates or fingerprints listed on the revocation list in `AuditLedger` are strictly rejected during TLS handshake.
- **Data Flow**: Generates RSA/ECDSA keypairs, exports PEM-encoded certificates for node tunnels, and verifies signatures on peer gossip announcements.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`cert_manager.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/cert_manager.py) (114 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `SwarmCertManager` | `class` | L13-L114 | PKI manager for swarm node authentication and certificate lifecycle. |
| `generate_self_signed_cert` | `def` | L15-L67 | Generates self-signed X.509 certificate and private key with SAN extensions. |
| `get_cert_fingerprint` | `def` | L70-L79 | Computes SHA256 hex digest fingerprint of a PEM certificate. |
| `sign_payload` | `def` | L82-L96 | Cryptographically signs an arbitrary bytes payload using node private key. |
| `verify_signature` | `def` | L99-L114 | Validates cryptographic signature against peer public certificate. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Automated Rotation**: Certificates nearing expiration (< 24 hours remaining) trigger automated rotation routines.
2. **Immediate Revocation Enforcement**: Revocation checks query `is_certificate_revoked` synchronously before granting socket connections.

---

## 4. Verification & Test Evidence
- **Test Suites**:
  - [`test_mtls_rotation.py`](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_mtls_rotation.py)
- **Execution Receipt**: Bytecode validated via `compileall` exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L5-Security-Sandbox-and-Merkle]]
- **Collaborating Modules**:
  - [[core-p2p-router]]
  - [[core-audit-ledger]]
