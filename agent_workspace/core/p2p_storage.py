import os
import math
import hashlib
import json
from pathlib import Path
from typing import Any

class P2PFileChunkDistributor:
    """Splits large datasets/logs into chunks distributed across tenant folders with SHA256 integrity verification."""
    
    def __init__(self, tenant_dirs: list[str | Path]):
        self.tenant_dirs = [Path(d) for d in tenant_dirs]
        for d in self.tenant_dirs:
            d.mkdir(parents=True, exist_ok=True)

    def distribute_file(self, source_file_path: str | Path, chunk_size_bytes: int, filename_prefix: str = "chunk") -> dict[str, Any]:
        """Splits source_file into chunks and distributes them round-robin across tenant directories.
        Returns a manifest containing checksums and location mapping.
        """
        source_path = Path(source_file_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file {source_file_path} does not exist.")
            
        file_bytes = source_path.read_bytes()
        total_size = len(file_bytes)
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        num_chunks = math.ceil(total_size / chunk_size_bytes) if total_size > 0 else 1
        chunks_info = []
        
        for idx in range(num_chunks):
            start = idx * chunk_size_bytes
            end = min(start + chunk_size_bytes, total_size)
            chunk_data = file_bytes[start:end]
            
            chunk_hash = hashlib.sha256(chunk_data).hexdigest()
            chunk_name = f"{filename_prefix}_{idx}_{chunk_hash[:8]}.bin"
            
            # Select target tenant dir round-robin
            tenant_dir = self.tenant_dirs[idx % len(self.tenant_dirs)]
            target_path = tenant_dir / chunk_name
            target_path.write_bytes(chunk_data)
            
            chunks_info.append({
                "index": idx,
                "name": chunk_name,
                "size": len(chunk_data),
                "sha256": chunk_hash,
                "tenant_dir": str(tenant_dir.resolve())
            })
            
        manifest = {
            "original_filename": source_path.name,
            "original_size": total_size,
            "original_sha256": file_hash,
            "chunk_size": chunk_size_bytes,
            "chunks": chunks_info
        }
        
        return manifest

    def reassemble_file(self, manifest: dict[str, Any], output_file_path: str | Path) -> bool:
        """Reads chunks from metadata manifest, verifies SHA256 integrity, reassembles and validates the full file.
        Raises ValueError if tampering or corruption is detected.
        """
        chunks_info = manifest.get("chunks", [])
        # Re-sort to make sure index order is correct
        chunks_info = sorted(chunks_info, key=lambda c: c["index"])
        
        assembled_data = bytearray()
        
        for chunk in chunks_info:
            idx = chunk["index"]
            name = chunk["name"]
            expected_hash = chunk["sha256"]
            tenant_dir_path = Path(chunk["tenant_dir"])
            
            chunk_file = tenant_dir_path / name
            if not chunk_file.is_file():
                raise FileNotFoundError(f"Missing chunk {idx} at {chunk_file}. Tampering or chunk loss detected.")
                
            chunk_bytes = chunk_file.read_bytes()
            actual_hash = hashlib.sha256(chunk_bytes).hexdigest()
            
            if actual_hash != expected_hash:
                raise ValueError(f"Integrity check failed for chunk {idx}. Expected {expected_hash}, got {actual_hash}. Possible tampering!")
                
            assembled_data.extend(chunk_bytes)
            
        final_bytes = bytes(assembled_data)
        final_hash = hashlib.sha256(final_bytes).hexdigest()
        expected_final_hash = manifest["original_sha256"]
        
        if final_hash != expected_final_hash:
            raise ValueError(f"Full file integrity check failed. Expected {expected_final_hash}, got {final_hash}. File corrupted!")
            
        out_path = Path(output_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(final_bytes)
        return True
