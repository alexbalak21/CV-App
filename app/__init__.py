import os
from pathlib import Path

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader

from config import CONFIG_MAP
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_CONFIG", "dev")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIG_MAP[config_name])
    if overrides:
        app.config.update(overrides)

    Path(app.config["PHOTOS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["CV_TEMPLATES_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # CV templates each live as a self-contained package under
    # app/storage/cv_templates/<slug>/ (page.html + style.css + any future
    # assets), outside the normal app/templates/ tree. A ChoiceLoader lets
    # render_template()/{% include %} find "cv_templates/<slug>/page.html"
    # there too, in addition to the app's own chrome templates — Jinja
    # tries each loader in order and uses the first one that resolves the
    # path, so nothing about existing template lookups changes.
    templates_parent_dir = Path(app.config["CV_TEMPLATES_DIR"]).parent
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        FileSystemLoader(str(templates_parent_dir)),
    ])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models  # noqa: F401  (ensure models are registered before migrations)

    from app.auth.routes import auth_bp
    from app.cvs.routes import cvs_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cvs_bp, url_prefix="/cvs")

    from app.services.cv_renderer import cv_inline_filter, contact_icon_class, link_icon_class
    app.jinja_env.filters["cv_inline"] = cv_inline_filter
    app.jinja_env.filters["contact_icon_class"] = contact_icon_class
    app.jinja_env.filters["link_icon_class"] = link_icon_class

    @app.cli.command("seed-templates")
    def seed_templates_command():
        """Seed the templates table with the built-in CV templates."""
        from scripts.seed_templates import run
        run()
        print("Templates seeded.")

    return app
