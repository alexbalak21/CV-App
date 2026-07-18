from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    display_name = StringField("Nom affiché", validators=[Length(max=120)])
    password = PasswordField(
        "Mot de passe", validators=[DataRequired(), Length(min=8, message="8 caractères minimum.")]
    )
    confirm_password = PasswordField(
        "Confirmer le mot de passe",
        validators=[DataRequired(), EqualTo("password", message="Les mots de passe ne correspondent pas.")],
    )
    submit = SubmitField("Créer mon compte")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")
