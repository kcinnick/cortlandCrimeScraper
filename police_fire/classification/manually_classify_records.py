import csv

from tqdm import tqdm

from database import get_database_session
from models.incident import Incident

db_session, engine = get_database_session(environment='prod')
incidents = db_session.query(Incident).all()

already_classified_incidents = []


def set_new_id():
    with open('manually_classified_records.csv', 'r') as f:
        csv_dict = list(csv.DictReader(f))

        for row in csv_dict:
            already_classified_incidents.append(row['incident_id'])

    print('Already classified incidents:', already_classified_incidents)
    last_used_id = len(already_classified_incidents)
    new_id = last_used_id + 1

    return new_id


def automatically_classify_case_status(incident):
    if 'released without bail' in incident.legal_actions:
        return 'released_without_bail'
    elif 'ticketed to appear' in incident.legal_actions:
        return 'released_without_bail'
    elif 'awaiting arraignment' in incident.legal_actions:
        return 'pending_arraignment'
    elif 'sent to Cortland County Jail without bail' in incident.legal_actions:
        return 'held_without_bail'
    elif 'on $' in incident.legal_actions:
        return 'held_on_bail'
    else:
        return None


def manually_classify_case_status(incident):
    case_status_classification_query = 'What is the case status of this incident?'
    case_status_classification_query += f'\n{incident.legal_actions}'
    case_status_classification_query += (
        f'\n1. released_to_program 2. pending_arraignment 3. held_without_bail 4. '
        f'held_on_bail 5. released_without_bail 6. arrested 7. arraigned 8. released_with_bail '
        f'9. pled guilty 10. other 11. sentenced\n> '
    )
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
        case_status_classification = 'pled_guilty'
    elif int(case_status_classification) == 10:
        case_status_classification = 'other'
    elif int(case_status_classification) == 11:
        case_status_classification = 'sentenced'
    else:
        print('Invalid input. Skipping this incident.')
        case_status_classification = None

    return case_status_classification


def write_or_skip_classification(incident, classification, new_id):
    if classification is None:
        return
    with open('manually_classified_records.csv', 'a', newline='') as f:
        print('Writing to manually_classified_records.csv')
        writer = csv.writer(f)
        writer.writerow([new_id, incident.id, incident.legal_actions, classification])
        new_id += 1
        return new_id


def main():
    with open('manually_classified_records.csv', 'r') as f:
        csv_dict = list(csv.DictReader(f))

        for row in csv_dict:
            already_classified_incidents.append(row['incident_id'])

    new_id = set_new_id()
    for incident in tqdm(incidents):
        if str(incident.id) in already_classified_incidents:
            print('---')
            print('Incident ID:', incident.id, 'already classified.')
            continue
        else:
            print('---')
            print('Incident ID:', incident.id, 'not in already classified incidents.')

        print('---')
        classification = automatically_classify_case_status(incident)
        if classification:
            new_id = write_or_skip_classification(incident, classification, new_id)
            continue
        else:
            classification = manually_classify_case_status(incident)
            new_id = write_or_skip_classification(incident, classification, new_id)


if __name__ == '__main__':
    main()
