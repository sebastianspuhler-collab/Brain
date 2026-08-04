#!/usr/bin/env python3
"""
buffer_sync.py — Schreibt aktuellen Buffer-Status nach _agent/buffer_status.md
Wird beim Brain-Start oder auf Abruf ausgeführt, damit Claude immer aktuellen
Buffer-Kontext hat — auch ohne direkten API-Zugriff in der Session.
"""

import os, json, requests
from datetime import datetime
from pathlib import Path

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
ENV_PATH = VAULT / "_inbox" / "Branding" / "claude-linkedin-auto-poster" / ".env"
STATUS_FILE = VAULT / "_agent" / "buffer_status.md"

API = "https://api.buffer.com/graphql"
ORG_ID = "6a15c3685a233c9c16251245"
CHANNELS = {
    "6a25d2578f1d11f9b260c5ee": "Sebastian Spühler",
    "6a25d2578f1d11f9b260c5ef": "Prozessia GbR",
}

POSTS_QUERY = """
query Posts($orgId: OrganizationId!, $status: [PostStatus!]) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }) {
    edges { node { id text status dueAt sentAt channel { id name } } }
  }
}
"""

INSIGHTS_QUERY = """
query PostsWithMetrics($orgId: OrganizationId!, $status: [PostStatus!], $first: Int) {
  posts(input: { organizationId: $orgId, filter: { status: $status } }, first: $first) {
    edges { node { id sentAt channel { id name } metrics { type value } } }
  }
}
"""

IDEAS_QUERY = """
query Ideas($orgId: OrganizationId!) {
  ideas(input: { organizationId: $orgId }) {
    edges { node { id content { title text date } createdAt } }
  }
}
"""


def load_token():
    t = os.environ.get("BUFFER_API_TOKEN")
    if t:
        return t
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("BUFFER_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    return None


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
        from datetime import timezone
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%Y %H:%M")
    except Exception:
        return dt_str[:16]


def run():
    token = load_token()
    if not token:
        print("BUFFER_API_TOKEN nicht gefunden — buffer_status.md nicht aktualisiert.")
        return

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [f"# Buffer Status\n_Zuletzt aktualisiert: {now}_\n"]

    try:
        # Scheduled posts
        data = gql(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["scheduled", "draft"]})
        posts = [e["node"] for e in data.get("posts", {}).get("edges", [])]
        posts_sorted = sorted(posts, key=lambda x: x.get("dueAt") or "")

        lines.append("## Geplante Posts")
        if posts_sorted:
            for p in posts_sorted:
                kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
                text = p["text"].replace("\n", " ")[:100]
                lines.append(f"- **{fmt_date(p.get('dueAt'))}** | {kanal} | `{p['id']}` | {text}…")
        else:
            lines.append("_Keine Posts geplant._")

        # Sent posts (last 5)
        data2 = gql(token, POSTS_QUERY, {"orgId": ORG_ID, "status": ["sent"]})
        sent = [e["node"] for e in data2.get("posts", {}).get("edges", [])]
        sent = sorted(sent, key=lambda x: x.get("sentAt") or "", reverse=True)[:5]

        lines.append("\n## Zuletzt gesendet (letzte 5)")
        if sent:
            for p in sent:
                kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
                text = p["text"].replace("\n", " ")[:80]
                lines.append(f"- **{fmt_date(p.get('sentAt'))}** | {kanal} | {text}…")
        else:
            lines.append("_Noch keine Posts gesendet._")

        # Ideas
        data3 = gql(token, IDEAS_QUERY, {"orgId": ORG_ID})
        ideas = [e["node"] for e in data3.get("ideas", {}).get("edges", [])]

        lines.append("\n## Content-Ideen in Buffer")
        if ideas:
            for idea in ideas:
                c = idea.get("content", {})
                title = c.get("title") or (c.get("text", "")[:60].replace("\n", " "))
                lines.append(f"- `{idea['id'][:16]}…` | {title}")
        else:
            lines.append("_Keine Ideen vorhanden._")

        # Insights (letzte 5 gesendete Posts mit Metriken)
        data4 = gql(token, INSIGHTS_QUERY, {"orgId": ORG_ID, "status": ["sent"], "first": 20})
        metric_posts = [e["node"] for e in data4.get("posts", {}).get("edges", [])]
        metric_posts = sorted(metric_posts, key=lambda x: x.get("sentAt") or "", reverse=True)[:5]

        lines.append("\n## Insights (letzte 5 gesendete Posts)")
        if metric_posts:
            for p in metric_posts:
                kanal = CHANNELS.get(p["channel"]["id"], p["channel"]["name"])
                m = {x["type"]: x["value"] for x in (p.get("metrics") or [])}
                impr = m.get("impressions")
                reach = m.get("reach")
                eng = m.get("engagementRate")
                parts = []
                if impr is not None:
                    parts.append(f"{impr:g} Impr.")
                if reach is not None:
                    parts.append(f"{reach:g} Reach")
                if eng is not None:
                    parts.append(f"{eng:.1f}% Eng.")
                stats = ", ".join(parts) if parts else "keine Metriken"
                lines.append(f"- **{fmt_date(p.get('sentAt'))}** | {kanal} | {stats}")
        else:
            lines.append("_Keine Insights verfügbar._")

        lines.append(f"\n---\n_Buffer Manager: `python3 _agent/buffer_manager.py [status|sent|drafts|ideas|push|delete|edit|insights]`_")

    except Exception as e:
        lines.append(f"\n**FEHLER beim Buffer-Abruf:** {e}")

    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"buffer_status.md aktualisiert ({now})")


if __name__ == "__main__":
    run()
