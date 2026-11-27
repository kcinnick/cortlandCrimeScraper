from datetime import date, datetime

import pytest

from police_fire.cortland_standard.scrape_structured_police_fire_details import check_if_details_references_a_relative_date
from police_fire.utilities.utilities import get_last_date_of_day_of_week_before_date


def test_check_if_details_references_a_relative_date():
    response = check_if_details_references_a_relative_date(
        'Two people called 911 about 5:35 p.m. Monday complaining', '2022-10-28'
    )
    assert response == '2022-10-24'


@pytest.mark.parametrize('day,reported,expected', [
    ('Monday', '2022-10-24', '2022-10-17'),
    ('Sunday', date(2026, 1, 1), '2025-12-28'),
    ('Wednesday', datetime(2024, 3, 1), '2024-02-28'),
])
def test_weekday_boundaries(day, reported, expected):
    assert get_last_date_of_day_of_week_before_date(day, reported) == expected


def test_no_weekday():
    assert check_if_details_references_a_relative_date('No date stated.', '2026-11-26') is None


def test_invalid_weekday():
    with pytest.raises(ValueError):
        get_last_date_of_day_of_week_before_date('Notaday', '2026-11-26')
