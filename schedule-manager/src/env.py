from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    # Load .env from project root of this package
    here = Path(__file__).resolve().parent.parent
    env_path = here / ".env"
    print(f"Looking for .env file at: {env_path}")
    if env_path.exists():
        print(f"Found .env file, loading...")
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"Loaded environment variables from {env_path}")
    else:
        print(f".env file not found at {env_path}, using default search")
        load_dotenv()  # fallback: default search


