"""
The real ANALYTICS extracts spell countries out in full (COUNTRY="Malawi"),
while Wimbi's RBAC and DIM_COUNTRY both key off ISO-2 codes. Small, explicit
mapping rather than guessing — extend as more countries' data lands.

Also covers non-standard values seen in the real SuccessFactors extract's
CountryCode field (e.g. "RW-TBR" — a Rwanda/Tubura sub-entity code, "ETH" —
3-letter instead of ISO-2) — same lookup, same reasoning.
"""

_NAME_TO_ISO = {
    "malawi": "MW",
    "kenya": "KE",
    "rwanda": "RW",
    "zambia": "ZM",
    "tanzania": "TZ",
    "uganda": "UG",
    "nigeria": "NG",
    "ethiopia": "ET",
    "democratic republic of congo": "CD",
    "drc": "CD",
    "burundi": "BI",
    "ghana": "GH",
    # SuccessFactors CountryCode quirks (verified 2026-09-01)
    "rw-tbr": "RW",
    "eth": "ET",
}


def to_iso(country_name: str | None) -> str:
    if not country_name:
        return ""
    key = country_name.strip().lower()
    if key in _NAME_TO_ISO:
        return _NAME_TO_ISO[key]
    # Already an ISO-ish code, or unrecognized — pass through rather than
    # silently dropping data; worth a look if this ever shows up in the UI.
    return country_name.strip().upper()
