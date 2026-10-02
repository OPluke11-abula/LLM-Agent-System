"""Unit and integration tests for Edge SLM & Local Coding Model Subsystem (Phase 110).

Validates EdgeSLMEngine mock completion, OfflineASTAnalyzer static defect detection
and test stub synthesis, SmartModelDispatcher complexity routing, and MeshFactoryDispatcher
routing to PeerCapability.EDGE_SLM.
"""

import ast
import pytest
from unittest.mock import AsyncMock, patch

from agent_workspace.core.factory.models import (
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.factory.mesh_dispatcher import MeshFactoryDispatcher
from agent_workspace.core.federated_mesh import PeerCapability
from agent_workspace.core.slm import (
    ASTDefectItem,
    EdgeSLMEngine,
    EdgeSLMResponse,
    ModelRouteTarget,
    OfflineAnalysisResult,
    OfflineASTAnalyzer,
    RoutingDecision,
    SmartModelDispatcher,
)


# --- Test Fixtures & Code Snippets ---

SIMPLE_SNIPPET = """
def calculate_sum(a: int, b: int) -> int:
    \"\"\"Calculates sum of two integers.\"\"\"
    return a + b
"""

BARE_EXCEPT_SNIPPET = """
def process_record(data: dict):
    try:
        val = data["key"]
    except:
        val = None
    return val
"""

MISSING_DOCSTRING_SNIPPET = """
def public_worker(x: int) -> int:
    return x * 2

def _private_worker(y: int) -> int:
    return y + 1
"""

HIGH_COMPLEXITY_SNIPPET = """
def complex_decision_matrix(a, b, c, d, e, f, g, h, items):
    \"\"\"Function with high cyclomatic complexity (CC > 10).\"\"\"
    total = 0
    if a and b:
        total += 1
    elif c or d:
        total += 2
    if e:
        for x in items:
            if x > 10 and f:
                total += x
            elif x < 0 or g:
                total -= x
            else:
                total += 1
    while h > 0:
        if h % 2 == 0:
            total += 1
        h -= 1
    return total
"""

SYNTAX_ERROR_SNIPPET = """
def broken_syntax(:
    return 42
"""


# --- EdgeSLMEngine Tests ---

@pytest.mark.asyncio
async def test_edge_slm_engine_mock_generation():
    """Verify EdgeSLMEngine generates completions correctly using hermetic mock handler."""
    def mock_fn(prompt: str, sys: str) -> str:
        return f"# Fixed Code\ndef fixed_fn(): pass"

    engine = EdgeSLMEngine(mock_handler=mock_fn)
    assert await engine.health_check() is True

    response = await engine.generate_completion(prompt="Fix this syntax error")
    assert isinstance(response, EdgeSLMResponse)
    assert response.content == "# Fixed Code\ndef fixed_fn(): pass"
    assert response.is_offline_mock is True
    assert response.cloud_egress_prevented is True
    assert response.latency_ms >= 0.0
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0


@pytest.mark.asyncio
async def test_edge_slm_engine_unreachable_endpoint():
    """Verify EdgeSLMEngine health check and error propagation when offline and no mock."""
    engine = EdgeSLMEngine(base_url="http://127.0.0.1:99999", mock_handler=None)
    is_healthy = await engine.health_check()
    assert is_healthy is False

    with pytest.raises(RuntimeError) as exc_info:
        await engine.generate_completion("Test prompt")
    assert "Edge SLM endpoint unreachable" in str(exc_info.value)


# --- OfflineASTAnalyzer Tests ---

def test_offline_ast_analyzer_clean_code():
    """Verify OfflineASTAnalyzer processes clean code with zero defects."""
    analyzer = OfflineASTAnalyzer()
    result = analyzer.audit_source(SIMPLE_SNIPPET, file_path="clean.py")

    assert isinstance(result, OfflineAnalysisResult)
    assert result.has_bare_except is False
    assert result.missing_docstrings_count == 0
    assert "calculate_sum" in result.functions_found
    assert len(result.defects) == 0
    assert result.cloud_egress is False


def test_offline_ast_analyzer_detects_bare_except():
    """Verify Anti-Corruption Principle #4: bare except is flagged as ERROR."""
    analyzer = OfflineASTAnalyzer()
    result = analyzer.audit_source(BARE_EXCEPT_SNIPPET, file_path="bare.py")

    assert result.has_bare_except is True
    bare_defects = [d for d in result.defects if d.rule_id == "ANTI-CORRUPTION-TYPED-FAILURES"]
    assert len(bare_defects) == 1
    assert bare_defects[0].severity == "ERROR"
    assert "Bare 'except:'" in bare_defects[0].message


def test_offline_ast_analyzer_detects_missing_docstrings():
    """Verify missing docstrings on public functions are detected with INFO severity."""
    analyzer = OfflineASTAnalyzer()
    result = analyzer.audit_source(MISSING_DOCSTRING_SNIPPET, file_path="docstrings.py")

    assert result.missing_docstrings_count == 1
    doc_defects = [d for d in result.defects if d.rule_id == "DOCSTRING-MISSING"]
    assert len(doc_defects) == 1
    assert "public_worker" in doc_defects[0].message


def test_offline_ast_analyzer_syntax_error_handling():
    """Verify syntax errors are gracefully caught as ASTDefectItem with ERROR severity."""
    analyzer = OfflineASTAnalyzer()
    result = analyzer.audit_source(SYNTAX_ERROR_SNIPPET, file_path="syntax_err.py")

    assert len(result.defects) >= 1
    syntax_defects = [d for d in result.defects if d.rule_id == "AST-SYNTAX-ERR"]
    assert len(syntax_defects) == 1
    assert syntax_defects[0].severity == "ERROR"


def test_offline_ast_analyzer_generates_valid_test_stubs():
    """Verify test stub synthesis generates valid, parsable pytest Python source."""
    sample_code = """
class UserService:
    def authenticate(self, username: str) -> bool:
        return True

def standalone_helper(token: str) -> str:
    return token.strip()
"""
    analyzer = OfflineASTAnalyzer()
    stubs = analyzer.generate_test_stubs(sample_code, module_name="auth_service")

    assert "class TestUserService:" in stubs
    assert "def test_userservice_initialization(self):" in stubs
    assert "def test_standalone_helper_baseline_execution():" in stubs

    # Generated Python code must be syntactically valid
    parsed_tree = ast.parse(stubs)
    assert parsed_tree is not None


@pytest.mark.asyncio
async def test_offline_ast_analyzer_propose_quick_fix():
    """Verify quick fix proposal queries Edge SLM without cloud tokens."""
    def mock_fix(prompt: str, sys: str) -> str:
        return "except KeyError:\n        val = None"

    engine = EdgeSLMEngine(mock_handler=mock_fix)
    analyzer = OfflineASTAnalyzer(slm_engine=engine)

    defect = ASTDefectItem(
        line_number=5,
        rule_id="ANTI-CORRUPTION-TYPED-FAILURES",
        message="Bare except",
        severity="ERROR",
    )
    fix_resp = await analyzer.propose_quick_fix(defect, BARE_EXCEPT_SNIPPET)
    assert fix_resp is not None
    assert "KeyError" in fix_resp.content
    assert fix_resp.cloud_egress_prevented is True


# --- SmartModelDispatcher Tests ---

@pytest.mark.asyncio
async def test_smart_dispatcher_routes_low_complexity_to_edge_slm():
    """Verify CC <= 10 code snippets are routed to EDGE_SLM with token savings."""
    engine = EdgeSLMEngine(mock_handler=lambda p, s: "output")
    dispatcher = SmartModelDispatcher(slm_engine=engine, complexity_threshold=10)

    decision = await dispatcher.decide_route(SIMPLE_SNIPPET)
    assert decision.target == ModelRouteTarget.EDGE_SLM
    assert decision.is_local_eligible is True
    assert decision.cyclomatic_complexity <= 10
    assert decision.estimated_cloud_tokens_saved > 0
    assert decision.fallback_triggered is False


@pytest.mark.asyncio
async def test_smart_dispatcher_routes_high_complexity_to_cloud():
    """Verify CC > 10 code snippets are routed to CLOUD_REASONER."""
    engine = EdgeSLMEngine(mock_handler=lambda p, s: "output")
    dispatcher = SmartModelDispatcher(slm_engine=engine, complexity_threshold=10)

    decision = await dispatcher.decide_route(HIGH_COMPLEXITY_SNIPPET)
    assert decision.target == ModelRouteTarget.CLOUD_REASONER
    assert decision.is_local_eligible is False
    assert decision.cyclomatic_complexity > 10
    assert decision.estimated_cloud_tokens_saved == 0


@pytest.mark.asyncio
async def test_smart_dispatcher_routes_slm_task_types_to_edge_slm():
    """Verify specific task types (e.g. SYNTAX_CLEANUP) route to EDGE_SLM."""
    engine = EdgeSLMEngine(mock_handler=lambda p, s: "output")
    dispatcher = SmartModelDispatcher(slm_engine=engine)

    decision = await dispatcher.decide_route(
        SIMPLE_SNIPPET,
        task_type=RefactoringTaskType.SYNTAX_CLEANUP.value,
    )
    assert decision.target == ModelRouteTarget.EDGE_SLM


@pytest.mark.asyncio
async def test_smart_dispatcher_offline_fallback():
    """Verify graceful fallback to CLOUD_REASONER when Edge SLM is offline."""
    # Engine pointing to closed port with no mock
    engine = EdgeSLMEngine(base_url="http://127.0.0.1:99999", mock_handler=None)
    dispatcher = SmartModelDispatcher(slm_engine=engine, cloud_fallback_enabled=True)

    decision = await dispatcher.decide_route(SIMPLE_SNIPPET, check_health=True)
    assert decision.target == ModelRouteTarget.CLOUD_REASONER
    assert decision.fallback_triggered is True
    assert "fallback to cloud" in decision.reason


@pytest.mark.asyncio
async def test_smart_dispatcher_execute_task_edge_and_cloud():
    """Verify execute_task routes execution to local SLM or cloud mock."""
    engine = EdgeSLMEngine(mock_handler=lambda p, s: "# SLM Generated Clean Code")
    dispatcher = SmartModelDispatcher(slm_engine=engine, complexity_threshold=10)

    # Edge SLM execution path
    result_slm = await dispatcher.execute_task(
        prompt="Refactor this function",
        code_snippet=SIMPLE_SNIPPET,
    )
    assert result_slm["source"] == "EDGE_SLM"
    assert "Clean Code" in result_slm["response"]["content"]
    assert result_slm["tokens_saved"] > 0

    # Cloud Reasoner execution path
    async def mock_cloud_executor(p: str, c: str) -> str:
        return "# Cloud Reasoner Refactoring"

    result_cloud = await dispatcher.execute_task(
        prompt="Refactor complex matrix",
        code_snippet=HIGH_COMPLEXITY_SNIPPET,
        cloud_executor=mock_cloud_executor,
    )
    assert result_cloud["source"] == "CLOUD_REASONER"
    assert "Cloud Reasoner Refactoring" in result_cloud["response"]["content"]


# --- MeshFactoryDispatcher Integration Tests ---

def test_mesh_dispatcher_routes_to_edge_slm_peer():
    """Verify MeshFactoryDispatcher assigns SYNTAX_CLEANUP & TEST_STUB_GENERATION to EDGE_SLM."""
    dispatcher = MeshFactoryDispatcher()

    # Verify node-edge-slm-worker is present in peer registry
    assert "node-edge-slm-worker" in dispatcher.peers
    assert PeerCapability.EDGE_SLM.value in dispatcher.peers["node-edge-slm-worker"]

    dag = RefactoringTaskDAG(goal="Edge SLM Workload Test")
    t1 = RefactoringTaskNode(
        node_id="task-syntax-clean",
        title="AST Syntax Cleanup",
        task_type=RefactoringTaskType.SYNTAX_CLEANUP,
        target_files=["clean.py"],
        mutable_scope=["clean.py"],
    )
    t2 = RefactoringTaskNode(
        node_id="task-stub-gen",
        title="Pytest Stub Generation",
        task_type=RefactoringTaskType.TEST_STUB_GENERATION,
        target_files=["stubs.py"],
        mutable_scope=["stubs.py"],
    )
    dag.add_node(t1)
    dag.add_node(t2)

    plan = dispatcher.create_dispatch_plan(dag)
    assert len(plan.assignments) == 2

    assignment_map = {a.task_id: a for a in plan.assignments}
    assert assignment_map["task-syntax-clean"].required_capability == PeerCapability.EDGE_SLM.value
    assert assignment_map["task-syntax-clean"].assigned_peer_id == "node-edge-slm-worker"

    assert assignment_map["task-stub-gen"].required_capability == PeerCapability.EDGE_SLM.value
    assert assignment_map["task-stub-gen"].assigned_peer_id == "node-edge-slm-worker"
