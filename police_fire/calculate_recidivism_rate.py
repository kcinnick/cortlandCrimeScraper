import pandas as pd
import sqlalchemy
from sqlalchemy import column, text

from database import get_database_session, Incident


dbSession, engine = get_database_session(environment='prod')

# get persons incidents by querying the combined_incidents view
sql = text("SELECT accused_name, incident_date, source FROM public.incident")
result = dbSession.execute(sql)
persons_incidents = result.fetchall()

# Assuming persons_incidents is a list of tuples (person_id, name, incident_date)
df = pd.DataFrame(persons_incidents, columns=['accused_name', 'incident_date', 'source'])

# Convert incident_date to datetime if it's not already
df['incident_date'] = pd.to_datetime(df['incident_date'])

# Identifying repeat offenders
repeat_offenders = df[df.duplicated(subset=['accused_name'], keep=False)]
print(f'Number of repeat offenders: {len(repeat_offenders)}')
#pd.set_option('display.max_rows', None)
repeat_offenders.to_html('repeat_offenders.html')
# Calculate recidivism rate
recidivism_rate = len(repeat_offenders['accused_name'].unique()) / len(df['accused_name'].unique())

print(f'Recidivism rate: {recidivism_rate}')

# Example: Checking for individuals with offenses within a year of each other
repeat_offenders['next_incident'] = repeat_offenders.groupby('accused_name')['incident_date'].shift(-1)
repeat_offenders['days_to_next'] = (repeat_offenders['next_incident'] - repeat_offenders['incident_date']).dt.days

# Filter based on your criteria, e.g., incidents within 365 days
recidivism_within_year = repeat_offenders[repeat_offenders['days_to_next'] <= 365]
print(f'Recidivism within a year: {len(recidivism_within_year)}')
#pd.set_option('display.max_columns', None)
#pd.set_option('display.max_rows', None)

thresholds = [30, 60, 180, 365, 1000, 10000]
for threshold in thresholds:
    filtered_df = repeat_offenders[repeat_offenders['days_to_next'] <= threshold]
    print(f"Threshold: {threshold}, Count: {len(filtered_df)}")

print(repeat_offenders['days_to_next'].isnull())
