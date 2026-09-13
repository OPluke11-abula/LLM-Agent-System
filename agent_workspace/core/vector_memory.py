"""Federated Vector Memory & RAG Knowledge Topology Subsystem (Phase 90).

Provides decentralized, thread-safe vector storage, normalized cosine similarity retrieval,
deterministic Merkle tree topology verification, and cross-peer experience synchronization
for the multi-agent coding pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.embeddings import EmbeddingGenerator, generate_mock_embedding

logger = logging.getLogger("FederatedVectorMemory")


class VectorCategory(str, Enum):
    """Classification taxonomy for federated vector memory entries."""

    DECISION = "DECISION"          # Architectural decision records, trade-offs
    LESSON = "LESSON"              # Post-debate learnings, failure analysis
    PATTERN = "PATTERN"            # Successful implementation & refactoring recipes
    ERROR = "ERROR"                # Security violations, boundary regressions
    CODE_SNIPPET = "CODE_SNIPPET"  # Golden contract examples, test patterns


class VectorMemoryEntry(BaseModel):
    """An immutable, cryptographically verifiable vector memory experience entry."""

    model_config = ConfigDict(extra="allow")

    entry_id: str = Field(default_factory=lambda: f"vec-{uuid.uuid4().hex[:12]}")
    task_id: str
    category: VectorCategory
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)
    content_hash: str = ""
    author_node_id: str = "node-local"
    timestamp: float = Field(default_factory=time.time)

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 digest over the canonical representation."""
        metadata_str = json.dumps(self.metadata, sort_keys=True, ensure_ascii=False)
        raw = (
            f"{self.entry_id}:{self.task_id}:{self.category.value}:"
            f"{self.author_node_id}:{self.content}:{metadata_str}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def ensure_hash(self) -> None:
        """Sets content_hash if empty."""
        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def verify_integrity(self) -> bool:
        """Validates that content_hash matches computed hash."""
        return bool(self.content_hash) and self.content_hash == self.compute_hash()


class VectorSearchResult(BaseModel):
    """Ranked search result from cosine similarity query."""

    entry: VectorMemoryEntry
    similarity: float
    rank: int


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Computes cosine similarity between two float vectors.
    
    If both vectors are already L2-normalized, this is identical to dot product.
    Includes numerical clamping to [-1.0, 1.0].
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a_sq += a * a
        norm_b_sq += b * b

    if norm_a_sq <= 0.0 or norm_b_sq <= 0.0:
        return 0.0

    denom = math.sqrt(norm_a_sq) * math.sqrt(norm_b_sq)
    sim = dot / denom
    return max(-1.0, min(1.0, float(sim)))


class FederatedVectorMemory:
    """Decentralized, thread-safe in-memory vector store with Merkle tree topology verification."""

    def __init__(
        self,
        node_id: str = "node-local",
        embedding_generator: Optional[EmbeddingGenerator] = None,
        embedding_dim: int = 1536,
    ) -> None:
        self.node_id = node_id
        self.embedding_generator = embedding_generator
        self.embedding_dim = embedding_dim
        self._entries: Dict[str, VectorMemoryEntry] = {}
        self._lock = threading.RLock()
        self._cached_merkle_root: Optional[str] = None
        self._is_dirty = True

    def _get_embedding(self, text: str) -> List[float]:
        """Generates embedding using the configured generator or deterministic mock fallback."""
        if self.embedding_generator:
            try:
                return self.embedding_generator.get_embedding(text, dimension=self.embedding_dim)
            except Exception as e:
                logger.warning("Embedding generator failed (%s); falling back to mock embedding", e)
        return generate_mock_embedding(text, dimension=self.embedding_dim)

    def store(
        self,
        task_id: str,
        category: Union[VectorCategory, str],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        author_node_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> VectorMemoryEntry:
        """Stores a new vector memory entry and marks the Merkle topology dirty."""
        if isinstance(category, str):
            category = VectorCategory(category.upper())

        author = author_node_id or self.node_id
        meta = dict(metadata or {})
        t = timestamp or time.time()
        eid = entry_id or f"vec-{uuid.uuid4().hex[:12]}"

        emb = embedding if (embedding and len(embedding) == self.embedding_dim) else self._get_embedding(content)

        entry = VectorMemoryEntry(
            entry_id=eid,
            task_id=task_id,
            category=category,
            content=content,
            metadata=meta,
            embedding=emb,
            author_node_id=author,
            timestamp=t,
        )
        entry.ensure_hash()

        with self._lock:
            self._entries[entry.entry_id] = entry
            self._is_dirty = True

        logger.debug(
            "[VectorMemory] Stored %s entry %s (task=%s, hash=%s...)",
            category.value,
            entry.entry_id,
            task_id,
            entry.content_hash[:8],
        )
        return entry

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[Union[VectorCategory, str]] = None,
        min_similarity: float = 0.0,
    ) -> List[VectorSearchResult]:
        """Searches memory entries by cosine similarity, returning ranked results."""
        if isinstance(category, str):
            category = VectorCategory(category.upper())

        query_vec = self._get_embedding(query)

        candidates: List[Tuple[float, VectorMemoryEntry]] = []
        with self._lock:
            for entry in self._entries.values():
                if category is not None and entry.category != category:
                    continue
                sim = cosine_similarity(query_vec, entry.embedding)
                if sim >= min_similarity:
                    candidates.append((sim, entry))

        # Sort descending by similarity score, then ascending by entry_id for determinism
        candidates.sort(key=lambda x: (x[0], x[1].entry_id), reverse=True)

        results: List[VectorSearchResult] = []
        for idx, (sim, entry) in enumerate(candidates[:top_k], start=1):
            results.append(
                VectorSearchResult(
                    entry=entry,
                    similarity=round(sim, 4),
                    rank=idx,
                )
            )
        return results

    def compute_merkle_root(self) -> str:
        """Computes deterministic Merkle tree root over sorted leaf hashes of all entries."""
        with self._lock:
            if not self._is_dirty and self._cached_merkle_root is not None:
                return self._cached_merkle_root

            if not self._entries:
                self._cached_merkle_root = hashlib.sha256(b"empty_vector_memory").hexdigest()
                self._is_dirty = False
                return self._cached_merkle_root

            # Collect and sort all leaf hashes
            leaves = sorted([e.content_hash for e in self._entries.values()])

            # Pairwise hashing to root
            current_level = leaves
            while len(current_level) > 1:
                next_level: List[str] = []
                for i in range(0, len(current_level), 2):
                    left = current_level[i]
                    right = current_level[i + 1] if i + 1 < len(current_level) else left
                    combined = f"{left}:{right}".encode("utf-8")
                    next_level.append(hashlib.sha256(combined).hexdigest())
                current_level = next_level

            self._cached_merkle_root = current_level[0]
            self._is_dirty = False
            return self._cached_merkle_root

    def get_manifest(self) -> Dict[str, Any]:
        """Returns topology manifest for fast P2P drift detection and synchronization."""
        with self._lock:
            root = self.compute_merkle_root()
            hashes = {eid: entry.content_hash for eid, entry in self._entries.items()}
            return {
                "node_id": self.node_id,
                "merkle_root": root,
                "entry_count": len(self._entries),
                "entry_hashes": hashes,
            }

    def reconcile_delta(self, peer_manifest: Dict[str, Any]) -> List[str]:
        """Identifies entry_ids present in peer_manifest that are missing in local storage."""
        peer_hashes: Dict[str, str] = peer_manifest.get("entry_hashes", {})
        missing_ids: List[str] = []
        with self._lock:
            for eid, p_hash in peer_hashes.items():
                if eid not in self._entries or self._entries[eid].content_hash != p_hash:
                    missing_ids.append(eid)
        return missing_ids

    def get_entries_by_ids(self, entry_ids: Sequence[str]) -> List[VectorMemoryEntry]:
        """Returns a list of entries matching the specified IDs."""
        with self._lock:
            return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def export_entries(self) -> List[Dict[str, Any]]:
        """Exports all memory entries as serializable dictionaries for peer synchronization."""
        with self._lock:
            return [entry.model_dump() for entry in self._entries.values()]

    def merge_entries(
        self,
        entries: Sequence[Union[VectorMemoryEntry, Dict[str, Any]]],
    ) -> Tuple[int, str]:
        """Merges incoming entries from an attested peer, verifying integrity.
        
        Returns (number_of_new_entries_merged, new_merkle_root).
        """
        added_count = 0
        with self._lock:
            for raw in entries:
                if isinstance(raw, dict):
                    entry = VectorMemoryEntry(**raw)
                else:
                    entry = raw

                # Validate cryptographic integrity
                entry.ensure_hash()
                if not entry.verify_integrity():
                    logger.warning("Skipping entry %s with invalid content_hash", entry.entry_id)
                    continue

                if entry.entry_id not in self._entries:
                    self._entries[entry.entry_id] = entry
                    added_count += 1
                    self._is_dirty = True
                elif self._entries[entry.entry_id].content_hash != entry.content_hash:
                    # Last-write-wins by timestamp on ID collision
                    if entry.timestamp > self._entries[entry.entry_id].timestamp:
                        self._entries[entry.entry_id] = entry
                        added_count += 1
                        self._is_dirty = True

            new_root = self.compute_merkle_root()

        logger.info(
            "[VectorMemory] Merged %d new entries. New Merkle Root: %s",
            added_count,
            new_root[:8],
        )
        return added_count, new_root

    def get_entries(self, limit: int = 50, category: Optional[str] = None) -> List[VectorMemoryEntry]:
        """Returns entries up to limit, sorted newest first."""
        cat_enum = VectorCategory(category.upper()) if category else None
        with self._lock:
            all_entries = list(self._entries.values())
        if cat_enum:
            all_entries = [e for e in all_entries if e.category == cat_enum]
        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistical telemetry on vector memory distribution."""
        with self._lock:
            category_counts: Dict[str, int] = {}
            for e in self._entries.values():
                c_name = e.category.value
                category_counts[c_name] = category_counts.get(c_name, 0) + 1

            return {
                "node_id": self.node_id,
                "total_entries": len(self._entries),
                "merkle_root": self.compute_merkle_root(),
                "embedding_dimension": self.embedding_dim,
                "category_breakdown": category_counts,
            }
