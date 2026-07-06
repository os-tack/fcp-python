"""Verb registration for fcp-python."""

from __future__ import annotations

from fcp_core import VerbRegistry, VerbSpec


def register_query_verbs(registry: VerbRegistry) -> None:
    registry.register_many([
        VerbSpec(verb="find", syntax="find QUERY [kind:KIND]", category="navigation"),
        VerbSpec(verb="def", syntax="def SYMBOL [@selectors...]", category="navigation"),
        VerbSpec(verb="refs", syntax="refs SYMBOL [@selectors...]", category="navigation"),
        VerbSpec(verb="symbols", syntax="symbols PATH [kind:KIND]", category="navigation"),
        VerbSpec(verb="diagnose", syntax="diagnose [PATH] [@all]", category="inspection"),
        VerbSpec(verb="inspect", syntax="inspect SYMBOL [@selectors...]", category="inspection"),
        VerbSpec(verb="callers", syntax="callers SYMBOL [@selectors...]", category="inspection"),
        VerbSpec(verb="callees", syntax="callees SYMBOL [@selectors...]", category="inspection"),
        VerbSpec(verb="impl", syntax="impl SYMBOL [@selectors...]", category="navigation"),
        VerbSpec(verb="map", syntax="map", category="inspection"),
        VerbSpec(verb="unused", syntax="unused [@file:PATH]", category="inspection"),
    ])


def register_mutation_verbs(registry: VerbRegistry) -> None:
    registry.register_many([
        VerbSpec(verb="rename", syntax="rename SYMBOL NEW_NAME [@selectors...]", category="mutation"),
    ])


def register_session_verbs(registry: VerbRegistry) -> None:
    registry.register_many([
        VerbSpec(verb="open", syntax="open PATH", category="session"),
        VerbSpec(verb="status", syntax="status", category="session"),
        VerbSpec(verb="close", syntax="close", category="session"),
    ])
