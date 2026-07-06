"""Mutation dispatcher and handlers."""

from __future__ import annotations

from fcp_core import VerbRegistry, parse_op, suggest, ParseError

from fcp_python.lsp.types import WorkspaceEdit
from fcp_python.lsp.workspace_edit import apply_workspace_edit
from fcp_python.resolver.selectors import parse_selector

from .format import (
    format_disambiguation,
    format_error,
    format_mutation_result,
)
from .model import PythonModel
from .query import resolve_with_fallback


async def dispatch_mutation(
    model: PythonModel,
    registry: VerbRegistry,
    input_str: str,
) -> str:
    """Dispatch a mutation operation string to the appropriate handler."""
    op = parse_op(input_str)
    if isinstance(op, ParseError):
        return format_error(f"parse error: {op.error}", None)

    if registry.lookup(op.verb) is None:
        verb_names = [v.verb for v in registry.verbs]
        suggestion = suggest(op.verb, verb_names)
        return format_error(f"unknown verb '{op.verb}'.", suggestion)

    if model.lsp_client is None:
        return format_error("no workspace open. Use python_session open PATH first.", None)

    match op.verb:
        case "rename":
            return await handle_rename(model, op.positionals, op.selectors)
        case _:
            return format_error(f"verb '{op.verb}' is not a mutation.", None)


# -- rename ---------------------------------------------------------------

async def handle_rename(
    model: PythonModel,
    positionals: list[str],
    selectors: list[str],
) -> str:
    if len(positionals) < 2:
        return format_error("rename requires SYMBOL and NEW_NAME.", None)
    old_name = positionals[0]
    new_name = positionals[1]

    parsed_selectors = [s for s in (parse_selector(sel) for sel in selectors) if s is not None]
    resolved = await resolve_with_fallback(model, old_name, parsed_selectors)

    if resolved.is_ambiguous:
        return format_disambiguation(old_name, resolved.entries)
    if resolved.is_not_found:
        return format_error(f"symbol '{old_name}' not found.", None)
    entry = resolved.entry

    client = model.lsp_client
    assert client is not None

    params = {
        "textDocument": {"uri": entry.uri},
        "position": {
            "line": entry.selection_range.start.line,
            "character": entry.selection_range.start.character,
        },
        "newName": new_name,
    }

    try:
        raw_edit = await client.request("textDocument/rename", params)
    except Exception as e:
        return format_error(f"rename failed: {e}", None)

    if raw_edit is None:
        return format_error("rename returned no edit.", None)

    workspace_edit = WorkspaceEdit.from_dict(raw_edit)
    try:
        result = apply_workspace_edit(workspace_edit)
    except Exception as e:
        return format_error(f"failed to apply rename: {e}", None)

    return format_mutation_result(
        "rename", f"{old_name} → {new_name}", result, model.root_uri
    )

