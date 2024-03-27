import pandas as pd
from flask import Flask, render_template, jsonify

from database import get_database_session
from models.charges import Charges
from models.incident import Incident

db_session, engine = get_database_session(environment='production')

app = Flask(__name__)


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
    #print('incidents: ', incidents)
    return incidents


@app.route('/incidents')
def incidents():
    incidents = fetch_incidents()
    return render_template('incidents.html', incidents=incidents)


@app.route('/incidents/<int:incident_id>')
def incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    return render_template('incident.html', incident=incident)


def get_people():
    people = db_session.query(
        Charges.charged_name
    ).distinct().all()
    # order people alphabetically
    people.sort()
    people = [person[0] for person in people]

    return people  # Replace with the actual list of distinct names


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
            'incident_reported_date': incident.incident_date,
        })
    df = pd.DataFrame(incident_data)  # Convert crimes to pandas DataFrame
    df['year'] = pd.to_datetime(df['incident_reported_date']).dt.year  # Extract year from date
    crimes_by_year = df.groupby('year').size().to_dict()  # Group by year and count
    return crimes_by_year


@app.route('/api/incidents_by_year')
def incidents_by_year_api():
    incidents = fetch_incidents()
    incidents_by_year = get_incidents_by_year(incidents)
    return render_template('index.html', incidents_by_year=incidents_by_year)



if __name__ == '__main__':
    app.run(debug=True)
