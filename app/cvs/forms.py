from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired, Length


class CreateCVForm(FlaskForm):
    title = StringField("Titre du CV", validators=[DataRequired(), Length(max=160)])
    template_slug = SelectField("Modèle", choices=[], validators=[DataRequired()])
