from flask import Flask, render_template, jsonify

from database import get_database_session
from models.charges import Charges
from models.incident import Incident

db_session, engine = get_database_session(environment='production')

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


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
    incidents = db_session.query(Incident).distinct()
    return incidents


@app.route('/incidents')
def incidents():
    incidents = fetch_incidents()
    return render_template('incidents.html', incidents=incidents)


@app.route('/incidents/<int:incident_id>')
def incident(incident_id):
    incident = db_session.query(Incident).filter(Incident.id == incident_id).first()
    return render_template('incident.html', incident=incident)

if __name__ == '__main__':
    app.run(debug=True)
