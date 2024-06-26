import os
from datetime import timedelta

import pandas as pd
from flask import Flask, render_template, jsonify, redirect, url_for, flash
from flask import send_from_directory
from sqlalchemy import func

from database import get_database_session
from flask_app.forms import VerificationForm, IncidentForm
from models.article import Article
from models.charges import Charges
from models.incident import Incident
from police_fire.cortland_voice.scrape_incidents_from_articles import rescrape_article as rescrape_cv_article

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
    # lookup the incident date
    charges = db_session.query(
        Charges
    ).filter(
        Charges.charged_name == person
    ).all()

    for charge in charges:
        # get the incident date by looking up the incident_id
        incident = db_session.query(Incident).filter(Incident.id == charge.incident_id).first()
        charge.incident_date = incident.incident_reported_date

    # sort charges by incident date
    charges.sort(key=lambda x: x.incident_date, reverse=True)

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
    # now that there are 2 sources, but we only want incidents created for one source or the other,
    # we need to do the same lookup we do before adding the incident to the database
    # when verifying it.
    form = VerificationForm(csrf_enabled=True)  # Enable CSRF protection

    cortlandVoice = False
    cortlandStandard = False
    cortland_voice_associated_incidents = []
    cortland_standard_associated_incidents = []

    if 'cortlandvoice' in article.url:
        cortlandVoice = True
        cortland_voice_associated_incidents = db_session.query(
            Incident).filter(
            Incident.cortlandVoiceSource == article.url).all()
    elif 'cortlandstandard' in article.url:
        cortlandStandard = True
        cortland_standard_associated_incidents = db_session.query(
            Incident).filter(
            Incident.cortlandStandardSource == article.url).all()
    else:
        raise ValueError('Article URL does not contain a recognized source.')

    print('cortlandVoiceAssociatedIncidents: ', cortland_voice_associated_incidents)
    print('cortlandStandardAssociatedIncidents: ', cortland_standard_associated_incidents)

    all_associated_incidents = []

    if cortlandStandard:
        for cortland_standard_incident in cortland_standard_associated_incidents:
            incidents = db_session.query(Incident).filter(
                Incident.accused_name == cortland_standard_incident.accused_name,
            ).order_by(Incident.incident_reported_date.asc()).all()
            new_incident_reported_date = cortland_standard_incident.incident_reported_date

            for existing_incident in incidents:
                existing_incident_reported_date = existing_incident.incident_reported_date
                print('new incident reported date: ', new_incident_reported_date)
                print('existing incident reported date: ', existing_incident_reported_date)
                # if the incident_reported_date is within a week of the new incident
                if new_incident_reported_date - timedelta(
                        days=5) <= existing_incident_reported_date <= new_incident_reported_date + timedelta(days=5):
                    print('Duplicate incident found in Cortland Standard.')
                    #
                    if existing_incident not in all_associated_incidents:
                        all_associated_incidents.append(existing_incident)
    elif cortlandVoice:
        for cortland_voice_incident in cortland_voice_associated_incidents:
            print(cortland_voice_incident)
            incidents = db_session.query(Incident).filter(
                Incident.accused_name == cortland_voice_incident.accused_name,
            ).order_by(Incident.incident_reported_date.asc()).all()
            new_incident_reported_date = cortland_voice_incident.incident_reported_date

            for existing_incident in incidents:
                existing_incident_reported_date = existing_incident.incident_reported_date
                print('new incident reported date: ', new_incident_reported_date)
                print('existing incident reported date: ', existing_incident_reported_date)
                # if the incident_reported_date is within a week of the new incident
                if new_incident_reported_date - timedelta(
                        days=5) <= existing_incident_reported_date <= new_incident_reported_date + timedelta(days=5):
                    print('Duplicate incident found in Cortland Voice.')
                    if existing_incident not in all_associated_incidents:
                        all_associated_incidents.append(existing_incident)

    potentially_duplicate_incidents = []
    # do a query with the first and last name like this: accused_name like '%Chris%Hines%
    # if there are any results, then the incident is likely a duplicate
    if len(all_associated_incidents) > 0:
        first_name, last_name = all_associated_incidents[0].accused_name.split()[0], all_associated_incidents[0].accused_name.split()[-1]
        if last_name in ['Jr.', 'Jr', 'Sr.', 'Sr', 'II', 'III', 'IV', 'V']:
            last_name = all_associated_incidents[0].accused_name.split()[-2]
        incidents = db_session.query(Incident).filter(
            Incident.accused_name.like(f"%{first_name}%{last_name}%")
        ).all()
        for incident in incidents:
            if incident not in all_associated_incidents:
                potentially_duplicate_incidents.append(incident)

    return render_template(
        'verify_article.html',
        article=article,
        incidents=all_associated_incidents,
        potentially_duplicate_incidents=potentially_duplicate_incidents,
        form=form
    )


@app.route('/verify-article/pdfs/<int:year>/<string:month>/<string:day>', methods=['GET'])
def get_pdf(year, month, day):
    base_pdf_path = os.path.normpath(os.getcwd() + os.sep + os.pardir) + '/pdfs' + f'/{year}/{month}/{day}/pages'

    try:
        files = [f for f in os.listdir(base_pdf_path) if f.endswith('.pdf')]
        if files:
            return send_from_directory(directory=base_pdf_path, path=files[0], as_attachment=False)
        else:
            return "No PDF found for this date.", 404
    except Exception as e:
        return str(e), 500


def get_article_id_from_incident(incident):
    article = db_session.query(Article).filter(Article.url == incident.cortlandStandardSource).first()
    if not article:
        article = db_session.query(Article).filter(Article.url == incident.cortlandVoiceSource).first()
    return article.id


@app.route('/delete-incident/<int:incident_id>', methods=['POST'])
def delete_incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    # check for any Charges associated to the incident
    charges = db_session.query(Charges).filter(Charges.incident_id == incident_id).all()
    if charges:
        for charge in charges:
            db_session.delete(charge)
            db_session.commit()
    if incident:
        db_session.delete(incident)
        db_session.commit()
        flash('Incident deleted successfully!', 'success')
    else:
        flash('Incident not found!', 'danger')

    article_id = get_article_id_from_incident(incident)
    return redirect(url_for('verify_article', article_id=article_id))  # Redirect back to verification page


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


@app.route('/add-incident', methods=['GET', 'POST'])
def add_incident():
    form = IncidentForm()
    if form.validate_on_submit():
        # Create a new Incident object
        incident = Incident(
            incident_reported_date=form.incident_reported_date.data,
            accused_name=form.accused_name.data,
            accused_age=form.accused_age.data,
            accused_location=form.accused_location.data,
            charges=form.charges.data,
            spellchecked_charges=form.spellchecked_charges.data,
            details=form.details.data,
            legal_actions=form.legal_actions.data,
            incident_date=form.incident_date.data,
            incident_location=form.incident_location.data,
            cortlandStandardSource=form.cortlandStandardSource.data,
            cortlandVoiceSource=form.cortlandVoiceSource.data
        )

        # Add the new Incident to the database
        db_session.add(incident)
        db_session.commit()
        flash('Incident added successfully!', 'success')
        return redirect(url_for('index'))  # Redirect or show a success message

    # Pass the form instance to the template
    return render_template('add_incident.html', form=form)


@app.route('/rescrape/cortland-voice/<int:article_id>', methods=['GET', 'POST'])
def rescrape_cortland_voice_article(article_id):
    # Logic to rescrape a Cortland Voice article
    article = db_session.query(Article).filter(Article.id == article_id).first()
    print('rescraping article: ', article.url)
    rescrape_cv_article(article.url)
    return redirect(url_for('verify_article', article_id=article_id))


if __name__ == '__main__':
    app.run(debug=True)
