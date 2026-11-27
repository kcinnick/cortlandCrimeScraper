import os
import hmac
import secrets
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template, jsonify, redirect, url_for, flash, g, request, abort
from flask import send_from_directory
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func
from werkzeug.local import LocalProxy

from database import get_database_session
from flask_app.forms import VerificationForm, IncidentForm
from models.article import Article
from models.charges import Charges
from models.incident import Incident
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32),
    DATABASE_ENV=os.getenv('DATABASE_ENV', os.getenv('FLASK_ENV', 'development')),
    READ_ONLY=os.getenv('APP_READ_ONLY', '1') != '0',
    ADMIN_TOKEN=os.getenv('FLASK_ADMIN_TOKEN'),
)


def get_request_session():
    if 'db_session' not in g:
        factory = app.config.get('DATABASE_SESSION_FACTORY')
        if factory:
            g.db_session, g.db_engine = factory()
        else:
            g.db_session, g.db_engine = get_database_session(
                environment=app.config['DATABASE_ENV'], create_tables=False,
            )
    return g.db_session


db_session = LocalProxy(get_request_session)


@app.before_request
def protect_writes():
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        if app.config['READ_ONLY']:
            abort(403, description='Read-only preview: database modifications are disabled.')
        expected = app.config.get('ADMIN_TOKEN')
        supplied = request.headers.get('X-Admin-Token', '')
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(403, description='An administrative token is required.')


csrf = CSRFProtect(app)


@app.teardown_appcontext
def close_request_session(error=None):
    session = g.pop('db_session', None)
    engine = g.pop('db_engine', None)
    if session is not None:
        session.rollback()
        session.close()
    if engine is not None:
        engine.dispose()


@app.route('/')
def index():
    incidents = fetch_incidents()  # Fetch incidents data
    incidents_by_year = get_incidents_by_year(incidents)  # Process data
    return render_template('index.html', incidents_by_year=incidents_by_year)  # Pass data to template


@app.route('/data')
def data():
    distinct_crimes = db_session.query(
        Charges.crime
    ).filter(Charges.crime.is_not(None)).distinct().all()
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
    incidents.sort(key=lambda x: x.incident_reported_date or date.min, reverse=True)
    return render_template('incidents.html', incidents=incidents)


@app.route('/incidents/<int:incident_id>')
def incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        abort(404)
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
    return dict(sorted(Counter(
        incident.incident_reported_date.year for incident in incidents
        if incident.incident_reported_date is not None
    ).items()))


@app.route('/api/incidents_by_year')
def incidents_by_year_api():
    incidents = fetch_incidents()
    incidents_by_year = get_incidents_by_year(incidents)
    return jsonify(incidents_by_year)


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
    if article is None:
        abort(404)
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
    if not month.isdigit() or not day.isdigit():
        abort(404)
    try:
        date(year, int(month), int(day))
    except ValueError:
        abort(404)
    base_pdf_path = Path(__file__).resolve().parents[1] / 'pdfs' / str(year) / month / day / 'pages'
    files = sorted(base_pdf_path.glob('*.pdf'))
    if not files:
        abort(404)
    return send_from_directory(directory=base_pdf_path, path=files[0].name, as_attachment=False)


def get_article_id_from_incident(incident):
    article = db_session.query(Article).filter(Article.url == incident.cortlandStandardSource).first()
    if not article:
        article = db_session.query(Article).filter(Article.url == incident.cortlandVoiceSource).first()
    return article.id if article else None


@app.route('/delete-incident/<int:incident_id>', methods=['POST'])
def delete_incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        abort(404)
    article_id = get_article_id_from_incident(incident)
    try:
        db_session.query(Charges).filter(Charges.incident_id == incident_id).delete()
        db_session.delete(incident)
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    flash('Incident deleted successfully!', 'success')
    return redirect(url_for('verify_article', article_id=article_id) if article_id else url_for('incidents'))


@app.route('/update-verification/<int:article_id>', methods=['POST'])
def update_verification(article_id):
    article = db_session.query(Article).filter(Article.id == article_id).first()
    if article is None:
        abort(404)
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


@app.route('/rescrape/cortland-voice/<int:article_id>', methods=['POST'])
def rescrape_cortland_voice_article(article_id):
    article = db_session.query(Article).filter(Article.id == article_id).first()
    if article is None:
        abort(404)
    if not article.url.startswith('https://cortlandvoice.com/') or article.incidents_scraped:
        abort(409, description='Reprocessing existing incidents requires manual review.')
    from police_fire.refresh_data import parse_article
    parse_article(db_session, article)
    return redirect(url_for('verify_article', article_id=article_id))


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=False, use_reloader=False)
