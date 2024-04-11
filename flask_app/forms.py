from flask_wtf import FlaskForm
from wtforms.fields.datetime import DateField
from wtforms.fields.simple import BooleanField, SubmitField, StringField
from wtforms.validators import DataRequired


class VerificationForm(FlaskForm):
    verified = BooleanField('Verified?')
    submit = SubmitField('Mark as Verified')
    csrf_enabled = True  # Enable CSRF protection in the form


class IncidentForm(FlaskForm):
    incident_reported_date = DateField('Incident Reported Date', validators=[DataRequired()])
    accused_name = StringField('Accused Name', validators=[DataRequired()])
    accused_age = StringField('Accused Age')
    accused_location = StringField('Accused Location', validators=[DataRequired()])
    charges = StringField('Charges', validators=[DataRequired()])
    spellchecked_charges = StringField('Spellchecked Charges')
    details = StringField('Details')
    legal_actions = StringField('Legal Actions')
    incident_date = DateField('Incident Date')
    incident_location = StringField('Incident Location')
    cortlandStandardSource = StringField('Cortland Standard Source')
    cortlandVoiceSource = StringField('Cortland Voice Source')

    submit = SubmitField('Add Incident')
