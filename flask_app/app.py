import pandas as pd
from flask import Flask, render_template, jsonify, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField
from sqlalchemy import func

from database import get_database_session
from models.article import Article
from models.charges import Charges
from models.incident import Incident

db_session, engine = get_database_session(environment='production')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'


@app.route('/')
def index():
    incidents = fetch_incidents()  # Fetch incidents data
    incidents_by_year = get_incidents_by_year(incidents)  # Process data
    return render_template('index.html', incidents_by_year=incidents_by_year)  # Pass data to template


@app.route('/data')
def data():
    distinct_crimes = db_session.query(
        Charges.crime
    ).distinct().all()
    # order crimes alphabetically
    distinct_crimes.sort()
    crimes = [crime[0] for crime in distinct_crimes]  # Extracting crime types
    return jsonify(crimes)


def fetch_crimes_by_type(crime_type):
    crimes_by_type = db_session.query(
        Charges
    ).filter(
        Charges.crime == crime_type
    ).all()
    return crimes_by_type


@app.route('/crimes/<crime_type>')
def show_filtered_crimes(crime_type):
    filtered_crimes = fetch_crimes_by_type(crime_type)

    return render_template('filtered_crimes.html', crimes=filtered_crimes)


def fetch_incidents():
    incidents = db_session.query(Incident).distinct().all()

    # print('incidents: ', incidents)
    return incidents


@app.route('/incidents')
def incidents():
    incidents = fetch_incidents()
    # order Incidents by reported_date
    incidents.sort(key=lambda x: x.incident_reported_date, reverse=True)
    return render_template('incidents.html', incidents=incidents)


@app.route('/incidents/<int:incident_id>')
def incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    return render_template('incident.html', incident=incident)


def get_people():
    people_counts = db_session.query(
        Charges.charged_name,
        func.count(Charges.id).label('total_charges'),
        func.count(Charges.incident_id.distinct()).label('total_incidents')
    ).group_by(
        Charges.charged_name
    ).order_by(
        func.count(Charges.id).desc()
    ).all()

    # Transform query results into a list of dictionaries for easier handling in the template
    people = [{
        'name': person.charged_name,
        'total_charges': person.total_charges,
        'total_incidents': person.total_incidents
    } for person in people_counts]

    return people


def get_charges_by_person(person):
    charges = db_session.query(
        Charges
    ).filter(
        Charges.charged_name == person
    ).all()

    return charges


@app.route('/charges/<string:person_name>')
def charges(person_name):
    charges = get_charges_by_person(person_name)  # Call the function to fetch charges
    return render_template('charges_for_person.html', person_name=person_name, charges=charges)


@app.route('/people')
def people():
    people = get_people()  # Call the function to fetch distinct names
    return render_template('people.html', people=people)


def get_incidents_by_year(incidents):
    incident_data = []
    for incident in incidents:
        incident_data.append({
            'incident_reported_date': incident.incident_reported_date,
            'id': incident.id
        })

    # Convert crimes to pandas DataFrame
    df = pd.DataFrame(incident_data)

    # Ensure 'incident_reported_date' is a datetime type
    df['incident_reported_date'] = pd.to_datetime(df['incident_reported_date'])

    # Extract year and month for sorting
    df['year'] = df['incident_reported_date'].dt.year

    # Group by year and count incidents
    crimes_by_year = df.groupby('year').size().to_dict()

    return crimes_by_year


@app.route('/api/incidents_by_year')
def incidents_by_year_api():
    incidents = fetch_incidents()
    incidents_by_year = get_incidents_by_year(incidents)
    return render_template('index.html', incidents_by_year=incidents_by_year)


@app.route('/verify_incidents')
def verify_incidents():
    # Fetch unverified articles by incidents_verified == False and incidents_scraped == True
    unverified_articles = db_session.query(Article).filter(
        Article.incidents_verified == False,
        Article.incidents_scraped == True
    ).all()
    return render_template('verify_articles.html', articles=unverified_articles)


@app.route('/verify-article/<int:article_id>', methods=['GET', 'POST'])
def verify_article(article_id):
    article = db_session.query(Article).filter(Article.id == article_id).first()
    associated_incidents = db_session.query(Incident).filter(
        Incident.source == article.url).all()  # Fetch associated incidents
    form = VerificationForm(csrf_enabled=True)  # Enable CSRF protection

    return render_template(
        'verify_article.html',
        article=article,
        incidents=associated_incidents,
        form=form
    )


def get_article_id_from_incident(incident):
    article = db_session.query(Article).filter(Article.url == incident.source).first()
    return article.id


@app.route('/delete-incident/<int:incident_id>', methods=['POST'])
def delete_incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    if incident:
        db_session.delete(incident)
        db_session.commit()
        flash('Incident deleted successfully!', 'success')
    else:
        flash('Incident not found!', 'danger')

    article_id = get_article_id_from_incident(incident)
    return redirect(url_for('verify_article', article_id=article_id))  # Redirect back to verification page


class VerificationForm(FlaskForm):
    verified = BooleanField('Verified?')
    submit = SubmitField('Mark as Verified')
    csrf_enabled = True  # Enable CSRF protection in the form


@app.route('/update-verification/<int:article_id>', methods=['POST'])
def update_verification(article_id):
    article = db_session.query(Article).filter(Article.id == article_id).first()
    form = VerificationForm(csrf_enabled=True)  # Create a VerificationForm instance

    if form.validate_on_submit():
        print(form.data)
        is_verified = form.verified.data  # Access the checkbox value using .data
        print(f"Checkbox is checked: {is_verified}")
        article.incidents_verified = is_verified
        db_session.commit()  # Commit changes to the database

        # Redirect to verify_incidents route after successful update
        return redirect(url_for('verify_incidents'))
    else:
        print('form errors: ', form.errors)  # Print errors if validation fails

    return render_template('verify_article.html', article=article, form=form)


if __name__ == '__main__':
    app.run(debug=True)
