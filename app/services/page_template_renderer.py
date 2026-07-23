"""
page_template_renderer — renders a CV template package's page.html by
substituting {{PLACEHOLDER}} tokens with pre-built HTML fragments.

This is deliberately NOT Jinja-based. A template author writes page.html
as a completely ordinary, self-contained HTML file — the kind you can
open directly in a browser or a live-preview editor and see the layout —
referencing a sibling `style.css` (and, optionally, `photo.jpg` as a
stand-in you can drop in for local preview). The only special syntax is
the `{{TOKEN}}` placeholders themselves, which just look like inert text
until this module substitutes them; there's no {% for %}/{% if %} or any
other engine-specific syntax to learn.

Available tokens (see build_placeholder_map): FULL_NAME, JOB_TITLE, LINKS,
CONTACT_TITLE, CONTACT, SKILLS_TITLE, SKILLS, CERTIFICATIONS_TITLE,
CERTIFICATIONS, LANGUAGES_TITLE, LANGUAGES, HOBBIES_TITLE, HOBBIES,
PROFILE_TITLE, PROFILE, EXPERIENCE_TITLE, EXPERIENCE, EDUCATION_TITLE,
EDUCATION.
"""
import re

from app.services.cv_renderer import cv_inline, contact_icon_class, link_icon_class

_STYLE_HREF_RE = re.compile(r'href=(["\'])style\.css\1')
_PHOTO_SRC_RE = re.compile(r'src=(["\'])photo\.jpg\1')
_TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def _build_links_html(links: list) -> str:
    parts = []
    for link in links:
        icon_class = link_icon_class(link.get("label", ""))
        parts.append(
            f'<a href="{link.get("url", "")}" target="_blank">'
            f'<span class="icon"><i class="{icon_class}"></i></span> '
            f'{cv_inline(link.get("text", ""))}</a>'
        )
    return "\n".join(parts)


def _build_contact_html(items: list) -> str:
    parts = []
    for item in items:
        icon_class = contact_icon_class(item.get("label", ""))
        text = cv_inline(item.get("display", ""))
        href = (item.get("href") or "").strip()
        content = f'<a href="{href}">{text}</a>' if href else text
        parts.append(
            '<div class="contact-item"><span class="icon">'
            f'<i class="fa-solid {icon_class}"></i></span> {content}</div>'
        )
    return "\n".join(parts)


def _build_simple_list_html(items: list, no_bullets: bool = False) -> str:
    cls = ' class="no-bullets"' if no_bullets else ""
    lis = "\n".join(f"<li>{cv_inline(item)}</li>" for item in items)
    return f"<ul{cls}>\n{lis}\n</ul>"


def _build_languages_html(items: list) -> str:
    parts = []
    for item in items:
        parts.append(
            '<div class="lang-item">'
            f'<span class="lang-name">{cv_inline(item.get("name", ""))}</span>'
            f'<span class="lang-level">{cv_inline(item.get("level", ""))}</span>'
            "</div>"
        )
    return "\n".join(parts)


def _build_timeline_html(items: list) -> str:
    parts = []
    for item in items:
        bullets = item.get("bullets") or []
        bullets_html = ""
        if bullets:
            lis = "\n".join(f"<li>{cv_inline(b)}</li>" for b in bullets)
            bullets_html = f"<ul>\n{lis}\n</ul>"
        parts.append(
            '<div class="timeline-item">'
            f'<h4 class="job-title">{cv_inline(item.get("title", ""))}</h4>'
            f'<p class="job-meta">{cv_inline(item.get("meta", ""))}</p>'
            f"{bullets_html}"
            "</div>"
        )
    return "\n".join(parts)


def build_placeholder_map(data: dict) -> dict:
    header = data.get("header") or {}
    contact = data.get("contact") or {}
    skills = data.get("skills") or {}
    certifications = data.get("certifications") or {}
    languages = data.get("languages") or {}
    hobbies = data.get("hobbies") or {}
    profile = data.get("profile") or {}
    experience = data.get("experience") or {}
    education = data.get("education") or {}

    return {
        "FULL_NAME": cv_inline(header.get("fullName", "")),
        "JOB_TITLE": cv_inline(header.get("jobTitle", "")),
        "LINKS": _build_links_html(header.get("links") or []),
        "CONTACT_TITLE": cv_inline(contact.get("title", "Contact")),
        "CONTACT": _build_contact_html(contact.get("items") or []),
        "SKILLS_TITLE": cv_inline(skills.get("title", "Compétences")),
        "SKILLS": _build_simple_list_html(skills.get("items") or []),
        "CERTIFICATIONS_TITLE": cv_inline(certifications.get("title", "Certifications")),
        "CERTIFICATIONS": _build_simple_list_html(certifications.get("items") or [], no_bullets=True),
        "LANGUAGES_TITLE": cv_inline(languages.get("title", "Langues")),
        "LANGUAGES": _build_languages_html(languages.get("items") or []),
        "HOBBIES_TITLE": cv_inline(hobbies.get("title", "Intérêts")),
        "HOBBIES": _build_simple_list_html(hobbies.get("items") or [], no_bullets=True),
        "PROFILE_TITLE": cv_inline(profile.get("title", "Profil")),
        "PROFILE": f"<p>{cv_inline(profile.get('text', ''))}</p>",
        "EXPERIENCE_TITLE": cv_inline(experience.get("title", "Expériences Professionnelles")),
        "EXPERIENCE": _build_timeline_html(experience.get("items") or []),
        "EDUCATION_TITLE": cv_inline(education.get("title", "Formations")),
        "EDUCATION": _build_timeline_html(education.get("items") or []),
    }


def render_page(page_html: str, data: dict, style_url: str) -> str:
    """
    Renders a full CV page from a raw page.html string:
    - resolves the sibling style.css reference to its real served URL
    - resolves (or hides) the photo.jpg placeholder based on the CV's data
    - substitutes every {{TOKEN}} with its built HTML fragment
    """
    html = page_html

    html = _STYLE_HREF_RE.sub(
        lambda m: f"href={m.group(1)}{style_url}{m.group(1)}", html, count=1
    )

    photo_url = ((data.get("header") or {}).get("photo") or "").strip()
    if photo_url:
        html = _PHOTO_SRC_RE.sub(
            lambda m: f"src={m.group(1)}{photo_url}{m.group(1)}", html, count=1
        )
    else:
        # No photo set: hide whatever element wraps the photo placeholder
        # instead of leaving a broken-image icon. Template authors don't
        # need any special conditional syntax for this — any element with
        # id="photo-container" is hidden automatically when there's no photo.
        html = html.replace(
            "</head>", "<style>#photo-container{display:none}</style>\n</head>", 1
        )

    placeholders = build_placeholder_map(data)
    html = _TOKEN_RE.sub(lambda m: placeholders.get(m.group(1), m.group(0)), html)
    return html
