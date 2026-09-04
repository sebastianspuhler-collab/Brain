"""Empfänger für eingehende Close-CRM-Webhooks (Lead updated, Call logged,
Opportunity won/lost, ...). ÖFFENTLICH erreichbar (siehe docker-compose.yml -
dieser Container hängt für /lead-agent/webhook/close zusätzlich direkt im
traefik_web-Netz, mit eigenem Traefik-Router NUR für diesen Pfad) - Close hat
keine Cookie-Session, kann also nicht über den bestehenden
Depends(get_current_user)-Auth-Layer laufen (siehe
docs/system-overview-lead-agent.md Punkt 3: "kein Muster im Repo").
Stattdessen HMAC-Signaturprüfung über Close's Webhook-Signing-Secret - fail
CLOSED ohne gesetztes Secret (kein offener, unauthentifizierter Endpunkt ins
Internet).

Close signiert mit zwei Headern: `close-sig-timestamp` (Unix-Sekunden) und
`close-sig-hash` (hex HMAC-SHA256(signing_key, timestamp + raw_body)) - siehe
Close-Doku "Webhook Signing". Zusätzlich ein Zeitfenster-Check gegen
Replay-Angriffe (5 Minuten, wie bei den meisten Webhook-Signaturschemata
üblich).

STAND 2026-09-04: strukturell gegen die dokumentierte Close-Signaturprüfung
gebaut, aber noch NICHT gegen ein echtes eingehendes Close-Event
live-verifiziert (kein Close-Account mit konfiguriertem Webhook zum
Testzeitpunkt vorhanden) - das exakte Event-Payload-Schema (welche Felder bei
welchem event.type wirklich befüllt sind) daher nur nach bestem Wissen
abgebildet, mit defensiven .get()-Zugriffen statt harten Annahmen. Vor
Produktivbetrieb: einen echten Testwebhook aus Close auslösen und die
Feldnamen in _apply_event() gegen die tatsächliche Payload abgleichen."""
import hashlib
import hmac
import time
from pathlib import Path

import vault_leads
from config import get_settings

REPLAY_WINDOW_SECONDS = 5 * 60

# Grobe, konservative Zuordnung Close-Event-Typ -> neuer Lead-Status. Nur
# Events, bei denen der neue Status eindeutig aus dem Typ folgt - alles
# andere (z.B. reines "lead.updated" ohne erkennbares Feld) wird geloggt,
# aber NICHT automatisch umgestellt (lieber keine Änderung als eine falsche).
_STATUS_BY_EVENT_TYPE = {
    "activity.call.created": "kontaktiert",
    "activity.email.created": "kontaktiert",
    "activity.note.created": "kontaktiert",
}


class WebhookAuthError(Exception):
    pass


def verify_signature(raw_body: bytes, timestamp: str, signature: str) -> None:
    settings = get_settings()
    if not settings.close_webhook_signing_key:
        raise WebhookAuthError("CLOSE_WEBHOOK_SIGNING_KEY ist nicht gesetzt - Webhook fail-closed abgelehnt.")
    if not timestamp or not signature:
        raise WebhookAuthError("close-sig-timestamp/close-sig-hash Header fehlen.")

    try:
        ts = int(timestamp)
    except ValueError as e:
        raise WebhookAuthError("close-sig-timestamp ist keine Zahl.") from e
    if abs(time.time() - ts) > REPLAY_WINDOW_SECONDS:
        raise WebhookAuthError("close-sig-timestamp außerhalb des Zeitfensters (Replay-Schutz).")

    signed_payload = timestamp.encode() + raw_body
    expected = hmac.new(settings.close_webhook_signing_key.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise WebhookAuthError("Signatur ungültig.")


def _extract_lead_id(event: dict) -> str | None:
    data = event.get("data") or {}
    return (
        event.get("lead_id")
        or data.get("lead_id")
        or (data.get("id") if event.get("object_type") == "lead" else None)
    )


def _apply_event(event: dict) -> dict:
    event_type = event.get("type") or event.get("action") or "unbekannt"
    lead_id = _extract_lead_id(event)
    if not lead_id:
        return {"handled": False, "reason": "keine lead_id im Event gefunden", "event_type": event_type}

    lead = vault_leads.find_lead_by_close_id(lead_id)
    if not lead:
        return {"handled": False, "reason": f"kein Vault-Lead mit close_lead_id={lead_id}", "event_type": event_type}

    new_status = _STATUS_BY_EVENT_TYPE.get(event_type)
    if event_type == "opportunity.status_updated":
        status_type = ((event.get("data") or {}).get("status_type") or "").lower()
        if status_type == "won":
            new_status = "gewonnen"
        elif status_type == "lost":
            new_status = "verloren"

    if not new_status:
        return {"handled": False, "reason": f"Event-Typ '{event_type}' hat keine hinterlegte Status-Zuordnung", "event_type": event_type}

    vault_leads.update_fields(Path(lead["path"]), {"status": new_status})
    return {"handled": True, "event_type": event_type, "vault_path": lead["filename"], "new_status": new_status}


def handle_payload(payload: dict) -> dict:
    """Close schickt entweder ein einzelnes Event oder (je nach
    Subscription-Konfiguration) eine Liste unter 'events' - beide Formen
    abfangen statt anzunehmen."""
    events = payload.get("events") if isinstance(payload.get("events"), list) else [payload]
    results = [_apply_event(e) for e in events if isinstance(e, dict)]
    return {"ok": True, "results": results}
