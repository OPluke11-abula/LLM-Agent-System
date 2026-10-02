import os
import sys
import time
import asyncio
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from observability import EventLoopBottleneckProfiler
from core.workflow_engine import WorkflowEngine
from core.engine import AgentEngine


@pytest.mark.asyncio
async def test_event_loop_stutter_detection():
    """Verify that EventLoopBottleneckProfiler successfully detects event loop stutters > 50ms."""
    # Initialize profiler with very tight check interval (5ms) and threshold (20ms)
    profiler = EventLoopBottleneckProfiler(check_interval_ms=5, stutter_threshold_ms=20)
    profiler.start(asyncio.get_running_loop())
    
    try:
        # Wait a brief moment to let monitor loop run
        await asyncio.sleep(0.01)
        
        # Block the event loop synchronously for 40ms to induce stutter
        time.sleep(0.04)
        
        # Let monitor process the stutter
        await asyncio.sleep(0.02)
        
        assert len(profiler.stutters) >= 1
        assert profiler.stutters[0]["type"] == "event_loop_stutter"
        assert profiler.stutters[0]["stutter_ms"] > 20
    finally:
        profiler.stop()


@pytest.mark.asyncio
async def test_sync_blocking_call_profiling():
    """Verify that ProfilingThreadPoolExecutor profiles sync blocking calls > 50ms with function context."""
    profiler = EventLoopBottleneckProfiler(check_interval_ms=10, stutter_threshold_ms=20)
    profiler.start(asyncio.get_running_loop())
    
    try:
        def slow_sync_fn(seconds):
            time.sleep(seconds)
            return "ok"
            
        loop = asyncio.get_running_loop()
        # Execute sync function taking 30ms (which is > threshold of 20ms)
        result = await loop.run_in_executor(
            profiler.executor,
            slow_sync_fn,
            0.03
        )
        
        assert result == "ok"
        assert len(profiler.sync_calls) == 1
        assert profiler.sync_calls[0]["type"] == "sync_blocking_call"
        assert "slow_sync_fn" in profiler.sync_calls[0]["function"]
        assert profiler.sync_calls[0]["duration_ms"] > 20
    finally:
        profiler.stop()


@pytest.mark.asyncio
async def test_dynamic_concurrency_scaling():
    """Verify that thread pool capacity and WorkflowEngine concurrency scale down on stutters and up on clean runs."""
    profiler = EventLoopBottleneckProfiler(check_interval_ms=10, stutter_threshold_ms=20)
    
    # Mock a WorkflowEngine
    mock_engine = MagicMock()
    mock_engine.max_concurrent_tasks = 5
    
    profiler.start(asyncio.get_running_loop())
    profiler.register_engine(mock_engine)
    
    try:
        # Initial max workers should be 4
        assert profiler.executor._max_workers == 4
        
        # 1. Induce a stutter
        profiler.record_sync_call(lambda: None, 0.05) # takes 50ms > 20ms
        
        # Verify capacities scaled down
        assert profiler.executor._max_workers == 3
        assert mock_engine.max_concurrent_tasks == 4
        
        # 2. Trigger tune_concurrency under clean conditions (no recent stutters)
        # Manually clear recent timestamps or stub them to simulate time passed
        profiler.sync_calls = []
        profiler.stutters = []
        
        profiler.tune_concurrency()
        
        # Verify capacities scaled back up
        assert profiler.executor._max_workers == 4
        assert mock_engine.max_concurrent_tasks == 5
    finally:
        profiler.stop()
