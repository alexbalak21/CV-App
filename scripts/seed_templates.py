"""
scripts/seed_templates.py

Seeds/updates the `templates` table from a static registry of built-in
templates. Safe to re-run (upserts by slug). Invoked via:

    flask seed-templates
"""
from app.extensions import db
from app.models import Template

BUILTIN_TEMPLATES = [
    {
        "slug": "classic_sidebar",
        "name": "Classic Sidebar",
        "description": "Mise en page à deux colonnes avec barre latérale bleue — le modèle original.",
        "thumbnail_path": "cv_templates/classic_sidebar/thumbnail.png",
    },
    {
        "slug": "ats_cv",
        "name": "ATS Friendly",
        "description": "Colonne unique, sans icônes ni mise en page complexe — optimisé pour les lecteurs ATS.",
        "thumbnail_path": "cv_templates/ats_cv/thumbnail.png",
    },
    # Add more templates here as they're built (Phase 3 of plan.md):
    # {"slug": "minimal", "name": "Minimal", ...},
    # {"slug": "two_column_timeline", "name": "Two Column Timeline", ...},
]


def run():
    for entry in BUILTIN_TEMPLATES:
        existing = Template.query.filter_by(slug=entry["slug"]).first()
        if existing:
            existing.name = entry["name"]
            existing.description = entry["description"]
            existing.thumbnail_path = entry["thumbnail_path"]
            existing.is_active = True
        else:
            db.session.add(Template(**entry, is_active=True))
    db.session.commit()


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run()
        print("Templates seeded.")
