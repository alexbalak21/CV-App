from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# Make sure SQLite actually enforces foreign keys (off by default).
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow)
    is_active_flag = db.Column("is_active", db.Boolean, default=True)

    cvs = db.relationship(
        "CV", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="CV.user_id",
    )

    # Flask-Login expects `is_active` as a property/attribute.
    @property
    def is_active(self):
        return self.is_active_flag

    def __repr__(self):
        return f"<User {self.email}>"


class Template(db.Model):
    __tablename__ = "templates"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    thumbnail_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Template {self.slug}>"


class CV(db.Model):
    __tablename__ = "cvs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), nullable=False)
    default_template_id = db.Column(db.Integer, db.ForeignKey("templates.id"))
    current_version_id = db.Column(
        db.Integer, db.ForeignKey("cv_versions.id", use_alter=True, name="fk_cv_current_version")
    )
    lang = db.Column(db.String(5), default="fr")
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="cvs", foreign_keys=[user_id])
    default_template = db.relationship("Template")
    versions = db.relationship(
        "CVVersion",
        back_populates="cv",
        foreign_keys="CVVersion.cv_id",
        cascade="all, delete-orphan",
        order_by="CVVersion.version_number",
    )
    current_version = db.relationship("CVVersion", foreign_keys=[current_version_id], post_update=True)

    __table_args__ = (db.UniqueConstraint("user_id", "slug", name="uq_user_cv_slug"),)

    def __repr__(self):
        return f"<CV {self.title!r} user={self.user_id}>"


class CVVersion(db.Model):
    __tablename__ = "cv_versions"

    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(db.Integer, db.ForeignKey("cvs.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    label = db.Column(db.String(255), nullable=True)
    is_autosave = db.Column(db.Boolean, default=False)

    cv = db.relationship("CV", back_populates="versions", foreign_keys=[cv_id])
    photo = db.relationship("Photo")

    __table_args__ = (
        db.UniqueConstraint("cv_id", "version_number", name="uq_cv_version_number"),
    )

    def __repr__(self):
        return f"<CVVersion cv={self.cv_id} v{self.version_number}>"


class Photo(db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    storage_path = db.Column(db.String(255), nullable=False)
    variant = db.Column(db.String(10), nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    filesize_bytes = db.Column(db.Integer)
    original_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)

    def __repr__(self):
        return f"<Photo {self.id} user={self.user_id}>"
