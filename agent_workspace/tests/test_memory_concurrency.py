import os
import sys
import tempfile
import concurrent.futures
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from memory_backends import SQLiteBackend

def test_sqlite_concurrency():
    """Verify that multiple concurrent threads writing to SQLiteBackend does not cause locks or failures."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_concurrency.db"
        backend = SQLiteBackend(db_path)
        
        session_id = "concurrent-session"
        num_threads = 25
        num_writes_per_thread = 10
        
        def worker(thread_idx):
            try:
                for write_idx in range(num_writes_per_thread):
                    key = f"key-{thread_idx}-{write_idx}"
                    value = {
                        "summary": f"Summary for thread {thread_idx} write {write_idx}",
                        "keywords": [f"t{thread_idx}", f"w{write_idx}"]
                    }
                    backend.write(session_id, key, value)
                    
                    # Verify immediately
                    read_val = backend.read(session_id, key)
                    assert read_val == value
            finally:
                backend.close()
                
        # Execute workers in parallel using thread executor
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, idx) for idx in range(num_threads)]
            
            # Raise any thread exceptions
            for fut in concurrent.futures.as_completed(futures):
                fut.result()
                
        # Verify total records in backend
        all_recs = backend.all_records()
        assert len(all_recs) == num_threads * num_writes_per_thread
        
        # Verify search works under concurrent entries
        search_res = backend.search("Summary")
        assert len(search_res) > 0
        
        # Close all connections across all threads so file can be unlinked
        backend.close_all()
