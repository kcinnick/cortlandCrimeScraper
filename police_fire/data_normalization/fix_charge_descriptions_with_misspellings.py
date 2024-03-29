# step 1: get all Incidents
# step 2: for each incident, check the `charges` attribute for misspellings
# step 3: if a misspelling is found, prompt the user for a correction
# step 4: update the incident in the database with the corrected charges
from spellchecker import SpellChecker
from tqdm import tqdm

from database import get_database_session
from models.incident import Incident

DBsession, engine = get_database_session(environment='prod')


def spellcheck_charges():
    correct_words = ['first-degree', 'second-degree', 'third-degree', 'fourth-degree',]
    corrected_words = {}

    # incidents = DBsession.query(Incident).all()
    # get incidents where spellchecked_charges is null
    incidents = DBsession.query(Incident).filter(Incident.spellchecked_charges == None).all()
    spell = SpellChecker()
    for incident in tqdm(incidents):
        print('---')
        charges = incident.charges
        print(charges)
        misspelled_charges = spell.unknown(charges.split())
        real_misspelled_charges = [word for word in misspelled_charges if word[-1] not in ['.', ',', ';']]
        real_misspelled_charges = [word for word in real_misspelled_charges if word not in correct_words]

        print(f"Misspelled charges: {real_misspelled_charges}")

        for misspelled_charge in real_misspelled_charges:
            if misspelled_charge in correct_words:
                continue
            elif misspelled_charge in corrected_words.keys():
                charges = charges.replace(misspelled_charge, corrected_words[misspelled_charge])
                continue
            corrected_charge = input(f"Correct {misspelled_charge} (leave blank to keep): ")

            if not corrected_charge:
                print(f'Keeping original: {misspelled_charge}')
                correct_words.append(misspelled_charge)
            else:
                punctuation = misspelled_charge[-1] if misspelled_charge[-1] in ['.', ',', ';'] else ''
                corrected_charge_with_punctuation = corrected_charge + punctuation
                corrected_words[misspelled_charge] = corrected_charge_with_punctuation
                charges = charges.replace(misspelled_charge, corrected_charge_with_punctuation)

        incident.spellchecked_charges = charges
        DBsession.commit()

    return
