from datetime import date, datetime

import pytest

from police_fire.utilities.incident_dates import infer_incident_date


@pytest.mark.parametrize('details,legal,published,expected', [
    ('Charged with petit larceny.', 'Charged Tuesday.', '2026-11-27', '2026-11-24'),
    ('Was charged Wednesday with DWI.', '', '2026-11-27', '2026-11-25'),
    ('Was charged Thursday.', '', '2026-11-25', '2026-11-19'),
    ('Was charged Tuesday.', '', '2026-11-24', '2026-11-24'),
    ('Was charged last Tuesday.', '', '2026-11-24', '2026-11-17'),
    ('Was CHARGED on tuesday.', '', '2026-11-27', '2026-11-24'),
    ('Arrested Nov. 12 on a warrant.', '', '2026-11-25', '2026-11-12'),
    ('Charged November 12, 2025.', '', '2026-11-25', '2025-11-12'),
    ('Charged Dec. 31.', '', '2026-01-02', '2025-12-31'),
    ('Charged Wednesday.', '', '2026-01-02', '2025-12-31'),
    ('Charged 2026-11-12.', '', '2026-11-25', '2026-11-12'),
    ('Charged yesterday.', '', '2026-11-25', '2026-11-24'),
    ('Charged today.', '', '2026-11-25', '2026-11-25'),
    ('The crash occurred Tuesday. Charged Wednesday.', 'Court Friday.', '2026-11-27', '2026-11-24'),
    ('Charged Tuesday. Due in court Thursday.', '', '2026-11-27', '2026-11-24'),
    ('No date supplied.', 'Will appear in court Tuesday.', '2026-11-27', None),
    ('Charged with DWI.', 'Hearing November 12.', '2026-11-25', None),
    ('Charged Tuesday. Arrested Wednesday.', '', '2026-11-27', None),
    ('Charged next Tuesday.', '', '2026-11-27', None),
    ('Charged November 28, 2026.', '', '2026-11-27', None),
    ('Charged February 30.', '', '2026-11-27', None),
    ('Charged with an offense.', '', '2026-11-27', None),
    ('Charged Tuesdays.', '', '2026-11-27', None),
    (None, None, '2026-11-27', None),
])
def test_inference(details, legal, published, expected):
    result = infer_incident_date(details, legal, published)
    assert result == (date.fromisoformat(expected) if expected else None)


def test_publication_datetime():
    assert infer_incident_date('Charged Tuesday.', '', datetime(2026, 11, 27, 10, 30)) == date(2026, 11, 24)
