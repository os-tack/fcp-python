"""Tests for mutation dispatch and handlers."""

import pytest

from fcp_core import VerbRegistry

from fcp_python.domain.model import PythonModel
from fcp_python.domain.mutation import dispatch_mutation
from fcp_python.domain.verbs import (
    register_mutation_verbs,
    register_query_verbs,
    register_session_verbs,
)


def _make_registry() -> VerbRegistry:
    reg = VerbRegistry()
    register_query_verbs(reg)
    register_mutation_verbs(reg)
    register_session_verbs(reg)
    return reg


def _make_model() -> PythonModel:
    return PythonModel("file:///project")


@pytest.mark.asyncio
async def test_dispatch_mutation_parse_error():
    model = _make_model()
    reg = _make_registry()
    result = await dispatch_mutation(model, reg, "")
    assert "parse error" in result


@pytest.mark.asyncio
async def test_dispatch_mutation_unknown_verb():
    model = _make_model()
    reg = _make_registry()
    result = await dispatch_mutation(model, reg, "refactor Config")
    assert "unknown verb" in result


@pytest.mark.asyncio
async def test_dispatch_mutation_no_workspace():
    model = _make_model()
    reg = _make_registry()
    result = await dispatch_mutation(model, reg, "rename Config Settings")
    assert "no workspace open" in result


@pytest.mark.asyncio
async def test_dispatch_rename_recognized():
    model = _make_model()
    reg = _make_registry()
    result = await dispatch_mutation(model, reg, "rename Config Settings")
    assert "no workspace open" in result


@pytest.mark.asyncio
async def test_dispatch_mutation_unrecognized_removed_verb():
    """extract/import were removed as broken/low-value; verify they're rejected cleanly."""
    model = _make_model()
    reg = _make_registry()
    for verb in ("extract", "import"):
        result = await dispatch_mutation(model, reg, f"{verb} foo @file:server.py")
        assert "unknown verb" in result
