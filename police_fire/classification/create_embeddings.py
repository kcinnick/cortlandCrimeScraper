import csv

from transformers import AutoTokenizer, AutoModel
import torch

import numpy as np

from database import get_database_session
from models.incident import Incident

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")


def get_embeddings(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze(1).detach().numpy()
    return embeddings


def calculate_centroid(embeddings):
    return np.mean(embeddings, axis=0)


def get_centroid_for_classification(classification):
    # pre-classified data
    with open('manually_classified_records.csv', 'r') as f:
        csv_dict = list(csv.DictReader(f))

    records = [row for row in csv_dict if row['case_status_classification'] == classification]
    print(len(records), f'{classification} records')
    embeddings = [get_embeddings(row['incident_legal_actions']) for row in records]
    return calculate_centroid(embeddings)


def classify_incident(incident, manually_classified_record_ids, centroids, last_used_id):
    if str(incident.id) in manually_classified_record_ids:
        print('---')
        print('Incident ID:', incident.id, 'already classified.')
        return
    print('---')
    print(incident.legal_actions)
    incident_embedding = get_embeddings(incident.legal_actions)
    incident_centroid = calculate_centroid([incident_embedding])

    distances = {
        'released_to_program': np.linalg.norm(incident_centroid - centroids['released_to_program_centroid']),
        'pending_arraignment': np.linalg.norm(incident_centroid - centroids['pending_arraignment_centroid']),
        'held_without_bail': np.linalg.norm(incident_centroid - centroids['held_without_bail_centroid']),
        'held_on_bail': np.linalg.norm(incident_centroid - centroids['held_on_bail_centroid']),
        'released_without_bail': np.linalg.norm(incident_centroid - centroids['released_without_bail_centroid']),
        'arrested': np.linalg.norm(incident_centroid - centroids['arrested_centroid']),
        'other': np.linalg.norm(incident_centroid - centroids['other_centroid']),
        'sentenced': np.linalg.norm(incident_centroid - centroids['sentenced_centroid']),
    }

    classification = min(distances, key=distances.get)
    print(f'Incident {incident.id} classified as {classification}')
    with open('automatically_classified_records.csv', 'a', encoding='utf-8') as f:
        f.write(f'{last_used_id},{incident.id},"{incident.legal_actions}",{classification}\n')

    return


def get_centroids():
    centroids = {}
    centroids['held_on_bail_centroid'] = get_centroid_for_classification('held_on_bail')
    centroids['released_without_bail_centroid'] = get_centroid_for_classification('released_without_bail')
    centroids['released_to_program_centroid'] = get_centroid_for_classification('released_to_program')
    centroids['pending_arraignment_centroid'] = get_centroid_for_classification('pending_arraignment')
    centroids['held_without_bail_centroid'] = get_centroid_for_classification('held_without_bail')
    centroids['arrested_centroid'] = get_centroid_for_classification('arrested')
    centroids['other_centroid'] = get_centroid_for_classification('other')
    centroids['sentenced_centroid'] = get_centroid_for_classification('sentenced')

    return centroids


def main():
    # pre-classified data
    with open('manually_classified_records.csv', 'r') as f:
        csv_dict = list(csv.DictReader(f))

    manually_classified_record_ids = [row['incident_id'] for row in csv_dict]

    centroids = get_centroids()

    db_session, engine = get_database_session(environment='prod')
    incidents = db_session.query(Incident).all()
    incidents_without_classification = [incident for incident in incidents if
                                        str(incident.id) not in manually_classified_record_ids]

    with open('automatically_classified_records.csv', 'w') as f:
        f.write('id,incident_id,incident_legal_actions,case_status_classification\n')

    last_used_id = 0
    for incident in incidents_without_classification:
        last_used_id += 1
        classify_incident(incident, manually_classified_record_ids, centroids, last_used_id)


if __name__ == '__main__':
    main()
