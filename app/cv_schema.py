"""
Canonical shape of a CV version's `data` JSON blob.
Mirrors the PHP prototype's profile JSON files 1:1 so the editor UI and
the cv_renderer service can stay close ports of the original.
"""

def blank_cv_data() -> dict:
    return {
        "header": {"fullName": "", "jobTitle": "", "photo": "", "links": []},
        "profile": {"title": "Profil", "text": ""},
        "contact": {"title": "Contact", "items": []},
        "skills": {"title": "Compétences", "items": []},
        "certifications": {"title": "Certifications", "items": []},
        "languages": {"title": "Langues", "items": []},
        "hobbies": {"title": "Intérêts", "items": []},
        "experience": {"title": "Expériences Professionnelles", "items": []},
        "education": {"title": "Formations", "items": []},
    }


REQUIRED_TOP_LEVEL_KEYS = set(blank_cv_data().keys())


def normalize_cv_data(data: dict) -> dict:
    """Fill in any missing top-level sections with blank defaults so the
    renderer / template layer never has to guard against missing keys."""
    base = blank_cv_data()
    if not isinstance(data, dict):
        return base
    for key, default_value in base.items():
        incoming = data.get(key)
        if isinstance(incoming, dict) and isinstance(default_value, dict):
            merged = {**default_value, **incoming}
            base[key] = merged
        elif incoming is not None:
            base[key] = incoming
    return base
