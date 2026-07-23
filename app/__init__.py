import os
from pathlib import Path

from flask import Flask

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

    @app.cli.command("seed-templates")
    def seed_templates_command():
        """Seed the templates table with the built-in CV templates."""
        from scripts.seed_templates import run
        run()
        print("Templates seeded.")

    return app
