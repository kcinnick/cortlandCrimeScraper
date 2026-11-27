from flask import Flask, jsonify, request
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


def test_flask_wtf_request_compatibility():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-only', WTF_CSRF_ENABLED=False)

    class ExampleForm(FlaskForm):
        name = StringField(validators=[DataRequired()])

    @app.post('/example')
    def example():
        form = ExampleForm()
        if not form.validate_on_submit():
            return jsonify(errors=form.errors), 400
        return jsonify(name=request.form['name'])

    client = app.test_client()
    assert client.post('/example', data={'name': 'Example'}).json == {'name': 'Example'}
    assert client.post('/example', data={'name': ''}).status_code == 400
