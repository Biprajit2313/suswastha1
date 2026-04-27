import base64
import hashlib
import hmac
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionService:
    def __init__(self) -> None:
        settings = get_settings()
        raw_key = settings.fernet_key.strip()
        if raw_key:
            key = raw_key.encode("utf-8")
        else:
            digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(digest)
        self.fernet = Fernet(key)
        self.hash_secret = settings.secret_key.encode("utf-8")

    def encrypt_text(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_text(self, value: str) -> str:
        try:
            return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return value

    def encrypt_json(self, value: dict[str, Any]) -> str:
        return self.encrypt_text(json.dumps(value, separators=(",", ":"), default=str))

    def decrypt_json(self, value: str) -> dict[str, Any]:
        decrypted = self.decrypt_text(value)
        return json.loads(decrypted)

    def keyed_hash(self, value: str) -> str:
        return hmac.new(
            self.hash_secret,
            value.strip().lower().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
