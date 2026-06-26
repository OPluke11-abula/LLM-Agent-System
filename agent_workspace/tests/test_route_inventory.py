import pytest
from agent_workspace.api import app


def collect_route_paths(routes):
    paths = set()
    for route in routes:
        if hasattr(route, "path"):
            paths.add(route.path)
        original_router = getattr(route, "original_router", None)
        if original_router is not None and hasattr(original_router, "routes"):
            paths.update(collect_route_paths(original_router.routes))
    return paths


def test_api_route_inventory():
    """Verify that all modular endpoint routes exist and match the expected inventory."""
    actual_routes = collect_route_paths(app.routes)
    expected_routes = {
        '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc',
        '/v1/swarm/nodes', '/v1/swarm/scale', '/v1/swarm/health', '/v1/swarm/peers',
        '/v1/swarm/billing/status', '/v1/swarm/billing/policy', '/v1/swarm/sessions',
        '/v1/swarm/sessions/resume', '/v1/swarm/replays/{session_id}', '/v1/swarm/replays/clean',
        '/v1/swarm/telemetry/ws', '/v1/swarm/governance/rules', '/v1/swarm/governance/vote',
        '/v1/cross-cloud/cert/status', '/v1/cross-cloud/cert/rotate', '/v1/cross-cloud/revoke',
        '/v1/cross-cloud/reinstate', '/v1/cross-cloud/revoked', '/v1/cross-cloud/tunnel',
        '/v1/audit/logs', '/v1/audit/verify', '/v1/audit/status', '/v1/audit/sync',
        '/v1/audit/proof/{event_id}', '/v1/audit/verify-proof', '/v1/health',
        '/v1/metrics', '/metrics', '/v1/tools', '/v1/chat', '/v1/stream', '/v1/stream_ws',
        '/v1/stream', '/v1/task', '/v1/session/{session_id}', '/v1/session/{session_id}/approve',
        '/v1/sessions/{session_id}/approve', '/v1/session/{session_id}/reject',
        '/v1/sessions/{session_id}/reject', '/v1/memory', '/v1/memory/query',
        '/v1/memory/preference', '/v1/memory/{session_id}/{key}', '/v1/memory/prune',
        '/v1/memory/update', '/v1/memory/batch-move',
        '/v1/config', '/v1/accounts', '/v1/accounts/{account_id}', '/v1/accounts/active',
        '/v1/session/{session_id}/turns', '/v1/sessions/{session_id}/turns',
        '/v1/session/{session_id}/handoff', '/v1/sessions/{session_id}/handoff',
        '/v1/session/{session_id}/defragment', '/v1/sessions/{session_id}/defragment',
        '/v1/session/{session_id}/defragment/metrics', '/v1/sessions/{session_id}/defragment/metrics',
        '/v1/session/{session_id}/ledger', '/v1/sessions/{session_id}/ledger',
        '/v1/session/{session_id}/ledger/reset', '/v1/sessions/{session_id}/ledger/reset',
        '/v1/session/{session_id}/sandbox/status', '/v1/sessions/{session_id}/sandbox/status',
        '/v1/session/{session_id}/telemetry', '/v1/sessions/{session_id}/telemetry',
        '/v1/session/{session_id}/router/status', '/v1/sessions/{session_id}/router/status',
        '/v1/router/status', '/v1/session/{session_id}/router/prune',
        '/v1/sessions/{session_id}/router/prune', '/v1/router/prune', '/v1/builder/agents',
        '/v1/builder/templates', '/v1/builder/test', '/v1/sandbox/execute',
        '/v1/crew/register', '/v1/crew/topology', '/v1/collaboration/{session_id}',
        '/v1/dashboard/{session_id}/{role}', '/v1/crew/sync/{session_id}', '/v1/federated/sync',
        '/v1/swarm/p2p/tunnel', '/v1/channels/slack/webhook', '/v1/channels/line/webhook',
        '/v1/billing/stripe/webhook', '/v1/auth/token', '/v1/admin/tenants',
        '/v1/admin/tenants/rotate-key', '/v1/admin/tenants/update-subscription',
        '/v1/session/{session_id}/pause', '/v1/sessions/{session_id}/pause',
        '/v1/session/{session_id}/resume', '/v1/sessions/{session_id}/resume',
        '/v1/session/{session_id}/hijack', '/v1/sessions/{session_id}/hijack',
        '/v1/billing/saas/invoice', '/v1/workspace/config'
    }
    # Check that all expected routes are present in actual routes
    missing = expected_routes - actual_routes
    assert not missing, f"Missing routes: {missing}"
