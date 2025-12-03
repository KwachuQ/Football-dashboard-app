from services.db import check_connection

def test_db_connection():
    assert check_connection(), "Database connectivity failed (SELECT 1 did not return 1)"