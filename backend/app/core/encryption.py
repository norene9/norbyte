import json
import os

from cryptography.fernet import Fernet

DEFAULT_ENCRYPTION_KEY = "3z7V6Kj9R2pL5wX8qA1bC4dE7fG0hI3jK5mN2oP5qR8="
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY)

try:
    fernet = Fernet(ENCRYPTION_KEY.encode("utf-8"))
except Exception as exc:
    raise RuntimeError(
        "ENCRYPTION_KEY must be a valid Fernet key in the format required by cryptography. "
        "Set it in the environment or a .env file."
    ) from exc


def encrypt_config(config: dict) -> str:
    raw = json.dumps(config, separators=(",", ":")).encode("utf-8")
    return fernet.encrypt(raw).decode("utf-8")


def decrypt_config(token: str) -> dict:
    raw = fernet.decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))
