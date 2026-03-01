"""
High-level tracking functions for common AutoFlow use cases.

This module provides simple decorators and context managers for tracking
agents, tools, MCP servers, and workflows with minimal code.

Usage:
    from autoflow.track import track_agent, track_tool_call, track_workflow

    # Track an agent execution
    @track_agent(agent_id="my_agent")
    async def my_agent(query: str):
        # Your agent code here
        return response

    # Track tool calls
    result = await track_tool_call(
        tool_name="search",
        agent_id="my_agent",
        parameters={"query": "test"}
    )(search_tool)("test")

    # Track workflow execution
    async with track_workflow(workflow_id="data_pipeline"):
        await run_pipeline()
"""

import functools
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Callable, Any, Mapping
from pathlib import Path

from autoflow.factory import autoflow
from autoflow.types import ObservationEvent, make_event
from autoflow.orchestrator.engine import AutoImproveEngine
from autoflow.orchestrator.engine_async import AsyncAutoImproveEngine


# Global engine instance (lazy-loaded)
_global_engine: Optional[AsyncAutoImproveEngine] = None


def get_engine() -> Optional[AsyncAutoImproveEngine]:
    """Get the global AutoFlow engine instance."""
    global _global_engine
    if _global_engine is None:
        # Create in-memory engine by default
        _global_engine = autoflow(in_memory=True)
    return _global_engine


def set_engine(engine: AsyncAutoImproveEngine) -> None:
    """Set the global AutoFlow engine instance."""
    global _global_engine
    _global_engine = engine


async def emit_event(
    source: str,
    name: str,
    attributes: Mapping[str, Any],
) -> None:
    """Emit an event to the global AutoFlow engine."""
    engine = get_engine()
    if engine:
        await engine.ingest([make_event(source=source, name=name, attributes=attributes)])


# =============================================================================
# Agent Tracking
# =============================================================================

def track_agent(
    agent_id: str,
    agent_type: Optional[str] = None,
    model: Optional[str] = None,
):
    """
    Decorator to track agent execution events.

    Usage:
        @track_agent(agent_id="search_agent", model="gpt-4")
        async def search_agent(query: str):
            return await search(query)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Emit start event
            await emit_event(
                source="agent",
                name="execution_started",
                attributes={
                    "agent_id": agent_id,
                    "agent_type": agent_type or func.__name__,
                    "model": model,
                    "query": str(args) if args else None,
                }
            )

            try:
                result = await func(*args, **kwargs)

                # Emit success event
                await emit_event(
                    source="agent",
                    name="execution_completed",
                    attributes={
                        "agent_id": agent_id,
                        "success": True,
                    }
                )

                return result

            except Exception as e:
                # Emit error event (triggers AutoFlow rules)
                await emit_event(
                    source="agent",
                    name="execution_failed",
                    attributes={
                        "agent_id": agent_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, emit synchronously if possible
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Try async emit, fall back silently
                try:
                    import asyncio
                    asyncio.create_task(emit_event(
                        source="agent",
                        name="execution_failed",
                        attributes={
                            "agent_id": agent_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    ))
                except:
                    pass
                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# Tool Call Tracking
# =============================================================================

async def track_tool_call(
    tool_name: str,
    agent_id: Optional[str] = None,
    parameters: Optional[Mapping[str, Any]] = None,
    result: Optional[Any] = None,
    error: Optional[Exception] = None,
):
    """
    Track a tool call event.

    Usage:
        await track_tool_call(
            tool_name="search",
            agent_id="my_agent",
            parameters={"query": "test"}
        )
    """
    attributes = {
        "tool_name": tool_name,
        "agent_id": agent_id,
    }

    if parameters:
        attributes["parameters"] = dict(parameters)

    if error:
        attributes["error"] = str(error)
        attributes["error_type"] = type(error).__name__
        await emit_event(source="tool", name="call_failed", attributes=attributes)
    else:
        await emit_event(source="tool", name="call_completed", attributes=attributes)


# =============================================================================
# Workflow Tracking
# =============================================================================

@asynccontextmanager
async def track_workflow(
    workflow_id: str,
    workflow_name: Optional[str] = None,
):
    """
    Context manager to track workflow execution.

    Usage:
        async with track_workflow(workflow_id="data_pipeline"):
            await step1()
            await step2()
            await step3()
    """
    # Emit workflow start
    await emit_event(
        source="workflow",
        name="execution_started",
        attributes={
            "workflow_id": workflow_id,
            "workflow_name": workflow_name or workflow_id,
        }
    )

    try:
        yield

        # Emit workflow completion
        await emit_event(
            source="workflow",
            name="execution_completed",
            attributes={
                "workflow_id": workflow_id,
                "success": True,
            }
        )

    except Exception as e:
        # Emit workflow failure (triggers AutoFlow rules)
        await emit_event(
            source="workflow",
            name="execution_failed",
            attributes={
                "workflow_id": workflow_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
        raise


# =============================================================================
# MCP Server Tracking
# =============================================================================

async def track_mcp_tool(
    server_id: str,
    tool_name: str,
    parameters: Optional[Mapping[str, Any]] = None,
):
    """Track an MCP tool invocation."""
    await track_tool_call(
        tool_name=tool_name,
        agent_id=f"mcp_{server_id}",
        parameters=parameters,
    )


async def track_mcp_server_event(
    server_id: str,
    event_name: str,
    attributes: Optional[Mapping[str, Any]] = None,
):
    """Track an MCP server event."""
    await emit_event(
        source="mcp_server",
        name=event_name,
        attributes={
            "server_id": server_id,
            **(attributes or {}),
        }
    )


# =============================================================================
# Quick Start Functions
# =============================================================================

async def track_error(
    source: str,
    error: Exception,
    context: Optional[Mapping[str, Any]] = None,
):
    """
    Quick way to track an error event.

    Usage:
        try:
            await risky_operation()
        except Exception as e:
            await track_error("my_component", e, {"user_id": 123})
    """
    await emit_event(
        source=source,
        name="error",
        attributes={
            "error": str(error),
            "error_type": type(error).__name__,
            **(context or {}),
        }
    )


async def track_metric(
    source: str,
    metric_name: str,
    value: float,
    units: Optional[str] = None,
):
    """
    Track a metric event.

    Usage:
        await track_metric("database", "query_latency_ms", 42.5)
    """
    await emit_event(
        source=source,
        name="metric",
        attributes={
            "metric_name": metric_name,
            "value": value,
            "units": units,
        }
    )


__all__ = [
    # Engine management
    "get_engine",
    "set_engine",
    # Agent tracking
    "track_agent",
    # Tool tracking
    "track_tool_call",
    "track_mcp_tool",
    "track_mcp_server_event",
    # Workflow tracking
    "track_workflow",
    # Quick utilities
    "track_error",
    "track_metric",
    "emit_event",
]
