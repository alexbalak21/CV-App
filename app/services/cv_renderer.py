"""
cv_renderer — Python port of the PHP prototype's Renderer::inline().

Handles the CV content's lightweight inline syntax:
    **bold**              -> <strong>bold</strong>
    [fa:solid:xxx]         -> <i class="fa-solid fa-xxx"></i>
    [fa:brands:xxx]        -> <i class="fa-brands fa-xxx"></i>

Exposed as the Jinja filter `cv_inline`, used throughout the CV templates
(e.g. `{{ cv.profile.text | cv_inline }}`) instead of Jinja's default
auto-escaping, since these strings are user-authored "trusted-ish" content
that intentionally contains a tiny whitelist of markup.
"""
import re
from html import escape
from markupsafe import Markup

_FA_RE = re.compile(r"\[fa:(brands|solid|regular):([a-z0-9\-]+)\]", re.IGNORECASE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_SLOT_RE = re.compile(r"§§(\d+)§§")


def cv_inline(text: str) -> Markup:
    """Escape HTML, then restore FA icon tags and apply **bold**."""
    if text is None:
        return Markup("")
    text = str(text)

    slots: list[str] = []

    def _stash_fa(match: re.Match) -> str:
        family, icon = match.group(1).lower(), match.group(2).lower()
        html = f'<i class="fa-{family} fa-{icon}"></i>'
        slots.append(html)
        return f"§§{len(slots) - 1}§§"

    text = _FA_RE.sub(_stash_fa, text)
    text = escape(text)

    def _restore_fa(match: re.Match) -> str:
        idx = int(match.group(1))
        return slots[idx] if idx < len(slots) else match.group(0)

    text = _SLOT_RE.sub(_restore_fa, text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)

    return Markup(text)


# Alias kept for use outside Jinja (e.g. server-side rendering, tests).
cv_inline_filter = cv_inline


_CONTACT_ICON_MAP = {
    "téléphone": "fa-phone", "phone": "fa-phone",
    "email": "fa-envelope",
    "localisation": "fa-location-dot", "location": "fa-location-dot",
    "date de naissance": "fa-cake-candles", "birthday": "fa-cake-candles",
    "permis": "fa-car", "license": "fa-car", "driving": "fa-car",
}

_LINK_ICON_MAP = {
    "linkedin": "fa-brands fa-linkedin",
    "github": "fa-brands fa-github",
    "twitter": "fa-brands fa-x-twitter",
    "site web": "fa-solid fa-globe",
    "website": "fa-solid fa-globe",
    "portfolio": "fa-solid fa-globe",
}


def contact_icon_class(label: str) -> str:
    key = (label or "").strip().lower()
    return _CONTACT_ICON_MAP.get(key, "fa-circle-dot")


def link_icon_class(label: str) -> str:
    label = (label or "").lower()
    for needle, cls in _LINK_ICON_MAP.items():
        if needle in label:
            return cls
    return "fa-solid fa-globe"
