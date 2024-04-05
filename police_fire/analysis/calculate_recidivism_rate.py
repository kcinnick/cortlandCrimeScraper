import pandas as pd
from sqlalchemy import text
from database import get_database_session

dbSession, engine = get_database_session(environment='prod')

# Get persons incidents by querying the combined_incidents view
sql = text("SELECT accused_name, incident_date, source FROM public.incident ORDER BY incident_date ASC;")
result = dbSession.execute(sql)
persons_incidents = result.fetchall()

# Assuming persons_incidents is a list of tuples (accused_name, incident_date, source)
df = pd.DataFrame(persons_incidents, columns=['accused_name', 'incident_date', 'source'])

# Convert incident_date to datetime if it's not already
df['incident_date'] = pd.to_datetime(df['incident_date'])

# Identifying repeat offenders
repeat_offenders = df[df.duplicated(subset=['accused_name'], keep=False)].copy()

# Calculate the next incident date and days to next incident for repeat offenders
repeat_offenders['next_incident'] = repeat_offenders.groupby('accused_name')['incident_date'].shift(-1)
repeat_offenders['days_to_next'] = (repeat_offenders['next_incident'] - repeat_offenders['incident_date']).dt.days

total_unique_offenders = len(df['accused_name'].unique())

thresholds = [30, 60, 180, 365, 1000, 10000]
for threshold in thresholds:
    filtered_df = repeat_offenders[repeat_offenders['days_to_next'] <= threshold]

    # Ensure each offender is counted only once for each threshold
    unique_offenders_within_threshold = filtered_df['accused_name'].nunique()

    recidivism_rate_within_threshold = unique_offenders_within_threshold / total_unique_offenders
    print(f"Threshold: {threshold} days, Recidivism Rate: {recidivism_rate_within_threshold:.2f}, Unique Re-offenders Count: {unique_offenders_within_threshold}")
