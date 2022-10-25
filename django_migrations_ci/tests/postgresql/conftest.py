from django.conf import settings
import psycopg2
import pytest


@pytest.fixture
def connection():
    db_conf = settings.DATABASES["postgresql"]
    conn = psycopg2.connect(
        "postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}".format(**db_conf)
    )
    try:
        yield conn
    finally:
        conn.close()
