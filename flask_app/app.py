from flask import Flask, render_template, jsonify

from database import get_database_session
from models.charges import Charges

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
    crimes = [crime[0] for crime in distinct_crimes]  # Extracting crime types
    return jsonify(crimes)


if __name__ == '__main__':
    app.run(debug=True)
