import os
import sys
import time
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from observability import ConcurrencyBalancer, get_global_balancer


def test_concurrency_balancer_offload_routing():
    # Initialize a balancer with custom workers
    balancer = ConcurrencyBalancer(max_heavy_workers=2, max_telemetry_workers=2)
    
    def dummy_task(duration, result):
        time.sleep(duration)
        return result

    # Offload to heavy pool
    future1 = balancer.offload(dummy_task, "heavy", 0.05, "heavy_res")
    # Offload to telemetry pool
    future2 = balancer.offload(dummy_task, "telemetry", 0.05, "telemetry_res")
    
    # Wait for execution and verify results
    assert future1.result() == "heavy_res"
    assert future2.result() == "telemetry_res"
    
    balancer.shutdown(wait=True)


def test_concurrency_balancer_dynamic_load_balancing():
    # Establish tight limits to force capacity adjustment
    balancer = ConcurrencyBalancer(max_heavy_workers=2, max_telemetry_workers=2)
    
    # Verify defaults
    assert balancer.heavy_pool._max_workers == 2
    assert balancer.telemetry_pool._max_workers == 2
    
    # Block heavy threads
    blockers = []
    
    # Submit more than max heavy tasks to trigger balancing load adjust
    # Since telemetry pool has 0 active tasks, heavy capacity should dynamically expand!
    for i in range(5):
        fut = balancer.offload(time.sleep, "heavy", 0.2)
        blockers.append(fut)
        
    # Wait a small duration for threads to activate and trigger balance_loads
    time.sleep(0.05)
    
    # Check that heavy capacity has expanded (max heavy expanded to min(16, self.max_heavy + 4) -> 6)
    # and telemetry capacity has shrunk
    assert balancer.heavy_pool._max_workers == 6
    assert balancer.telemetry_pool._max_workers == 2  # max(2, telemetry - 2) -> 2
    
    # Let tasks complete
    for fut in blockers:
        fut.result()
        
    # Now that active tasks are 0, they should restore to defaults
    time.sleep(0.05)
    assert balancer.heavy_pool._max_workers == 2
    assert balancer.telemetry_pool._max_workers == 2
    
    balancer.shutdown(wait=True)


def test_global_balancer_singleton():
    balancer1 = get_global_balancer()
    balancer2 = get_global_balancer()
    assert balancer1 is balancer2
    assert isinstance(balancer1, ConcurrencyBalancer)
