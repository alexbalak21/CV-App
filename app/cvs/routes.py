import os
import re
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort,
    current_app, send_from_directory,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import CV, CVVersion, Template
from app.cvs.forms import CreateCVForm
from app.cv_schema import blank_cv_data, normalize_cv_data
from app.services.cv_renderer import cv_inline_filter  # noqa: F401 (used via jinja filter, kept for clarity)
from app.services.photo_service import (
    process_and_save_photo, PhotoTooLarge, PhotoInvalidFormat
)

cvs_bp = Blueprint("cvs", __name__, template_folder="../templates/cvs")


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "cv"


def _unique_slug_for_user(user_id: int, title: str) -> str:
    base = _slugify(title)
    slug = base
    counter = 2
    while CV.query.filter_by(user_id=user_id, slug=slug).first() is not None:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def owns_cv(view_func):
    """Loads the CV by id from the route and 404s if it doesn't belong to
    the current user (404, not 403, to avoid leaking existence)."""
    @wraps(view_func)
    def wrapper(cv_id, *args, **kwargs):
        cv = CV.query.filter_by(id=cv_id, user_id=current_user.id, deleted_at=None).first()
        if cv is None:
            abort(404)
        return view_func(cv, *args, **kwargs)
    return wrapper


@cvs_bp.route("/")
@login_required
def list_cvs():
    cvs = (
        CV.query.filter_by(user_id=current_user.id, deleted_at=None)
        .order_by(CV.updated_at.desc())
        .all()
    )
    return render_template("cvs/list.html", cvs=cvs)


@cvs_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_cv():
    form = CreateCVForm()
    templates = Template.query.filter_by(is_active=True).all()
    form.template_slug.choices = [(t.slug, t.name) for t in templates]

    if form.validate_on_submit():
        template = Template.query.filter_by(slug=form.template_slug.data).first()

        cv = CV(
            user_id=current_user.id,
            title=form.title.data.strip(),
            slug=_unique_slug_for_user(current_user.id, form.title.data),
            default_template_id=template.id if template else None,
        )
        db.session.add(cv)
        db.session.flush()  # get cv.id before creating the first version

        version = CVVersion(
            cv_id=cv.id,
            version_number=1,
            data=blank_cv_data(),
            created_by_user_id=current_user.id,
            label="Version initiale",
        )
        db.session.add(version)
        db.session.flush()

        cv.current_version_id = version.id
        db.session.commit()

        flash(f"CV « {cv.title} » créé.", "success")
        return redirect(url_for("cvs.edit_cv", cv_id=cv.id))

    return render_template("cvs/new.html", form=form, templates=templates)


@cvs_bp.route("/<int:cv_id>/edit")
@login_required
@owns_cv
def edit_cv(cv: CV):
    templates = Template.query.filter_by(is_active=True).all()
    data = normalize_cv_data(cv.current_version.data if cv.current_version else blank_cv_data())
    template_slug = _resolve_template_slug(cv, None)
    return render_template(
        "cvs/edit.html", cv=cv, cv_data=data, templates=templates, template_slug=template_slug
    )


@cvs_bp.route("/<int:cv_id>/save", methods=["POST"])
@login_required
@owns_cv
def save_cv(cv: CV):
    payload = request.get_json(silent=True) or {}
    data = normalize_cv_data(payload.get("data") or {})
    label = (payload.get("label") or "").strip() or None

    last_version = (
        CVVersion.query.filter_by(cv_id=cv.id).order_by(CVVersion.version_number.desc()).first()
    )
    next_number = (last_version.version_number + 1) if last_version else 1

    version = CVVersion(
        cv_id=cv.id,
        version_number=next_number,
        data=data,
        created_by_user_id=current_user.id,
        label=label,
    )
    db.session.add(version)
    db.session.flush()

    cv.current_version_id = version.id
    db.session.commit()

    return jsonify({"ok": True, "version_id": version.id, "version_number": version.version_number})


def _resolve_template_slug(cv: CV, requested_slug: str | None) -> str:
    """Only ever return a slug that exists and is active in the templates
    table — never trust a query-string/body value directly in a
    render_template() path."""
    if requested_slug:
        match = Template.query.filter_by(slug=requested_slug, is_active=True).first()
        if match:
            return match.slug
    if cv.default_template and cv.default_template.is_active:
        return cv.default_template.slug
    fallback = Template.query.filter_by(is_active=True).first()
    return fallback.slug if fallback else "classic_sidebar"


@cvs_bp.route("/template-assets/<slug>/<path:filename>")
def serve_template_asset(slug, filename):
    """
    Serves a CV template package's static files (style.css, thumbnails,
    etc.) from app/storage/cv_templates/<slug>/.

    These live outside app/static/, so url_for('static', ...) can't reach
    them — this route stands in for that. `slug` is validated against the
    templates table first (same pattern as _resolve_template_slug) so this
    isn't an open "read any file under storage/" endpoint; send_from_directory
    additionally guards `filename` against path traversal on top of that.
    Deliberately not behind @login_required: CSS/thumbnails aren't
    sensitive, and this keeps <link>/<img> tags simple in every template.
    """
    if not Template.query.filter_by(slug=slug, is_active=True).first():
        abort(404)
    return send_from_directory(
        os.path.join(current_app.config["CV_TEMPLATES_DIR"], slug), filename
    )


@cvs_bp.route("/<int:cv_id>/render-preview", methods=["POST"])
@login_required
@owns_cv
def render_preview(cv: CV):
    payload = request.get_json(silent=True) or {}
    data = normalize_cv_data(payload.get("data") or {})
    template_slug = _resolve_template_slug(cv, payload.get("template"))

    html = render_template(f"cv_templates/{template_slug}/page.html", cv=data)
    return jsonify({"html": html})


@cvs_bp.route("/<int:cv_id>/photo", methods=["POST"])
@login_required
@owns_cv
def upload_photo(cv: CV):
    if "photo" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    variant = request.form.get("variant", "200")

    try:
        photo = process_and_save_photo(
            request.files["photo"],
            user_id=current_user.id,
            max_upload_bytes=current_app.config["PHOTO_MAX_UPLOAD_BYTES"],
            photos_dir=current_app.config["PHOTOS_DIR"],
            variant=variant,
        )
    except PhotoTooLarge:
        return jsonify({"error": "Fichier trop volumineux (1 Mo max)"}), 413
    except PhotoInvalidFormat as exc:
        return jsonify({"error": f"Format non supporté : {exc}"}), 415

    return jsonify({"ok": True, "photo_id": photo.id, "url": url_for("cvs.serve_photo", photo_id=photo.id)})


@cvs_bp.route("/photos/<int:photo_id>")
@login_required
def serve_photo(photo_id):
    from app.models import Photo

    photo = Photo.query.get_or_404(photo_id)
    if photo.user_id != current_user.id:
        abort(404)
    # Defensive: older rows created before the storage_path fix may have
    # been saved with OS-native (backslash) separators on Windows, which
    # Werkzeug's safe_join()/send_from_directory() rejects outright. New
    # uploads always store forward slashes (see photo_service.py), but we
    # normalize here too so already-uploaded photos don't 404 forever.
    normalized_path = photo.storage_path.replace("\\", "/")
    return send_from_directory(current_app.config["PHOTOS_DIR"], normalized_path)


@cvs_bp.route("/<int:cv_id>/versions")
@login_required
@owns_cv
def list_versions(cv: CV):
    versions = (
        CVVersion.query.filter_by(cv_id=cv.id, is_autosave=False)
        .order_by(CVVersion.version_number.desc())
        .all()
    )
    return render_template("cvs/versions.html", cv=cv, versions=versions)


@cvs_bp.route("/<int:cv_id>/versions/<int:version_id>/restore", methods=["POST"])
@login_required
@owns_cv
def restore_version(cv: CV, version_id: int):
    old_version = CVVersion.query.filter_by(id=version_id, cv_id=cv.id).first_or_404()

    last_version = (
        CVVersion.query.filter_by(cv_id=cv.id).order_by(CVVersion.version_number.desc()).first()
    )
    next_number = (last_version.version_number + 1) if last_version else 1

    new_version = CVVersion(
        cv_id=cv.id,
        version_number=next_number,
        data=old_version.data,
        photo_id=old_version.photo_id,
        created_by_user_id=current_user.id,
        label=f"Restauré depuis la version {old_version.version_number}",
    )
    db.session.add(new_version)
    db.session.flush()
    cv.current_version_id = new_version.id
    db.session.commit()

    flash(f"Version {old_version.version_number} restaurée (nouvelle version {next_number}).", "success")
    return redirect(url_for("cvs.edit_cv", cv_id=cv.id))


@cvs_bp.route("/<int:cv_id>/view")
@login_required
@owns_cv
def view_cv(cv: CV):
    template_slug = _resolve_template_slug(cv, request.args.get("template"))
    data = normalize_cv_data(cv.current_version.data if cv.current_version else blank_cv_data())
    templates = Template.query.filter_by(is_active=True).all()
    return render_template(
        "cvs/view.html", cv=cv, cv_data=data, template_slug=template_slug, templates=templates
    )


@cvs_bp.route("/<int:cv_id>/versions/<int:version_id>/view")
@login_required
@owns_cv
def view_version(cv: CV, version_id: int):
    version = CVVersion.query.filter_by(id=version_id, cv_id=cv.id).first_or_404()
    template_slug = _resolve_template_slug(cv, request.args.get("template"))
    data = normalize_cv_data(version.data)
    return render_template(
        "cvs/view.html", cv=cv, cv_data=data, template_slug=template_slug,
        templates=Template.query.filter_by(is_active=True).all(), pinned_version=version,
    )


@cvs_bp.route("/<int:cv_id>/delete", methods=["POST"])
@login_required
@owns_cv
def delete_cv(cv: CV):
    from datetime import datetime, timezone
    cv.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"CV « {cv.title} » supprimé.", "info")
    return redirect(url_for("cvs.list_cvs"))
