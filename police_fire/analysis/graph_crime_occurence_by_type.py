from pprint import pprint

from database import get_database_session
from models.charges import Charges
DBsession, engine = get_database_session(environment='prod')

from sqlalchemy import func

crime_counts_with_ids = DBsession.query(
    Charges.crime,
    func.count(Charges.crime).label('total'),
    func.array_agg(Charges.incident_id).label('incident_ids')  # This aggregates the IDs into an array
).group_by(Charges.crime).order_by(func.count(Charges.crime).desc()).all()

for crime_count in crime_counts_with_ids:
    print(f'{crime_count.crime}, {crime_count.total}, {crime_count.incident_ids}')