import os

from dotenv import load_dotenv

load_dotenv()


def config_get(key: str) -> str:
    """Read a required value from environment variables.

    Args:
        key: Environment variable name.

    Returns:
        The variable's string value.

    Raises:
        RuntimeError: If the variable is not set.
    """
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value
