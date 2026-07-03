#!/usr/bin/env python3
"""
buffer_push.py — Pushes generated LinkedIn posts to Buffer via GraphQL API.

Usage:
  python3 _agent/buffer_push.py                      # auto-detects latest beitraege JSON
  python3 _agent/buffer_push.py path/to/beitraege.json
"""

import os
import sys
import json
import requests
from pathlib import Path

VAULT_PATH = Path.home() / "Documents" / "Prozessia-Brain"
AUTOPOSTER_ENV = VAULT_PATH / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / ".env"
LINKEDIN_PATH = VAULT_PATH / "Marketing" / "LinkedIn"

BUFFER_GRAPHQL = "https://api.buffer.com/graphql"

DEFAULT_CHANNELS = [
    "6a25d2578f1d11f9b260c5ee",  # Sebastian Spühler (Profil)
    "6a25d2578f1d11f9b260c5ef",  # Prozessia (Unternehmensseite)
]

POST_KEYS = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]

CREATE_POST_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id status dueAt }
    }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError { message }
    ... on LimitReachedError { message }
  }
}
"""


def load_token():
    token = os.environ.get("BUFFER_API_TOKEN")
    if token:
        return token
    if AUTOPOSTER_ENV.exists():
        for line in AUTOPOSTER_ENV.read_text().splitlines():
            line = line.strip()
            if line.startswith("BUFFER_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return None


def find_latest_beitraege():
    candidates = sorted(LINKEDIN_PATH.glob("*beitraege*.json"), reverse=True)
    if candidates:
        return candidates[0]
    fallback = VAULT_PATH / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / "output"
    candidates = sorted(fallback.glob("beitraege*.json"), reverse=True)
    return candidates[0] if candidates else None


def extract_posts(data: dict) -> list:
    posts = []
    kanaele = data.get("kanaele") or DEFAULT_CHANNELS

    for key in POST_KEYS:
        entry = data.get(key)
        if not entry:
            continue
        text = entry.get("text", "").strip()
        termin = entry.get("termin", "")

        if text.startswith("{") or text.startswith("```") or not text or not termin:
            if text:
                print(f"  WARNUNG: {key} hat ungültigen Text — übersprungen.")
            continue

        posts.append({
            "key": key,
            "text": text,
            "termin": termin,
            "kanaele": kanaele,
        })

    return posts


def create_post(token: str, channel_id: str, text: str, due_at: str) -> dict:
    resp = requests.post(
        BUFFER_GRAPHQL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "query": CREATE_POST_MUTATION,
            "variables": {
                "input": {
                    "channelId": channel_id,
                    "text": text,
                    "schedulingType": "automatic",
                    "mode": "customScheduled",
                    "dueAt": due_at,
                    "assets": [],
                    "saveToDraft": False,
                }
            },
        },
        timeout=15,
    )

    body = resp.json()
    result = (body.get("data") or {}).get("createPost") or {}
    errors = body.get("errors")

    if errors:
        return {"erfolg": False, "fehler": errors[0].get("message", "Unbekannter Fehler")}

    if "post" in result:
        post = result["post"]
        return {"erfolg": True, "postId": post["id"], "dueAt": post["dueAt"], "status": post["status"]}

    fehler = result.get("message", "Unbekannte Antwort")
    return {"erfolg": False, "fehler": fehler}


def run(json_path: Path = None):
    token = load_token()
    if not token:
        print("FEHLER: BUFFER_API_TOKEN nicht gefunden.")
        sys.exit(1)

    if json_path is None:
        json_path = find_latest_beitraege()
    if json_path is None or not json_path.exists():
        print("FEHLER: Keine beitraege-JSON gefunden.")
        sys.exit(1)

    print(f"Lade: {json_path.name}")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    posts = extract_posts(data)
    if not posts:
        print("Keine gültigen Posts gefunden.")
        return

    planungen = list(data.get("planungen") or [])
    bereits_gepusht = {p.get("key") for p in planungen if p.get("erfolg")}

    print(f"{len(posts)} Post(s) → pushe zu Buffer...\n")

    for post in posts:
        if post["key"] in bereits_gepusht:
            print(f"  {post['key']}: bereits gepusht — übersprungen.")
            continue

        print(f"  {post['key']} ({post['termin'][:10]}):")
        for channel_id in post["kanaele"]:
            result = create_post(token, channel_id, post["text"], post["termin"])
            result["key"] = post["key"]
            result["channel"] = channel_id
            planungen.append(result)

            if result["erfolg"]:
                label = "Sebastian" if channel_id == "6a25d2578f1d11f9b260c5ee" else "Prozessia"
                print(f"    ✓ {label} → {result['postId']} ({result.get('status', '')})")
            else:
                print(f"    ✗ {channel_id[:12]}… → {result['fehler']}")

    data["planungen"] = planungen
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for p in planungen if p.get("erfolg"))
    fail = sum(1 for p in planungen if not p.get("erfolg"))
    print(f"\nFertig: {ok} erfolgreich, {fail} Fehler → {json_path.name}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    run(path)
