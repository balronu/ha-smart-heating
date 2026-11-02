"""Conservative, read-only classification of window sensor states."""

UNKNOWN = {"unknown", "unbekannt", "unavailable", "nicht verfügbar", "missing", "none", ""}
OPEN = {"open", "opened", "offen"}
TILTED = {"tilt", "tilted", "gekippt", "gekipp", "gekippte"}
AMBIGUOUS = {"on", "true", "1"}
CLOSED = {"off", "false", "0", "closed", "geschlossen"}


def classify_window_detail(states):
    """Prefer explicit open evidence; never interpret a binary 'on' as tilt.

    Unknown inputs block a closed/tilted conclusion, but an explicit open
    report still proves an open window. All other combinations remain unknown
    unless the observed states prove a more specific classification.
    """
    values = [str(value).strip().lower() for value in states]
    if not values:
        return "unknown"
    if any(value in OPEN for value in values):
        return "open"
    if any(value in AMBIGUOUS for value in values):
        return "open_or_tilted"
    if any(value in UNKNOWN or value not in OPEN | TILTED | AMBIGUOUS | CLOSED for value in values):
        return "unknown"
    if any(value in TILTED for value in values):
        return "tilted"
    if all(value in CLOSED for value in values):
        return "closed"
    return "unknown"
