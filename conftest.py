"""Default tests never contact external services; live tests require opt-in."""
import socket

import pytest


LIVE_MODULES = {
    'test_scrape_articles_by_section.py',
    'test_add_incident_with_multiple_people.py',
    'test_scrape_structured_police_fire_details.py',
    'test_scrape_unstructured_police_fire_details.py',
}


def pytest_addoption(parser):
    parser.addoption('--integration', action='store_true', default=False,
                     help='Enable live website/API tests (may incur API charges).')


def pytest_configure(config):
    config.addinivalue_line('markers', 'integration: requires external services')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.path.name in LIVE_MODULES or item.name == 'test_get_incident_location':
            item.add_marker(pytest.mark.integration)
        if item.get_closest_marker('integration') and not config.getoption('--integration'):
            item.add_marker(pytest.mark.skip(reason='Live test: opt in with --integration'))


@pytest.fixture(autouse=True)
def block_offline_network(request, monkeypatch):
    if request.node.get_closest_marker('integration'):
        return

    def blocked(*args, **kwargs):
        raise AssertionError('Offline test attempted a network connection')

    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)
