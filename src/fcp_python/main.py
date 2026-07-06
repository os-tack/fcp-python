"""fcp-python — Python Code Intelligence FCP MCP server."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from fastmcp import FastMCP

from fcp_core import VerbRegistry, suggest

from fcp_python.domain.format import format_error
from fcp_python.domain.model import PythonModel
from fcp_python.domain.mutation import dispatch_mutation
from fcp_python.domain.query import dispatch_query
from fcp_python.domain.verbs import (
    register_mutation_verbs,
    register_query_verbs,
    register_session_verbs,
)
from fcp_python.lsp.client import LspClient
from fcp_python.lsp.lifecycle import ServerStatus
from fcp_python.lsp.types import PublishDiagnosticsParams, SymbolInformation
from fcp_python.resolver.index import SymbolEntry, SymbolIndex

mcp = FastMCP(
    "fcp-python",
    instructions=(
        "FCP Python server for querying and refactoring Python codebases via pylsp. "
        "Use python_session to open a workspace directory containing Python files, "
        "python_query for read-only queries like finding definitions, references, "
        "diagnostics, and symbols, python for refactoring operations, and python_help "
        "for the full verb reference. Start every interaction with python_session."
    ),
)

# Global state
_model = PythonModel("file:///")
_lock = asyncio.Lock()


def _make_registry() -> VerbRegistry:
    reg = VerbRegistry()
    register_query_verbs(reg)
    register_mutation_verbs(reg)
    register_session_verbs(reg)
    return reg


_registry = _make_registry()


@mcp.tool(
    description=(
        "Execute Python mutation operations. Examples: "
        "'rename Config Settings'"
    )
)
async def python(ops: list[str]) -> str:
    """Execute mutation operations."""
    async with _lock:
        results = []
        for op in ops:
            result = await dispatch_mutation(_model, _registry, op)
            results.append(result)
        return "\n\n".join(results)


@mcp.tool(
    description=(
        "Execute a read-only FCP query on the Python workspace. Examples: "
        "'find Config', 'def main @file:main.py', 'diagnose', 'unused', 'map'"
    )
)
async def python_query(input: str) -> str:
    """Execute a read-only query."""
    async with _lock:
        return await dispatch_query(_model, _registry, input)


@mcp.tool(
    description=(
        "Manage the Python workspace session. Actions: "
        "'open PATH' to open a workspace, "
        "'status' to check server status, "
        "'close' to close the workspace."
    )
)
async def python_session(action: str) -> str:
    """Manage workspace session."""
    async with _lock:
        return await _handle_session(action)


@mcp.tool(
    description="Show the FCP Python reference card with all available verbs and their syntax."
)
async def python_help() -> str:
    """Show reference card."""
    extra = {
        "Selectors": (
            "  @file:PATH      — filter by file path\n"
            "  @class:NAME     — filter by containing class\n"
            "  @kind:KIND      — filter by symbol kind (function, class, method, variable, ...)\n"
            "  @module:NAME    — filter by module\n"
            "  @line:N         — filter by line number\n"
            "  @decorator:NAME — filter by decorator"
        ),
        "Mutation Examples": (
            '  python ["rename Config Settings"]              — cross-file semantic rename'
        ),
    }
    return _registry.generate_reference_card(extra)


async def _handle_session(action: str) -> str:
    global _model
    tokens = action.split()
    if not tokens:
        return "! empty session action."

    cmd = tokens[0]
    if cmd == "open":
        if len(tokens) < 2:
            return "! open requires a path."
        return await _handle_open(tokens[1])
    elif cmd == "status":
        return _handle_status()
    elif cmd == "close":
        return await _handle_close()
    else:
        return f"! unknown session action '{cmd}'."


async def _handle_open(path: str) -> str:
    global _model

    if path.startswith("file://"):
        uri = path
    else:
        p = Path(path).resolve()
        if not p.exists():
            return f"! path not found: {path}"
        uri = p.as_uri()

    try:
        client = await LspClient.spawn("pylsp", [], uri)
    except Exception as e:
        return f"! failed to start pylsp: {e}"

    _model = PythonModel(uri)
    _model.lsp_client = client
    _model.server_status = ServerStatus.Ready
    _model.py_file_count = _count_py_files(path)

    # Start notification handler
    asyncio.create_task(_notification_handler(client.notification_queue, _model))

    # Populate initial index
    symbol_count = await _populate_initial_index(client, _model)

    _model.last_reload = time.time()

    return f"Opened workspace: {path} ({_model.py_file_count} files, {symbol_count} symbols)"


def _handle_status() -> str:
    status_str = _model.server_status.name
    errors, warnings = _model.total_diagnostics()
    return (
        f"Status: {status_str}\n"
        f"Workspace: {_model.root_uri}\n"
        f"Files: {_model.py_file_count}\n"
        f"Symbols: {_model.symbol_index.size()}\n"
        f"Diagnostics: {errors} errors, {warnings} warnings"
    )


async def _handle_close() -> str:
    global _model
    if _model.lsp_client:
        try:
            await _model.lsp_client.shutdown()
        except Exception:
            pass

    _model.server_status = ServerStatus.Stopped
    _model.lsp_client = None
    _model.symbol_index = SymbolIndex()
    _model.diagnostics.clear()
    _model.open_documents.clear()

    return "Workspace closed."


async def _notification_handler(
    queue: asyncio.Queue,
    model: PythonModel,
) -> None:
    """Process LSP notifications (diagnostics etc)."""
    while True:
        try:
            notif = await queue.get()
        except Exception:
            break
        if notif.method == "textDocument/publishDiagnostics":
            if notif.params:
                try:
                    params = PublishDiagnosticsParams.from_dict(notif.params)
                    model.update_diagnostics(params.uri, params.diagnostics)
                except Exception:
                    pass


async def _populate_initial_index(client: LspClient, model: PythonModel) -> int:
    """Populate symbol index with workspace/symbol query, with retries."""
    for attempt in range(10):
        try:
            raw_symbols = await client.request("workspace/symbol", {"query": "*"})
            if raw_symbols:
                for sym_dict in raw_symbols:
                    sym = SymbolInformation.from_dict(sym_dict)
                    model.symbol_index.insert(SymbolEntry(
                        name=sym.name,
                        kind=sym.kind,
                        container_name=sym.container_name,
                        uri=sym.location.uri,
                        range=sym.location.range,
                        selection_range=sym.location.range,
                    ))
                return len(raw_symbols)
        except Exception:
            pass
        if attempt < 9:
            await asyncio.sleep(0.5)
    return 0


def _count_py_files(path: str) -> int:
    """Count .py files in directory, skipping hidden dirs and __pycache__."""
    if not os.path.isdir(path):
        return 0
    skip_dirs = {"__pycache__", "node_modules", ".venv", "venv"}
    count = 0
    try:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                if entry.name.startswith(".") or entry.name in skip_dirs:
                    continue
                count += _count_py_files(entry.path)
            elif entry.name.endswith(".py"):
                count += 1
    except PermissionError:
        pass
    return count


def main() -> None:
    # Spawn slipstream bridge in background (silent no-op if daemon not running)
    from fcp_python.bridge import start_bridge

    async def _bridge_session(action: str) -> str:
        async with _lock:
            return await _handle_session(action)

    async def _bridge_query(q: str) -> str:
        async with _lock:
            return await dispatch_query(_model, _registry, q)

    async def _bridge_mutation(ops: list[str]) -> str:
        async with _lock:
            results = []
            for op in ops:
                results.append(await dispatch_mutation(_model, _registry, op))
            return "\n\n".join(results)

    bridge_thread = start_bridge(_bridge_session, _bridge_query, _bridge_mutation)

    # Bridge-only mode: when spawned by slipstream (stdin is /dev/null),
    # mcp.run() would get immediate EOF and exit, killing the bridge thread.
    # Instead, block on the bridge thread directly.
    if os.environ.get("SLIPSTREAM_SOCKET") and not os.isatty(0):
        if bridge_thread is not None:
            bridge_thread.join()
            return
        # No bridge thread means socket wasn't found — nothing to do
        return

    mcp.run()


if __name__ == "__main__":
    main()
