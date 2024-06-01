import pandas as pd
import matplotlib.pyplot as plt

from database import get_database_session
from models.incident import Incident

# Read CSV files
df1 = pd.read_csv('../classification/manually_classified_records.csv')
df2 = pd.read_csv('../classification/automatically_classified_records.csv')

# Merge DataFrames
df = pd.concat([df1, df2], ignore_index=True)

# get dates
DBsession, engine = get_database_session(environment='prod')
date_query ='SELECT id, incident_date FROM incident'
dates_df = pd.read_sql(date_query, engine)

# merge with df
df = df.merge(dates_df, left_on='incident_id', right_on='id')

# Convert date column to datetime
df['incident_date'] = pd.to_datetime(df['incident_date'], format='%d-%m-%Y')

# Extract year from date
df['year'] = df['incident_date'].dt.year

# Group by year and case status classification
case_status_by_year = df.groupby(['year', 'case_status_classification']).size().unstack(fill_value=0)

# Plotting
case_status_by_year.plot(kind='bar', stacked=True, figsize=(10, 6))
plt.title('Case Status Classification by Year')
plt.xlabel('Year')
plt.ylabel('Count of Case Statuses')
plt.legend(title='Case Status')
plt.tight_layout()
plt.show()
