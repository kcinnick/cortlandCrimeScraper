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


# pre-classified data
with open('manually_classified_records.csv', 'r') as f:
    csv_dict = list(csv.DictReader(f))

manually_classified_record_ids = [row['incident_id'] for row in csv_dict]
held_on_bail = [row for row in csv_dict if row['case_status_classification'] == 'held_on_bail']
print(len(held_on_bail), 'held_on_bail records')
released_without_bail = [row for row in csv_dict if row['case_status_classification'] == 'released_without_bail']
print(len(released_without_bail), 'released_without_bail records')
released_to_program = [row for row in csv_dict if row['case_status_classification'] == 'released_to_program']
print(len(released_to_program), 'released_to_program records')
pending_arraignment = [row for row in csv_dict if row['case_status_classification'] == 'pending_arraignment']
print(len(pending_arraignment), 'pending_arraignment records')
held_without_bail = [row for row in csv_dict if row['case_status_classification'] == 'held_without_bail']
print(len(held_without_bail), 'held_without_bail records')
arrested = [row for row in csv_dict if row['case_status_classification'] == 'arrested']
print(len(arrested), 'arrested records')
issued_appearance_ticket = [row for row in csv_dict if row['case_status_classification'] == 'issued_appearance_ticket']
print(len(issued_appearance_ticket), 'issued_appearance_ticket records')

released_without_bail_embeddings = [get_embeddings(row['incident_legal_actions']) for row in released_without_bail]
released_to_program_embeddings = [get_embeddings(row['incident_legal_actions']) for row in released_to_program]
pending_arraignment_embeddings = [get_embeddings(row['incident_legal_actions']) for row in pending_arraignment]
held_without_bail_embeddings = [get_embeddings(row['incident_legal_actions']) for row in held_without_bail]
held_on_bail_embeddings = [get_embeddings(row['incident_legal_actions']) for row in held_on_bail]
issued_appearance_ticket_embeddings = [get_embeddings(row['incident_legal_actions']) for row in
                                       issued_appearance_ticket]
arrested_embeddings = [get_embeddings(row['incident_legal_actions']) for row in arrested]

released_without_bail_centroid = calculate_centroid(released_without_bail_embeddings)
released_to_program_centroid = calculate_centroid(released_to_program_embeddings)
pending_arraignment_centroid = calculate_centroid(pending_arraignment_embeddings)
held_without_bail_centroid = calculate_centroid(held_without_bail_embeddings)
held_on_bail_centroid = calculate_centroid(held_on_bail_embeddings)
issued_appearance_ticket_centroid = calculate_centroid(issued_appearance_ticket_embeddings)
arrested_centroid = calculate_centroid(arrested_embeddings)

# new data
db_session, engine = get_database_session(environment='prod')
incidents = db_session.query(Incident).all()
incidents_without_classification = [incident for incident in incidents if str(incident.id) not in manually_classified_record_ids]
for incident in incidents_without_classification[:25]:
    if str(incident.id) in manually_classified_record_ids:
        print('---')
        print('Incident ID:', incident.id, 'already classified.')
        continue
    print('---')
    print(incident.legal_actions)
    incident_embedding = get_embeddings(incident.legal_actions)
    incident_centroid = calculate_centroid([incident_embedding])

    distances = {
        #'released_to_program': np.linalg.norm(incident_centroid - released_to_program_centroid),
        'pending_arraignment': np.linalg.norm(incident_centroid - pending_arraignment_centroid),
        'held_without_bail': np.linalg.norm(incident_centroid - held_without_bail_centroid),
        'held_on_bail': np.linalg.norm(incident_centroid - held_on_bail_centroid),
        'released_without_bail': np.linalg.norm(incident_centroid - released_without_bail_centroid),
        'issued_appearance_ticket': np.linalg.norm(incident_centroid - issued_appearance_ticket_centroid),
        'arrested': np.linalg.norm(incident_centroid - arrested_centroid),
    }

    print(distances)
    classification = min(distances, key=distances.get)
    print(f'Incident {incident.id} classified as {classification}')
