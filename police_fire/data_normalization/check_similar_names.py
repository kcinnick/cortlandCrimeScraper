# step 1: get all distinct names from Charges table
# step 2: split the names into first and last names - if last name is 'Jr/Sr' then use the second to last name as last name
# step 3: print all the split names
from pprint import pprint

from database import get_database_session
from models.charges import Charges


def get_distinct_names_from_charges_table(DBsession):
    names = DBsession.query(Charges).distinct(Charges.charged_name).all()
    return names


def split_names(names):
    split_names_array = []
    for name in names:
        split_name = name.charged_name.split(' ')
        if split_name[-1] == 'Jr.' or split_name[-1] == 'Sr.' or split_name[-1] == 'Jr' or split_name[-1] == 'Sr' or \
                split_name[-1] == 'II' or split_name[-1] == 'III' or split_name[-1] == 'IV' or split_name[-1] == 'V':
            last_name = split_name[-2]
        else:
            last_name = split_name[-1]
        first_name = split_name[0]
        split_names_array.append(f'{first_name} {last_name}')
    return split_names_array


def check_for_duplicate_names(split_names_array):
    duplicate_names = []
    for name in split_names_array:
        if split_names_array.count(name) > 1:
            duplicate_names.append(name)
    return duplicate_names


def main():
    DBsession, engine = get_database_session(environment='prod')
    names = get_distinct_names_from_charges_table(DBsession)
    split_names_array = split_names(names)
    duplicate_names = check_for_duplicate_names(split_names_array)
    # print the duplicate names
    pprint('Duplicate names: ' + str(set(duplicate_names)))

    return


if __name__ == '__main__':
    main()
