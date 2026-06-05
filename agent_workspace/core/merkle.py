import hashlib
from typing import List

class MerkleTree:
    """
    Deterministic binary Merkle Tree implementation for auditing and proving
    consistency of audit ledger states.
    """
    def __init__(self, leaves: List[str]):
        """
        leaves: A list of hash strings representing individual audit ledger events.
        """
        self.leaves = leaves
        self.root = self._build_tree(leaves)

    def _build_tree(self, leaves: List[str]) -> str:
        if not leaves:
            return "0" * 64
        
        # Hash each leaf once to prevent second-preimage attacks
        current_level = [hashlib.sha256(leaf.encode("utf-8")).hexdigest() for leaf in leaves]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # Duplicate last element if odd
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent_hash)
            current_level = next_level
            
        return current_level[0]
