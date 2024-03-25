# step 1: get all unique charge names
# step 2: find similar charge names
# step 3: normalize charge names
# step 4: update database with normalized charge names

from fuzzywuzzy import process
from tqdm import tqdm

from database import get_database_session
from models.charges import Charges

DBsession, engine = get_database_session(environment='prod')


# step 1: get all unique charge names
def get_unique_charge_names():
    unique_charge_names = DBsession.query(Charges.crime).distinct().all()
    unique_charge_names = [charge_name[0] for charge_name in unique_charge_names]
    return unique_charge_names


# step 2: find similar charge names
def find_similar_charge_names(charge_name, unique_charge_names):
    print(f'charge_name: {charge_name}')
    similar_charge_names = process.extract(charge_name, unique_charge_names, limit=5)
    return similar_charge_names


# step 3: normalize charge names
def normalize_charge_name(charge_name, similar_charge_names):
    print(f'charge_name: {charge_name}')
    return similar_charge_names[0][0]


# step 4: update database with normalized charge names
def update_database_with_normalized_charge_names(unique_charge_names):
    for charge_name in unique_charge_names:
        similar_charge_names = find_similar_charge_names(charge_name, unique_charge_names)
        normalized_charge_name = normalize_charge_name(charge_name, similar_charge_names)
        print(f'{charge_name} -> {normalized_charge_name}')
        # DBsession.query(Charges).filter(Charges.crime == charge_name).update({Charges.crime: normalized_charge_name})
        # DBsession.commit()


def main():
    unique_charge_names = get_unique_charge_names()
    for charge_name in tqdm(unique_charge_names):
        print('---')
        similar_charge_names = find_similar_charge_names(charge_name, unique_charge_names)
        for similar_charge_name in similar_charge_names:
            print(similar_charge_name)
        input('Press Enter to continue...')


if __name__ == '__main__':
    main()
