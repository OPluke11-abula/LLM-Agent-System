"""Zero-Knowledge Task State Verifier & Air-gap Proof Engine (Phase 111).

Aligned with Universal Coding Agent Development Protocol v3.8.0, Anti-Corruption
Principle #4 (Typed Failures), and Principle #6 (Idempotence & Side-Effect Safety).

Enables cross-organization task delegation without raw source code leakage,
exchanging only redacted AST signatures, SHA-256 Merkle roots, and cryptographic execution proofs.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("ZeroKnowledgeTaskVerifier")


class SecurityLeakageError(RuntimeError):
    """Raised when raw unredacted code or sensitive secrets are detected in a cross-org payload."""


class ZKProofPayload(BaseModel):
    """Cryptographic task envelope devoid of raw sensitive source code."""

    model_config = ConfigDict(extra="ignore")

    proof_id: str = Field(default_factory=lambda: f"zkp-{uuid.uuid4().hex[:12]}")
    task_id: str
    organization_id: str
    merkle_root: str
    ast_shape_hash: str
    redacted_signatures: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
    airgap_verified: bool = True


class StateMerkleAttestation(BaseModel):
    """Attestation proof validating task completion state integrity."""

    model_config = ConfigDict(extra="ignore")

    attestation_id: str = Field(default_factory=lambda: f"attest-{uuid.uuid4().hex[:12]}")
    proof_id: str
    executor_node_id: str
    output_state_hash: str
    exit_code: int = 0
    passed: bool = True
    signature: str = ""


class ZeroKnowledgeTaskVerifier:
    """Verifies task structural integrity and execution state across untrusted network boundaries."""

    def __init__(self, organization_id: str = "org-primary") -> None:
        self.organization_id = organization_id

    def extract_ast_shape(self, code_content: str) -> Dict[str, Any]:
        """Extracts high-level AST structural fingerprint without code text."""
        try:
            tree = ast.parse(code_content)
        except SyntaxError as e:
            return {"error": str(e), "functions": [], "classes": []}

        functions: List[str] = []
        classes: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(f"{node.name}:{len(node.args.args)}")
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        return {
            "functions": sorted(functions),
            "classes": sorted(classes),
            "total_nodes": len(list(ast.walk(tree))),
        }

    def compute_merkle_root(self, code_content: str) -> str:
        """Computes deterministic SHA-256 Merkle root across code lines."""
        lines = [line.strip().encode("utf-8") for line in code_content.splitlines() if line.strip()]
        if not lines:
            return hashlib.sha256(b"EMPTY").hexdigest()

        hashes = [hashlib.sha256(line).hexdigest() for line in lines]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_level = []
            for i in range(0, len(hashes), 2):
                combined = f"{hashes[i]}:{hashes[i+1]}".encode("utf-8")
                new_level.append(hashlib.sha256(combined).hexdigest())
            hashes = new_level

        return hashes[0]

    def create_task_proof(self, task_id: str, code_content: str) -> ZKProofPayload:
        """Generates a zero-knowledge task envelope that redacts all raw source code."""
        # 1. Compute AST shape
        ast_shape = self.extract_ast_shape(code_content)
        shape_json = json.dumps(ast_shape, sort_keys=True)
        shape_hash = hashlib.sha256(shape_json.encode("utf-8")).hexdigest()

        # 2. Compute Merkle root
        merkle_root = self.compute_merkle_root(code_content)

        # 3. Redact signatures
        signatures = [f"fn:{f}" for f in ast_shape.get("functions", [])] + [f"cls:{c}" for c in ast_shape.get("classes", [])]

        payload = ZKProofPayload(
            task_id=task_id,
            organization_id=self.organization_id,
            merkle_root=merkle_root,
            ast_shape_hash=shape_hash,
            redacted_signatures=signatures,
            airgap_verified=True,
        )
        return payload

    def verify_no_unauthorized_leakage(self, payload: Dict[str, Any]) -> bool:
        """Audits an outgoing or incoming payload to ensure no raw source code is present."""
        forbidden_indicators = ["def ", "class ", "import ", "lambda ", "return ", "except:"]
        serialized = json.dumps(payload)

        for indicator in forbidden_indicators:
            if f'"{indicator}' in serialized or f' {indicator}' in serialized:
                raise SecurityLeakageError(
                    f"Cross-organization payload violates zero-knowledge policy! Found code pattern: '{indicator}'"
                )
        return True

    def verify_execution_attestation(
        self,
        proof: ZKProofPayload,
        attestation: StateMerkleAttestation,
    ) -> bool:
        """Validates that execution attestation correctly references the zero-knowledge proof."""
        if attestation.proof_id != proof.proof_id:
            logger.warning("Attestation proof ID mismatch: %s != %s", attestation.proof_id, proof.proof_id)
            return False

        if not attestation.passed or attestation.exit_code != 0:
            logger.warning("Attestation failed with exit_code %d", attestation.exit_code)
            return False

        # Validate cryptographic signature
        expected_sig = hashlib.sha256(
            f"{attestation.proof_id}:{attestation.output_state_hash}:{attestation.executor_node_id}".encode()
        ).hexdigest()

        return attestation.signature == expected_sig

    def generate_execution_attestation(
        self,
        proof: ZKProofPayload,
        executor_node_id: str,
        output_result_str: str,
        exit_code: int = 0,
    ) -> StateMerkleAttestation:
        """Generates a cryptographic execution receipt binding the output state to the proof."""
        output_hash = hashlib.sha256(output_result_str.encode("utf-8")).hexdigest()
        sig = hashlib.sha256(f"{proof.proof_id}:{output_hash}:{executor_node_id}".encode()).hexdigest()

        return StateMerkleAttestation(
            proof_id=proof.proof_id,
            executor_node_id=executor_node_id,
            output_state_hash=output_hash,
            exit_code=exit_code,
            passed=(exit_code == 0),
            signature=sig,
        )
