#!/usr/bin/env python3
"""Legt einen Benutzer in users.json an oder aktualisiert sein Passwort.
Ausführen: python scripts/hash_password.py
"""
import getpass
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.security import hash_password  # noqa: E402

if __name__ == "__main__":
    username = input("Benutzername: ").strip()
    password = getpass.getpass("Passwort: ")
    if not username or not password:
        print("Benutzername und Passwort dürfen nicht leer sein.")
        raise SystemExit(1)

    users_file = get_settings().users_file
    users = json.loads(users_file.read_text(encoding="utf-8")) if users_file.exists() else {}
    users[username] = hash_password(password)
    users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")

    print(f"\n{username} gespeichert in {users_file.resolve()}")
