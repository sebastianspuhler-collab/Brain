"""Auth: gehashte Passwörter + signierte Session-Cookies statt Klartext-Token-Set.

Ersetzt die alte _AUTH_TOKENS-Logik aus brain_server.py, die zwei Klartext-Passwörter
im Quellcode hielt und Tokens auch per URL-Query-Parameter akzeptierte (Leak-Risiko
über Logs/Browser-Historie/Referrer). Hier: bcrypt-Hash + itsdangerous-signiertes,
httpOnly-Cookie mit Ablaufzeit.
"""
from datetime import timedelta

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

SESSION_COOKIE = "brain_session"
SESSION_MAX_AGE = int(timedelta(days=30).total_seconds())

# Nutzer + Passwort-Hashes kommen aus ENV (siehe .env.example), nicht aus dem Code.
# Erzeugen mit: python scripts/hash_password.py
# (passlib wurde bewusst nicht verwendet - es ist unmaintained und inkompatibel
# mit aktuellen bcrypt-Versionen; direkter bcrypt-Aufruf ist robuster.)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except Exception:
        return False


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret, salt="brain-session")


def create_session_token(username: str) -> str:
    return _serializer().dumps({"user": username})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user")
    except (BadSignature, SignatureExpired, Exception):
        return None
