"""Read-only cleanup planning for legacy Smart Heating instances."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .const import DOMAIN


def build_cleanup_plan(
    entries: Iterable[Mapping[str, Any]],
    entities: Iterable[Mapping[str, Any]],
    *,
    keep_entry_id: str | None = None,
    protected_entity_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Classify exact Smart Heating ownership without deleting anything."""
    protected = set(protected_entity_ids)
    smart_entries = [dict(entry) for entry in entries if entry.get("domain") == DOMAIN]
    duplicate_entries = []
    if keep_entry_id:
        duplicate_entries = [
            entry["entry_id"] for entry in smart_entries
            if entry.get("entry_id") != keep_entry_id and entry.get("entry_id")
        ]
    owned, retained = [], []
    owner_ids = {entry.get("entry_id") for entry in smart_entries}
    for raw in entities:
        entity = dict(raw)
        is_owned = entity.get("platform") == DOMAIN and entity.get("config_entry_id") in owner_ids
        if is_owned and entity.get("entity_id") not in protected:
            owned.append(entity)
        else:
            retained.append(entity)
    return {
        "domain": DOMAIN,
        "keep_entry_id": keep_entry_id,
        "duplicate_entry_ids": sorted(duplicate_entries),
        "native_owned_entities": owned,
        "retained_entities": retained,
        "requires_explicit_approval": bool(duplicate_entries or owned),
    }
