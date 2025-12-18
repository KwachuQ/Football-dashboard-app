from config.settings import get_db_settings

# Singleton instance
_settings = None

def get_settings():
    global _settings
    if _settings is None:
        _settings = get_db_settings()
    return _settings