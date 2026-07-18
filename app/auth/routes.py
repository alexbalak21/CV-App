from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.extensions import db, login_manager
from app.models import User
from app.auth.forms import RegisterForm, LoginForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

ph = PasswordHasher()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("cvs.list_cvs"))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing:
            flash("Un compte existe déjà avec cet email.", "error")
            return render_template("auth/register.html", form=form)

        user = User(
            email=form.email.data.lower().strip(),
            display_name=form.display_name.data.strip() or None,
            password_hash=ph.hash(form.password.data),
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Compte créé avec succès.", "success")
        return redirect(url_for("cvs.list_cvs"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("cvs.list_cvs"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user is None:
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("auth/login.html", form=form)

        try:
            ph.verify(user.password_hash, form.password.data)
        except VerifyMismatchError:
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("auth/login.html", form=form)

        if ph.check_needs_rehash(user.password_hash):
            user.password_hash = ph.hash(form.password.data)
            db.session.commit()

        login_user(user)
        next_url = request.args.get("next")
        return redirect(next_url or url_for("cvs.list_cvs"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("auth.login"))
