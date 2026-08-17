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
  python3 _agent/buffer_manager.py insights [n]    # Analytics (Impressions, Reach, Eng.-Rate %) der letzten n gesendeten Posts
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


def _normalize_posts(data: dict) -> list:
    """Liest Posts aus einer beitraege-*.json, egal ob altes Format
    (Wochentag als Key) oder neues Format (Liste mit stabiler id pro Post,
    seit mindestens beitraege-2026-07-25.json aktiv). 1:1 dieselbe Logik wie
    backend/app/services/linkedin_service.py:_normalize_posts() - ohne diese
    kannte `push` nur noch die Wochentag-Keys und fand in aktuellen Dateien
    nie Posts ("Keine gültigen Posts in der Datei."), ohne dass das auffiel."""
    if isinstance(data.get("posts"), list):
        return data["posts"]
    posts = []
    datum = data.get("generiert_am", "")[:10]
    for key in POST_KEYS:
        p = data.get(key)
        if not p:
            continue
        posts.append({
            "id": f"{datum}-{key}",
            "tag": key.capitalize(),
            "datum": datum,
            "termin": p.get("termin", ""),
            "idee": p.get("idee", ""),
            "typ": p.get("typ", ""),
            "text": p.get("text", ""),
        })
    return posts


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
query Posts($orgId: OrganizationId!, $status: [PostStatus!], $after: String) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id text status dueAt sentAt
        channel { id name }
      }
    }
  }
}
"""

INSIGHTS_QUERY = """
query PostsWithMetrics($orgId: OrganizationId!, $status: [PostStatus!], $after: String) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id text sentAt
        channel { id name }
        metricsUpdatedAt
        metrics { name type unit value }
      }
    }
  }
}
"""


def gql_all_posts(token, query, variables):
    """Paginiert eine posts()-Query vollständig durch. Buffer liefert pro Aufruf
    nur eine Seite (beobachtet: 10 Treffer) und markiert das nur über
    pageInfo.hasNextPage/endCursor - ohne dieses Nachfassen wurden reale Posts
    jenseits der ersten Seite komplett verschluckt (2026-08-17: Sebastians
    EU-AI-Act-Draft lag in Buffer, aber status/drafts zeigten ihn nicht, weil
    er auf Seite 3 von 3 lag)."""
    edges = []
    cursor = None
    while True:
        vars_page = dict(variables, after=cursor)
        data = gql(token, query, vars_page)
        page = data.get("posts", {})
        edges.extend(page.get("edges", []))
        page_info = page.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return edges


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
    ... on NotFoundError { message }
    ... on UnexpectedError { message }
    ... on RestProxyError { message }
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
    ... on NotFoundError { message }
    ... on UnexpectedError { message }
    ... on RestProxyError { message }
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
    edges = gql_all_posts(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["scheduled", "draft"]})
    posts = [e["node"] for e in edges]
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
    edges = gql_all_posts(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["sent"]})
    posts = [e["node"] for e in edges]
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


def cmd_insights(token, n=10):
    edges = gql_all_posts(token, INSIGHTS_QUERY, {"orgId": ORG_ID, "status": ["sent"]})
    posts = [e["node"] for e in edges]
    posts = sorted(posts, key=lambda x: x.get("sentAt") or "", reverse=True)[:n]
    if not posts:
        print("Keine gesendeten Posts gefunden.")
        return

    print(f"\n{'─'*110}")
    print(f"{'BUFFER INSIGHTS (letzte ' + str(n) + ' gesendete Posts)':^110}")
    print(f"{'─'*110}")
    print(f"{'Gesendet':<18} {'Kanal':<14} {'Impr.':>7} {'Reach':>7} {'Eng.%':>7} {'React.':>7} {'Komm.':>6} {'Shares':>7} {'Text'}")
    print(f"{'─'*110}")
    for p in posts:
        kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
        m = {x["type"]: x["value"] for x in (p.get("metrics") or [])}

        def fmt_num(v, pct=False):
            if v is None:
                return "—"
            return f"{v:.1f}%" if pct else f"{v:g}"

        print(
            f"{fmt_date(p.get('sentAt')):<18} {kanal:<14} "
            f"{fmt_num(m.get('impressions')):>7} {fmt_num(m.get('reach')):>7} "
            f"{fmt_num(m.get('engagementRate'), pct=True):>7} {fmt_num(m.get('reactions')):>7} "
            f"{fmt_num(m.get('comments')):>6} {fmt_num(m.get('shares')):>7} "
            f"{fmt_text(p['text'], 30)}"
        )
    print(f"{'─'*110}")

    with_impressions = [p for p in posts if any(x["type"] == "impressions" for x in (p.get("metrics") or []))]
    if with_impressions:
        avg_eng = sum(
            next((x["value"] for x in p["metrics"] if x["type"] == "engagementRate"), 0) for p in with_impressions
        ) / len(with_impressions)
        print(f"Ø Engagement-Rate (Posts mit Impressions-Daten): {avg_eng:.2f}%")
    print()


def cmd_drafts(token):
    edges = gql_all_posts(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["draft"]})
    posts = [e["node"] for e in edges]
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
    posts = _normalize_posts(data)

    to_push = []
    for post in posts:
        text = (post.get("text") or "").strip()
        if not text or text.startswith("{") or text.startswith("```"):
            continue
        to_push.append(post)

    if not to_push:
        print("Keine gültigen Posts in der Datei.")
        return

    print(f"Lade: {json_path.name} → {len(to_push)} Post(s)\n")
    for post in to_push:
        label = post.get("id") or post.get("idee") or "?"
        if post.get("pushed"):
            print(f"  {label}: bereits gepusht — übersprungen.")
            continue
        termin = post.get("termin", "")
        print(f"  {label} ({termin[:10] if termin else 'kein Termin, Buffer-Queue'}):")
        buffer_ids = list(post.get("buffer_post_ids") or [])
        any_ok = False
        for channel_id in kanaele:
            result = gql(token, CREATE_MUTATION, {"input": {
                "channelId": channel_id,
                "text": post["text"],
                "schedulingType": "automatic",
                "mode": "customScheduled" if termin else "addToQueue",
                **({"dueAt": termin} if termin else {}),
                "assets": [],
                "saveToDraft": False,
            }})
            r = result.get("createPost", {})
            if "post" in r:
                p = r["post"]
                buffer_ids.append(p["id"])
                any_ok = True
                print(f"    ✓ {CHANNELS.get(channel_id, channel_id)} → {p['id']}")
            else:
                err = r.get("message", "Fehler")
                print(f"    ✗ {CHANNELS.get(channel_id, channel_id)} → {err}")
        if any_ok:
            post["pushed"] = True
            post["buffer_post_ids"] = buffer_ids

    # Immer im neuen id-basierten Format zurückschreiben (dieselbe Migration
    # wie linkedin_service._save_post_fields()), damit Web-App und CLI
    # denselben Push-Status (post["pushed"]/post["buffer_post_ids"]) sehen.
    data["posts"] = posts
    for key in POST_KEYS:
        data.pop(key, None)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for p in posts if p.get("pushed"))
    print(f"\nFertig: {ok} von {len(posts)} Posts in Buffer.\n")


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
    elif args[0] == "insights":
        n = int(args[1]) if len(args) > 1 else 10
        cmd_insights(token, n)
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
