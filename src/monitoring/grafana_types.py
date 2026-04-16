"""Typed JSON aliases for Grafana payload builders."""

from __future__ import annotations

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
GrafanaPayload = dict[str, JsonValue]

__all__ = [
    "GrafanaPayload",
    "JsonValue",
]
