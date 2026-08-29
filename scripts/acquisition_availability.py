"""Conservative acquisition-window and prerequisite evaluation.

Acquisition ``prerequisites`` also contain route-description metadata.  Keep
that metadata visible, but never treat a true gate as satisfied merely because
its checkpoint window has opened.
"""

from __future__ import annotations


ROUTE_CONDITION_KEYS = frozenset({
    "access", "arena", "boss", "cup", "defeat_blocking_troll", "event",
    "interaction", "item", "items", "key", "key_item", "mini_medals",
    "npc", "puzzle", "quest", "story", "story_segment", "story_window",
    "timing", "turn_limit",
})


def _medal_status(state: dict, required: int) -> tuple[str, str]:
    completion = state.get("completion", {})
    explicit = completion.get("mini_medal_count")
    numbered = completion.get("mini_medals_found", [])
    numbered_count = len(numbered) if isinstance(numbered, list) else 0
    if isinstance(explicit, int) and not isinstance(explicit, bool):
        if numbered_count > explicit and max(explicit, numbered_count) < required:
            return ("unknown", f"Mini Medal records disagree ({explicit} total; "
                    f"{numbered_count} numbered; {required} needed)")
        known = max(explicit, numbered_count)
        return (("satisfied" if known >= required else "unmet"),
                f"Mini Medals: {known}/{required} explicitly recorded")
    if numbered_count >= required:
        return ("satisfied",
                f"Mini Medals: {numbered_count}/{required} numbered medals recorded")
    return ("unknown",
            f"Mini Medal count unknown ({numbered_count} numbered recorded; {required} needed)")


def prerequisite_status(prerequisites: dict | None, state: dict | None) -> dict:
    prerequisites = prerequisites if isinstance(prerequisites, dict) else {}
    gate_keys = ["mini_medals"] if "mini_medals" in prerequisites else []
    condition_keys = sorted(ROUTE_CONDITION_KEYS.intersection(prerequisites)
                            - {"mini_medals"})
    if not gate_keys:
        return {"status": "not_applicable", "reason": "No progression gate recorded",
                "gate_keys": [], "route_condition_keys": condition_keys}
    checks = []
    if "mini_medals" in gate_keys:
        required = prerequisites["mini_medals"]
        if (state is not None and isinstance(required, int)
                and not isinstance(required, bool)):
            checks.append(_medal_status(state, required))
        else:
            checks.append(("not_state_evaluable",
                           f"Mini Medal threshold {required!r} is not evaluated"))
    statuses = {status for status, _ in checks}
    if "unmet" in statuses:
        status = "unmet"
    elif statuses == {"satisfied"}:
        status = "satisfied"
    elif "unknown" in statuses:
        status = "unknown"
    else:
        status = "not_state_evaluable"
    return {"status": status, "reason": "; ".join(reason for _, reason in checks),
            "gate_keys": gate_keys, "route_condition_keys": condition_keys}


def route_availability(window_status: str, prerequisites: dict | None,
                       state: dict | None = None) -> dict:
    prerequisite = prerequisite_status(prerequisites, state)
    if window_status in {"later", "expired", "invalid", "unknown"}:
        availability = "unavailable" if window_status in {"later", "expired"} else "unknown"
    elif prerequisite["status"] in {"not_applicable", "satisfied"}:
        availability = "available_now"
    elif prerequisite["status"] == "unmet":
        availability = "unavailable"
    else:
        availability = "conditionally_available"
    return {"window_status": window_status,
            "prerequisite_status": prerequisite["status"],
            "availability_status": availability,
            "availability_reason": prerequisite["reason"],
            "gate_keys": prerequisite["gate_keys"],
            "route_condition_keys": prerequisite["route_condition_keys"]}
