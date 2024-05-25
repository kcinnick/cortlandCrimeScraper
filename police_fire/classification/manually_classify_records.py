import csv

from database import get_database_session
from models.incident import Incident

db_session, engine = get_database_session(environment='prod')
incidents = db_session.query(Incident).all()

already_classified_incidents = []

with open('manually_classified_records.csv', 'r') as f:
    csv_dict = list(csv.DictReader(f))

    for row in csv_dict:
        already_classified_incidents.append(row['incident_id'])

print('Already classified incidents:', already_classified_incidents)
last_used_id = len(already_classified_incidents)
new_id = last_used_id + 1

for incident in incidents[100:200]:
    if str(incident.id) in already_classified_incidents:
        print('---')
        print('Incident ID:', incident.id, 'already classified.')
        continue
    else:
        print('---')
        print('Incident ID:', incident.id, 'not in already classified incidents.')

    print('---')
    print(incident.legal_actions)
    case_status_classification_query = 'What is the case status of this incident?'
    case_status_classification_query += f'\n{incident.legal_actions}'
    case_status_classification_query += (f'\n1. released_to_program 2. pending_arraignment 3. held_without_bail 4. '
                                         f'held_on_bail 5. released_without_bail 6. arrested 7. arraigned 8. released_with_bail '
                                         f'9. issued_appearance_ticket \n> ')
    case_status_classification = input(case_status_classification_query)
    if int(case_status_classification) == 1:
        case_status_classification = 'released_to_program'
    elif int(case_status_classification) == 2:
        case_status_classification = 'pending_arraignment'
    elif int(case_status_classification) == 3:
        case_status_classification = 'held_without_bail'
    elif int(case_status_classification) == 4:
        case_status_classification = 'held_on_bail'
    elif int(case_status_classification) == 5:
        case_status_classification = 'released_without_bail'
    elif int(case_status_classification) == 6:
        case_status_classification = 'arrested'
    elif int(case_status_classification) == 7:
        case_status_classification = 'arraigned'
    elif int(case_status_classification) == 8:
        case_status_classification = 'released_with_bail'
    elif int(case_status_classification) == 9:
        case_status_classification = 'issued_appearance_ticket'
    else:
        print('Invalid input. Skipping this incident.')
        continue
    with open('manually_classified_records.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([new_id, incident.id, incident.legal_actions, case_status_classification])
        new_id += 1