import os

from requests import Session
from sqlalchemy.ext.declarative import declarative_base


def login():
    session = Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'})
    session.get('https://www.cortlandstandard.com/login.html')

    login_username = os.getenv('LOGIN_EMAIL')
    login_password = os.getenv('LOGIN_PASSWORD')

    r = session.post('https://www.cortlandstandard.com/login.html?action=login', data={
        'login_username': login_username,
        'login_password': login_password,
        'referer': '',
        'ssoreturn': '',
        'referer_content': '',
        'login_standard': '',
    })
    assert r.status_code == 200

    return session
