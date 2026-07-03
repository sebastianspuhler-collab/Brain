#!/usr/bin/env python3
"""
buffer_manager.py — Volle Buffer-Kontrolle für das Prozessia Brain.

Befehle:
  python3 _agent/buffer_manager.py status          # geplante Posts anzeigen
  python3 _agent/buffer_manager.py sent [n]        # letzte n gesendete Posts (default: 10)
  python3 _agent/buffer_manager.py drafts          # Entwürfe anzeigen
  python3 _agent/buffer_manager.py ideas           # Content-Ideen anzeigen
  python3 _agent/buffer_manager.py push [datei]    # Posts aus JSON → Buffer
  python3 _agent/buffer_manager.py delete <id>     # Post löschen
  python3 _agent/buffer_manager.py edit <id> [text] [datum]  # Post bearbeiten
"""

import os, sys, json, requests
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
ENV_PATH = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / ".env"
LINKEDIN_PATH = VAULT / "Marketing" / "LinkedIn"

API = "https://api.buffer.com/graphql"
ORG_ID = "6a15c3685a233c9c16251245"
CHANNELS = {
    "6a25d2578f1d11f9b260c5ee": "Sebastian",
    "6a25d2578f1d11f9b260c5ef": "Prozessia",
}
POST_KEYS = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]


def load_token():
    t = os.environ.get("BUFFER_API_TOKEN")
    if t:
        return t
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("BUFFER_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    print("FEHLER: BUFFER_API_TOKEN nicht gefunden.")
    sys.exit(1)


def gql(token, query, variables=None):
    resp = requests.post(
        API,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=15,
    )
    body = resp.json()
    if body.get("errors"):
        raise RuntimeError(body["errors"][0]["message"])
    return body.get("data", {})


def fmt_date(dt_str):
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%Y %H:%M")
    except Exception:
        return dt_str[:16]


def fmt_text(text, width=80):
    if not text:
        return "—"
    text = text.replace("\n", " ")
    return text[:width] + "…" if len(text) > width else text


# ── Queries ──────────────────────────────────────────────────────────────────

POSTS_QUERY = """
query Posts($orgId: OrganizationId!, $status: [PostStatus!]) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }) {
    edges {
      node {
        id text status dueAt sentAt
        channel { id name }
      }
    }
  }
}
"""

IDEAS_QUERY = """
query Ideas($orgId: OrganizationId!) {
  ideas(input: { organizationId: $orgId }) {
    edges {
      node {
        id
        content { title text date }
        createdAt
      }
    }
  }
}
"""

CREATE_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id status dueAt } }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError { message }
    ... on LimitReachedError { message }
  }
}
"""

EDIT_MUTATION = """
mutation EditPost($input: EditPostInput!) {
  editPost(input: $input) {
    ... on PostActionSuccess { post { id status dueAt text } }
    ... on InvalidInputError { message }
    ... on UnauthorizedError { message }
    ... on UnexpectedError { message }
  }
}
"""

DELETE_MUTATION = """
mutation DeletePost($id: PostId!) {
  deletePost(input: { id: $id }) {
    ... on DeletePostSuccess { id }
  }
}
"""


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_status(token):
    data = gql(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["scheduled", "draft"]})
    posts = [e["node"] for e in data.get("posts", {}).get("edges", [])]
    if not posts:
        print("Keine geplanten Posts in Buffer.")
        return
    print(f"\n{'─'*90}")
    print(f"{'GEPLANTE POSTS IN BUFFER':^90}")
    print(f"{'─'*90}")
    print(f"{'Datum':<18} {'Kanal':<12} {'Status':<10} {'ID':<26} {'Text'}")
    print(f"{'─'*90}")
    for p in sorted(posts, key=lambda x: x.get("dueAt") or ""):
        kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
        print(f"{fmt_date(p.get('dueAt')):<18} {kanal:<12} {p['status']:<10} {p['id']:<26} {fmt_text(p['text'], 40)}")
    print(f"{'─'*90}")
    print(f"Gesamt: {len(posts)} Posts\n")


def cmd_sent(token, n=10):
    data = gql(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["sent"]})
    posts = [e["node"] for e in data.get("posts", {}).get("edges", [])]
    posts = sorted(posts, key=lambda x: x.get("sentAt") or "", reverse=True)[:n]
    if not posts:
        print("Keine gesendeten Posts gefunden.")
        return
    print(f"\n{'─'*90}")
    print(f"{'GESENDETE POSTS (letzte {n})':^90}")
    print(f"{'─'*90}")
    print(f"{'Gesendet':<18} {'Kanal':<12} {'ID':<26} {'Text'}")
    print(f"{'─'*90}")
    for p in posts:
        kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
        print(f"{fmt_date(p.get('sentAt')):<18} {kanal:<12} {p['id']:<26} {fmt_text(p['text'], 44)}")
    print(f"{'─'*90}\n")


def cmd_drafts(token):
    data = gql(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["draft"]})
    posts = [e["node"] for e in data.get("posts", {}).get("edges", [])]
    if not posts:
        print("Keine Entwürfe in Buffer.")
        return
    print(f"\n{len(posts)} Entwurf/Entwürfe:\n")
    for p in posts:
        kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
        print(f"  [{p['id']}] {kanal}: {fmt_text(p['text'], 70)}")
    print()


def cmd_ideas(token):
    data = gql(token, IDEAS_QUERY, {"orgId": ORG_ID})
    ideas = [e["node"] for e in data.get("ideas", {}).get("edges", [])]
    if not ideas:
        print("Keine Ideen in Buffer.")
        return
    print(f"\n{'─'*80}")
    print(f"{'CONTENT IDEEN IN BUFFER':^80}")
    print(f"{'─'*80}")
    for idea in ideas:
        c = idea.get("content", {})
        title = c.get("title") or fmt_text(c.get("text", ""), 50)
        date = c.get("date")
        created = datetime.fromtimestamp(idea["createdAt"]).strftime("%d.%m.") if idea.get("createdAt") else ""
        print(f"  [{idea['id'][:12]}…] {title:<50} {fmt_date(date) if date else f'erstellt {created}'}")
    print(f"{'─'*80}")
    print(f"Gesamt: {len(ideas)} Ideen\n")


def cmd_push(token, json_path=None):
    if json_path is None:
        candidates = sorted(LINKEDIN_PATH.glob("*beitraege*.json"), reverse=True)
        if not candidates:
            print("Keine beitraege-JSON gefunden.")
            sys.exit(1)
        json_path = candidates[0]

    json_path = Path(json_path)
    if not json_path.exists():
        print(f"Datei nicht gefunden: {json_path}")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    kanaele = data.get("kanaele") or list(CHANNELS.keys())
    planungen = list(data.get("planungen") or [])
    gepusht = {p.get("key") for p in planungen if p.get("erfolg")}

    posts = []
    for key in POST_KEYS:
        entry = data.get(key)
        if not entry:
            continue
        text = (entry.get("text") or "").strip()
        termin = entry.get("termin", "")
        if not text or text.startswith("{") or text.startswith("```") or not termin:
            continue
        posts.append({"key": key, "text": text, "termin": termin})

    if not posts:
        print("Keine gültigen Posts in der Datei.")
        return

    print(f"Lade: {json_path.name} → {len(posts)} Post(s)\n")
    for post in posts:
        if post["key"] in gepusht:
            print(f"  {post['key']}: bereits gepusht — übersprungen.")
            continue
        print(f"  {post['key']} ({post['termin'][:10]}):")
        for channel_id in kanaele:
            result = gql(token, CREATE_MUTATION, {"input": {
                "channelId": channel_id,
                "text": post["text"],
                "schedulingType": "automatic",
                "mode": "customScheduled",
                "dueAt": post["termin"],
                "assets": [],
                "saveToDraft": False,
            }})
            r = result.get("createPost", {})
            if "post" in r:
                p = r["post"]
                planungen.append({"key": post["key"], "channel": channel_id, "erfolg": True,
                                   "postId": p["id"], "dueAt": p["dueAt"], "status": p["status"]})
                print(f"    ✓ {CHANNELS.get(channel_id, channel_id)} → {p['id']}")
            else:
                err = r.get("message", "Fehler")
                planungen.append({"key": post["key"], "channel": channel_id, "erfolg": False, "fehler": err})
                print(f"    ✗ {CHANNELS.get(channel_id, channel_id)} → {err}")

    data["planungen"] = planungen
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for p in planungen if p.get("erfolg"))
    print(f"\nFertig: {ok} Posts in Buffer.\n")


def cmd_delete(token, post_id):
    result = gql(token, DELETE_MUTATION, {"id": post_id})
    r = result.get("deletePost", {})
    if r.get("id"):
        print(f"Gelöscht: {post_id}")
    else:
        print(f"Fehler: {r.get('message', 'Unbekannt')}")


def cmd_edit(token, post_id, text=None, due_at=None):
    inp = {
        "id": post_id,
        "schedulingType": "automatic",
        "mode": "customScheduled",
    }
    if text:
        inp["text"] = text
    if due_at:
        inp["dueAt"] = due_at
    result = gql(token, EDIT_MUTATION, {"input": inp})
    r = result.get("editPost", {})
    if "post" in r:
        p = r["post"]
        print(f"Aktualisiert: {p['id']} | {fmt_date(p['dueAt'])} | {fmt_text(p['text'], 60)}")
    else:
        print(f"Fehler: {r.get('message', 'Unbekannt')}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = load_token()
    args = sys.argv[1:]

    if not args or args[0] == "status":
        cmd_status(token)
    elif args[0] == "sent":
        n = int(args[1]) if len(args) > 1 else 10
        cmd_sent(token, n)
    elif args[0] == "drafts":
        cmd_drafts(token)
    elif args[0] == "ideas":
        cmd_ideas(token)
    elif args[0] == "push":
        cmd_push(token, args[1] if len(args) > 1 else None)
    elif args[0] == "delete" and len(args) > 1:
        cmd_delete(token, args[1])
    elif args[0] == "edit" and len(args) > 1:
        text = args[2] if len(args) > 2 else None
        due_at = args[3] if len(args) > 3 else None
        cmd_edit(token, args[1], text, due_at)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
