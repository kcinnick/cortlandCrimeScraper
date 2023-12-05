import os

from database import get_database_session
import pandas as pd
from datetime import datetime


def make_folder_for_today(table_name):
    # get today's year, month, and day
    today = datetime.today()
    year = today.year
    month = today.month
    if month < 10:
        month = f'0{month}'
    day = today.day
    if day < 10:
        day = f'0{day}'

    # create a folder for today's date
    folder_name = f"{table_name}/{year}/{month}/{day}"
    os.makedirs(folder_name, exist_ok=True)

    return folder_name


def export_table(table_name, folder_name, engine):
    results = pd.read_sql_query(f'select * from {table_name}', engine)
    results.to_csv(
        f"{folder_name}/{table_name}.csv",
        index=False, header=True)


def main():
    DBsession, engine = get_database_session(environment='prod')
    for table_name in ['persons', 'incidents', 'incidents_from_pdf']:
        folder_name = make_folder_for_today(table_name)
        export_table(table_name, folder_name, engine)


if __name__ == '__main__':
    main()
