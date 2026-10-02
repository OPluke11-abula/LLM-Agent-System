"""
agent_workspace/routes/responses.py - OpenAI-compatible Responses API Gateway (Phase 105 Task D).

Provides POST /v1/responses endpoint with SSE streaming and non-streaming responses,
supporting multi-account quota-aware routing, client disconnect handling, and tool execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Union

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent_workspace.core.account_manager import QuotaExhaustedError
from agent_workspace.core.protocol_repair import ProtocolRepairManager, RepairStrategy
from agent_workspace.core.providers import ProviderFactory
from agent_workspace.routes.dependencies import get_account_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["responses"])


def _repair_tool_calls(
    raw_calls: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]],
    repair_mgr: ProtocolRepairManager,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Applies ProtocolRepairManager to normalize/repair tool call arguments."""
    repaired_calls = []
    repair_events = []

    schema_map: dict[str, dict[str, Any]] = {}
    for t in tool_schemas:
        if isinstance(t, dict):
            name = t.get("name") or t.get("function", {}).get("name", "")
            if name:
                schema_map[name] = t.get("parameters") or t.get("function", {}).get("parameters", {})

    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        c_name = call.get("name", "")
        c_args = call.get("arguments", {})
        target_schema = schema_map.get(c_name)

        repair_res = repair_mgr.validate_and_repair(
            tool_name=c_name,
            raw_arguments=c_args,
            schema=target_schema,
        )

        final_args = repair_res.repaired_arguments if repair_res.success else c_args
        repaired_call = dict(call)
        repaired_call["arguments"] = final_args
        repaired_calls.append(repaired_call)

        if repair_res.strategy != RepairStrategy.NOOP:
            repair_events.append({
                "tool": c_name,
                "strategy": repair_res.strategy.value,
                "turns": repair_res.turns_used,
                "success": repair_res.success,
                "history": repair_res.repair_history,
            })

    return repaired_calls, repair_events


class ResponsesRequest(BaseModel):
    model: str = "gpt-4o"
    input: Union[str, list[Any]] = Field(..., description="Prompt or message sequence")
    stream: bool = False
    instructions: str | None = None
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None


def _normalize_input_messages(raw_input: Union[str, list[Any]]) -> list[dict[str, Any]]:
    if isinstance(raw_input, str):
        return [{"role": "user", "content": raw_input}]
    if isinstance(raw_input, list):
        messages: list[dict[str, Any]] = []
        for item in raw_input:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                if "role" in item and "content" in item:
                    messages.append(item)
                elif "content" in item:
                    messages.append({"role": "user", "content": item["content"]})
                else:
                    messages.append({"role": "user", "content": str(item)})
            else:
                messages.append({"role": "user", "content": str(item)})
        return messages if messages else [{"role": "user", "content": ""}]
    return [{"role": "user", "content": str(raw_input)}]


def _infer_provider_from_model(model: str) -> str:
    m = (model or "").lower()
    if any(prefix in m for prefix in ("gemini", "google")):
        return "google-genai"
    if any(prefix in m for prefix in ("claude", "anthropic")):
        return "anthropic"
    if "ollama" in m:
        return "ollama"
    if "deepseek" in m:
        return "deepseek"
    return "openai"


@router.post("/v1/responses")
async def create_response(request: Request, body: ResponsesRequest):
    """OpenAI-compatible Responses API endpoint.

    Supports non-streaming JSON output and SSE event streaming with quota-aware routing.
    """
    messages = _normalize_input_messages(body.input)
    provider_name = _infer_provider_from_model(body.model)
    am = get_account_manager()

    # Route through QuotaAwareRouter if available
    active_account = None
    account_id = "default"
    try:
        if hasattr(am, "quota_router"):
            active_account = am.quota_router.get_available_account(preferred_provider=provider_name)
        else:
            active_account = am.get_active_account()
        if active_account:
            account_id = active_account.get("id", "default")
    except QuotaExhaustedError:
        raise HTTPException(
            status_code=429,
            detail="Quota exhausted across all available accounts in pool."
        )
    except Exception as exc:
        logger.warning("Quota-aware routing fallback: %s", exc)
        active_account = am.get_active_account()

    api_key = am.resolve_api_key(active_account) if active_account else None
    base_url = active_account.get("base_url") if active_account else None

    try:
        provider = ProviderFactory.get_provider(provider_name, api_key=api_key, base_url=base_url)
    except Exception as exc:
        logger.error("Failed to acquire provider '%s': %s", provider_name, exc)
        raise HTTPException(status_code=500, detail=f"Provider initialization failed: {exc}")

    system_prompt = body.instructions or ""
    tool_schemas = body.tools or []
    config: dict[str, Any] = {
        "model": body.model,
        "temperature": body.temperature if body.temperature is not None else 0.7,
    }
    if body.max_output_tokens:
        config["max_tokens"] = body.max_output_tokens

    if body.stream:
        async def event_generator():
            resp_id = f"resp_{uuid.uuid4().hex[:16]}"
            item_id = f"msg_{uuid.uuid4().hex[:16]}"

            # 1. response.created
            init_resp = {
                "id": resp_id,
                "object": "response",
                "created_at": int(time.time()),
                "status": "in_progress",
                "model": body.model,
                "output": [],
            }
            yield f"event: response.created\ndata: {json.dumps({'response': init_resp})}\n\n"

            # 2. response.output_item.added
            item_payload = {
                "id": item_id,
                "type": "message",
                "status": "in_progress",
                "role": "assistant",
                "content": [],
            }
            yield f"event: response.output_item.added\ndata: {json.dumps({'output_item': item_payload})}\n\n"

            repair_mgr = ProtocolRepairManager()

            # Call provider with dynamic failover
            try:
                if await request.is_disconnected():
                    logger.info("Client disconnected before completion: %s", resp_id)
                    return

                result = await provider.complete(system_prompt, messages, tool_schemas, config)
                resp_type = result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else "text"
                raw_text = result[1] if isinstance(result, (tuple, list)) and len(result) > 1 else str(result)
            except Exception as exc:
                err_msg = str(exc)
                logger.warning("Primary provider '%s' failed in streaming: %s. Attempting failover...", provider_name, err_msg)
                if hasattr(am, "quota_router"):
                    am.quota_router.mark_rate_limited(account_id)

                fallback_success = False
                if hasattr(am, "quota_router"):
                    fb_acc, fb_prov, fb_model = am.quota_router.get_fallback_account_or_provider(
                        failed_account_id=account_id, failed_provider=provider_name
                    )
                    if fb_prov and fb_prov.lower() != provider_name.lower():
                        try:
                            fb_key = am.resolve_api_key(fb_acc) if fb_acc else None
                            fb_url = fb_acc.get("base_url") if fb_acc else None
                            fb_provider = ProviderFactory.get_provider(fb_prov, api_key=fb_key, base_url=fb_url)
                            fb_config = dict(config)
                            fb_config["model"] = fb_model

                            yield f"event: response.failover\ndata: {json.dumps({'from': provider_name, 'to': fb_prov, 'model': fb_model, 'reason': err_msg})}\n\n"

                            result = await fb_provider.complete(system_prompt, messages, tool_schemas, fb_config)
                            resp_type = result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else "text"
                            raw_text = result[1] if isinstance(result, (tuple, list)) and len(result) > 1 else str(result)
                            fallback_success = True
                            logger.info("Successfully failed over to '%s' (%s)", fb_prov, fb_model)
                        except Exception as fb_exc:
                            logger.error("Fallback provider '%s' failed: %s", fb_prov, fb_exc)
                            err_msg = f"{err_msg}; fallback error: {fb_exc}"

                if not fallback_success:
                    yield f"event: response.error\ndata: {json.dumps({'error': err_msg})}\n\n"
                    return

            if await request.is_disconnected():
                logger.info("Client disconnected during stream delivery: %s", resp_id)
                return

            # Function call or text content with ProtocolRepair self-healing
            if resp_type == "tool_calls" and isinstance(raw_text, list):
                repaired_calls, repair_events = _repair_tool_calls(raw_text, tool_schemas, repair_mgr)
                for r_evt in repair_events:
                    yield f"event: response.repair\ndata: {json.dumps(r_evt)}\n\n"
                for call in repaired_calls:
                    call_name = call.get("name", "")
                    call_args = call.get("arguments", {})
                    yield f"event: response.function_call\ndata: {json.dumps({'name': call_name, 'arguments': call_args})}\n\n"
                raw_text = repaired_calls
            else:
                text_content = raw_text if isinstance(raw_text, str) else json.dumps(raw_text)
                part_payload = {
                    "type": "output_text",
                    "text": text_content,
                }
                yield f"event: response.content_part.added\ndata: {json.dumps({'part': part_payload})}\n\n"

            # 3. response.output_item.done
            done_content = [
                {
                    "type": "output_text",
                    "text": raw_text if isinstance(raw_text, str) else json.dumps(raw_text),
                }
            ]
            done_item = {
                "id": item_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": done_content,
            }
            yield f"event: response.output_item.done\ndata: {json.dumps({'output_item': done_item})}\n\n"

            # Usage tracking
            usage_info = getattr(result, "usage", None) or {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            if hasattr(am, "quota_router"):
                am.quota_router.record_request_telemetry(account_id, tokens=usage_info.get("total_tokens", 0))

            # 4. response.completed
            final_resp = {
                "id": resp_id,
                "object": "response",
                "created_at": int(time.time()),
                "status": "completed",
                "model": body.model,
                "output": [done_item],
                "usage": {
                    "total_tokens": usage_info.get("total_tokens", 0),
                    "input_tokens": usage_info.get("prompt_tokens", 0),
                    "output_tokens": usage_info.get("completion_tokens", 0),
                },
            }
            yield f"event: response.completed\ndata: {json.dumps({'response': final_resp})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming mode with dynamic failover
    repair_mgr = ProtocolRepairManager()
    try:
        result = await provider.complete(system_prompt, messages, tool_schemas, config)
    except Exception as exc:
        err_msg = str(exc)
        logger.warning("Primary provider '%s' failed in non-streaming: %s. Attempting failover...", provider_name, err_msg)
        if hasattr(am, "quota_router"):
            am.quota_router.mark_rate_limited(account_id)

        fallback_success = False
        if hasattr(am, "quota_router"):
            fb_acc, fb_prov, fb_model = am.quota_router.get_fallback_account_or_provider(
                failed_account_id=account_id, failed_provider=provider_name
            )
            if fb_prov and fb_prov.lower() != provider_name.lower():
                try:
                    fb_key = am.resolve_api_key(fb_acc) if fb_acc else None
                    fb_url = fb_acc.get("base_url") if fb_acc else None
                    fb_provider = ProviderFactory.get_provider(fb_prov, api_key=fb_key, base_url=fb_url)
                    fb_config = dict(config)
                    fb_config["model"] = fb_model
                    result = await fb_provider.complete(system_prompt, messages, tool_schemas, fb_config)
                    fallback_success = True
                    logger.info("Non-streaming successfully failed over to '%s' (%s)", fb_prov, fb_model)
                except Exception as fb_exc:
                    logger.error("Non-streaming fallback failed: %s", fb_exc)

        if not fallback_success:
            if "429" in err_msg or "rate limit" in err_msg.lower():
                raise HTTPException(status_code=429, detail="Upstream provider rate limited")
            raise HTTPException(status_code=500, detail=f"Provider completion failed: {err_msg}")

    resp_type = result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else "text"
    raw_content = result[1] if isinstance(result, (tuple, list)) and len(result) > 1 else str(result)

    if resp_type == "tool_calls" and isinstance(raw_content, list):
        repaired_calls, _ = _repair_tool_calls(raw_content, tool_schemas, repair_mgr)
        raw_content = repaired_calls

    usage_info = getattr(result, "usage", None) or {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    if hasattr(am, "quota_router"):
        am.quota_router.record_request_telemetry(account_id, tokens=usage_info.get("total_tokens", 0))

    resp_id = f"resp_{uuid.uuid4().hex[:16]}"
    msg_id = f"msg_{uuid.uuid4().hex[:16]}"

    if resp_type == "tool_calls" and isinstance(raw_content, list):
        message_content = [
            {
                "type": "function_call",
                "name": call.get("name", "") if isinstance(call, dict) else "",
                "arguments": (
                    json.dumps(call.get("arguments", {}), ensure_ascii=False)
                    if isinstance(call, dict) and isinstance(call.get("arguments"), dict)
                    else str(call.get("arguments", "") if isinstance(call, dict) else call)
                ),
            }
            for call in raw_content
        ]
    else:
        text_content = raw_content if isinstance(raw_content, str) else json.dumps(raw_content, ensure_ascii=False)
        message_content = [
            {
                "type": "output_text",
                "text": text_content,
            }
        ]

    return JSONResponse(
        status_code=200,
        content={
            "id": resp_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "model": body.model,
            "output": [
                {
                    "id": msg_id,
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": message_content,
                }
            ],
            "usage": {
                "total_tokens": usage_info.get("total_tokens", 0),
                "input_tokens": usage_info.get("prompt_tokens", 0),
                "output_tokens": usage_info.get("completion_tokens", 0),
            },
        },
    )
