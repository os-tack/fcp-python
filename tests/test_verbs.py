"""Tests for verb registration."""

from fcp_core import VerbRegistry

from fcp_python.domain.verbs import (
    register_mutation_verbs,
    register_query_verbs,
    register_session_verbs,
)


def test_register_query_verbs():
    reg = VerbRegistry()
    register_query_verbs(reg)
    for name in ["find", "def", "refs", "symbols", "diagnose", "inspect", "callers", "callees", "impl", "map", "unused"]:
        assert reg.lookup(name) is not None, f"missing query verb: {name}"


def test_register_session_verbs():
    reg = VerbRegistry()
    register_session_verbs(reg)
    for name in ["open", "status", "close"]:
        assert reg.lookup(name) is not None, f"missing session verb: {name}"


def test_query_verb_count():
    reg = VerbRegistry()
    register_query_verbs(reg)
    assert len(reg.verbs) == 11


def test_session_verb_count():
    reg = VerbRegistry()
    register_session_verbs(reg)
    assert len(reg.verbs) == 3


def test_register_mutation_verbs():
    reg = VerbRegistry()
    register_mutation_verbs(reg)
    for name in ["rename"]:
        assert reg.lookup(name) is not None, f"missing mutation verb: {name}"


def test_mutation_verb_count():
    reg = VerbRegistry()
    register_mutation_verbs(reg)
    assert len(reg.verbs) == 1


def test_reference_card_has_categories():
    reg = VerbRegistry()
    register_query_verbs(reg)
    register_mutation_verbs(reg)
    register_session_verbs(reg)
    card = reg.generate_reference_card()
    assert "NAVIGATION:" in card
    assert "INSPECTION:" in card
    assert "MUTATION:" in card
    assert "SESSION:" in card


def test_all_verbs_registered():
    reg = VerbRegistry()
    register_query_verbs(reg)
    register_mutation_verbs(reg)
    register_session_verbs(reg)
    assert len(reg.verbs) == 15  # 11 query + 1 mutation + 3 session
