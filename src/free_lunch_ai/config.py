import os
from dotenv import load_dotenv

# --- GLOBAL STATE ---
AVAILABLE_PROVIDERS = {
    "groq": False,
    "google": False
}


def load_api_keys(env_path: str = None):
    """
    Loads .env, updates os.environ

    """
    # 1. Load Environment
    if env_path:
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)

    # 2. test connection
    # ...
