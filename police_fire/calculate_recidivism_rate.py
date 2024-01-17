import pandas as pd
from sqlalchemy import text

from database import get_database_session

dbSession, engine = get_database_session(environment='prod')

# get persons incidents by querying the combined_incidents view
sql = text("SELECT accused_name, incident_date, source FROM public.incident ORDER BY incident_date ASC;")
result = dbSession.execute(sql)
persons_incidents = result.fetchall()

# Assuming persons_incidents is a list of tuples (person_id, name, incident_date)
df = pd.DataFrame(persons_incidents, columns=['accused_name', 'incident_date', 'source'])

# Convert incident_date to datetime if it's not already
df['incident_date'] = pd.to_datetime(df['incident_date'])

# Identifying repeat offenders
repeat_offenders = df[df.duplicated(subset=['accused_name'], keep=False)]

recidivism_rate = len(repeat_offenders['accused_name'].unique()) / len(df['accused_name'].unique())

print(f'Recidivism rate: {recidivism_rate}')

repeat_offenders['next_incident'] = repeat_offenders.groupby('accused_name')['incident_date'].shift(-1)
repeat_offenders['days_to_next'] = (repeat_offenders['next_incident'] - repeat_offenders['incident_date']).dt.days

thresholds = [30, 60, 180, 365, 1000, 10000]
for threshold in thresholds:
    filtered_df = repeat_offenders[repeat_offenders['days_to_next'] <= threshold]

    # Ensure each offender is counted only once
    unique_offenders = filtered_df.drop_duplicates(subset=['accused_name'])

    print(f"Threshold: {threshold}, Unique Offenders Count: {len(unique_offenders)}")

    with open(f"repeat_offenders_{threshold}.html", 'w') as f:
        f.write(unique_offenders.to_html())

