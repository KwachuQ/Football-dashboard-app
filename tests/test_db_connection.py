from services.db import test_connection

def test_db_connection():
    assert test_connection(), "Database connectivity failed (SELECT 1 did not return 1)"