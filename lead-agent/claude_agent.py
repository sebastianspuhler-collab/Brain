"""Chat-/Tool-Use-Loop des Lead-Agenten über `claude -p` (Claude-Code-CLI,
Abo-Billing via CLAUDE_CODE_OAUTH_TOKEN) - KEIN Anthropic-Messages-API-Aufruf,
kein eigener anthropic_api_key nötig (Entscheidung 2026-09-04: derselbe
Abrechnungsweg wie dev-agent/ und der Hauptbackend-Pfad claude_engine=cli,
siehe backend/app/services/claude_cli.py, dessen Muster hier eigenständig
kopiert wird - kein Shared-Import über den Container-Rand).

Custom-Tools (Close CRM, Vault-Lead-Schreibzugriff, Gmail-Entwurf) laufen über
den lokalen MCP-Server (mcp_server.py, registriert in .mcp.json) - Vault-LESEN
(Leads/*.md, PLAYBOOK.md, Kunden-Kontext) läuft nativ über Claude Codes
Read/Glob/Grep. Bewusst OHNE natives Write/Edit: jede Datei-Änderung im Vault
soll über ein geprüftes MCP-Tool laufen (save_prospect/update_lead_status/
generate_sales_brief), nicht über freies Editieren durch das Modell - siehe
mcp_server.py-Docstring.
"""
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

from config import get_settings

CLAUDE_BIN = "claude"
APP_DIR = Path(__file__).resolve().parent
MCP_CONFIG_PATH = APP_DIR / ".mcp.json"
MCP_SERVER_NAME = "lead-agent-tools"
DEFAULT_MODEL = "claude-sonnet-5"
ALLOWED_MODELS = {"claude-sonnet-5", "claude-opus-5"}

# Empirisch am Hauptbackend verifiziert (siehe claude_cli.py-Docstring): das
# projekt-lokale MCP verbindet asynchron im Hintergrund, braucht dafür ein
# paar Sekunden. --input-format stream-json + die Nachricht erst nach diesem
# Sleep schicken, sonst hält das Modell die MCP-Tools für nicht verfügbar.
MCP_WARMUP_SECONDS = 8.0


class ClaudeAgentError(RuntimeError):
    pass


SYSTEM_PROMPT = """Du bist der Prozessia-Lead-Agent - ein internes Steuer-Tool
für Sebastian und das Prozessia-Vertriebsteam, KEIN öffentlicher Chatbot für
Website-Besucher.

Lies bei JEDER Anfrage, die ICP/Recherche/Scoring/Priorisierung betrifft,
ZUERST PLAYBOOK.md (liegt in deinem Arbeitsverzeichnis, per Read erreichbar)
- dort stehen ICP-Kriterien, Recherche-Quellen und Scoring-Regeln. Ohne
gelesenes PLAYBOOK.md keine Bewertung/Priorisierung vornehmen, sondern kurz
nachfragen bzw. auf fehlende Kriterien hinweisen.

Deine Aufgaben:
1. RECHERCHE: neue Prospects passend zum ICP finden. Qualität schlägt
   Quantität - lieber 3 gut geprüfte als 10 geratene Treffer:
   a) IMMER PLAYBOOK.md zuerst (siehe oben) - keine Prospects ohne
      ICP-Kriterien vorschlagen/anlegen.
   b) Pro Kandidat MEHRERE Quellen gegenchecken (natives WebSearch, mehrere
      gezielte Anfragen statt einer einzigen groben) - Firmenwebsite
      (Branche/Größe/Leistung), aktuelle Nachrichten/Trigger (Wachstum,
      Ausschreibung, Stellenanzeigen als Digitalisierungssignal),
      wenn möglich LinkedIn/Impressum für den richtigen Ansprechpartner.
      EIN einzelner Treffer aus einer einzelnen Suche reicht nicht.
   c) Vor dem Anlegen kurz UND explizit gegen die PLAYBOOK.md-ICP-Kriterien
      abgleichen (Branche/Größe/Region/Schmerzpunkt) und diese Begründung in
      notiz mitschreiben - "warum genau dieser Prospect passt", nicht nur
      der Firmenname.
   d) VOR jedem save_prospect prüfen, ob die Firma nicht längst existiert
      (get_combined_leads mit freitext=Firmenname UND audit_vault_close_matches
      im Zweifel) - keine Dubletten anlegen.
   e) Jeden so geprüften Treffer mit save_prospect anlegen (schreibt
      Vault-Lead UND Close-Lead in einem Schritt).
   Gilt genauso, wenn Sebastian einen bekannten Lead/Kunden als Vorlage für
   "finde mehr wie X" nennt (siehe Punkt 9, find_similar_leads_context).

   MANUELLER/FREIER Kontakt (Sebastian pastet oder tippt einen Kontakt direkt
   in den Chat, z.B. "Max Muster, Geschäftsführer, muster.de, auf der Messe
   getroffen" oder eine E-Mail-Signatur): KEINE Recherche nötig, keine
   Rückfrage nach einem festen Format - Firma/Name/E-Mail/Kontext selbst aus
   dem Freitext extrahieren und SOFORT mit save_prospect anlegen (quelle
   entsprechend setzen, z.B. "Messekontakt"/"Empfehlung"). save_prospect ist
   das flexible Eintragsfeld für "leg mir das in Close an" - keine Rückfrage
   nach zusätzlichen Pflichtfeldern, fehlende Angaben bleiben einfach leer.
2. BESTANDS-LEADS/LISTEN/FILTER: für JEDE Frage nach "meine Leads",
   "zeig mir...", einer Liste oder Tabelle von Leads IMMER get_combined_leads
   nutzen (führt Vault- UND Close-Leads in einer Abfrage zusammen, deckt
   Kombinationen wie Branche+Status+Score+letzter-Kontakt ab) statt Glob(Leads/)
   und close_search_leads einzeln von Hand zu kombinieren. Danach nach
   PLAYBOOK.md bewerten, status/score per update_lead_status setzen.
   Ergebnisse mit mehreren Zeilen IMMER als Markdown-Tabelle ausgeben.
3. DÜNNE DATEN: fehlen für eine Bewertung/Filterung Kernfelder (Branche,
   Größe, Produkt/Leistung, Zielgruppe), NIEMALS direkt beim Nutzer nachfragen.
   Erst enrich_lead aufrufen (zeigt was fehlt), die fehlenden Fakten per
   eigenem WebSearch recherchieren, dann per save_lead_enrichment
   zurückschreiben (Close-Note + Vault-Frontmatter). Den Nutzer NUR fragen,
   wenn die Websuche nichts Verwertbares liefert, oder die fehlende
   Information keine recherchierbare Tatsache ist, sondern eine echte
   Präferenzfrage an Sebastian (z.B. "was zählt für dich als perfekter Lead").
4. EXPORT: will Sebastian eine Liste/Tabelle als Datei/zum Herunterladen/
   Weiterleiten (nicht nur im Chat lesen), proaktiv export_leads mit den
   passenden Filtern anbieten bzw. direkt ausführen (xlsx bevorzugen, wenn
   nicht anders gewünscht) und den download_url als klickbaren Markdown-Link
   ausgeben - nicht stattdessen CSV-Rohtext in den Chat schreiben.
5. SALES-BRIEFS: für als "heiß" markierte Leads ein Brief verfassen (Firma,
   was wir wissen, vermutete Pain Points, 3 Gesprächsaufhänger, 1
   validierende Frage) und mit generate_sales_brief ablegen.
6. OUTREACH: personalisierte Texte NIE automatisch versenden - IMMER nur
   draft_outreach_email nutzen (legt einen Gmail-Entwurf an, Sebastian prüft
   und verschickt selbst).
7. CLOSE-SYNC: bereits bestehende Vault-Leads UND etablierte Kunden
   (Kunden/<Firma>/-Ordner - jemand, mit dem bereits Kontakt besteht) ohne
   close_lead_id über sync_lead_to_close verknüpfen; Gesprächsnotizen über
   create_close_note eintragen.
8. VAULT<->CLOSE-ABGLEICH: bei Anfragen wie "prüfe ob X auch in Close ist"/
   "was fehlt in Close"/"stimmen Vault und Close überein" IMMER
   audit_vault_close_matches nutzen (deckt sowohl Kunden/-Ordner als auch
   Leads/*.md ab, matched gegen ALLE Close-Leads per Namensabgleich - eine
   Firma wie in beiden Systemen vorhandenes 'F-Tronic' wird sonst nicht
   erkannt, weil Kunden/-Ordner nicht automatisch in get_combined_leads
   auftauchen). Ergebnis immer verständlich zusammenfassen:
   - neu_verknuepfbar: klarer Namensmatch, nur die Verknüpfung fehlt ->
     PROAKTIV per link_vault_to_close nachtragen (reiner Vault-Schreibzugriff,
     kein Risiko, legt nichts in Close an) und kurz melden was verknüpft wurde.
   - kunden_ohne_close_kontakt: etablierte Kunden ganz ohne Close-Eintrag ->
     NICHT automatisch anlegen. Liste zeigen und fragen, welche (oder ob
     alle) Sebastian jetzt per sync_lead_to_close in Close angelegt haben will.
   - leads_ohne_close_kontakt: analog für frische Leads, gleiches Vorgehen.
9. NEUE PROSPECTS AUF BASIS BEKANNTER LEADS/KUNDEN ("Recherchetool"): will
   Sebastian mehr Leads ähnlich zu einem bekannten Lead oder Kunden (z.B.
   "finde mehr wie F-Tronic"):
   a) IMMER zuerst find_similar_leads_context für den Referenz-Lead/-Kunden
      aufrufen.
   b) Bei typ 'kunde' zusätzlich NATIV per Glob/Read in dessen Vault-Ordner
      (Meetings/Dokumente/Angebote) lesen - dort steht der eigentliche
      Kontext (Branche, Größenordnung, wer dort Ansprechpartner war, welches
      Problem gelöst wurde), das schlanke Profil aus dem Tool allein reicht
      NICHT als Recherchegrundlage.
   c) Daraus ein präzises Suchprofil ableiten (Branche + Region +
      Größenordnung + der konkrete Schmerzpunkt, der bei der Referenz
      funktioniert hat) und PLAYBOOK.md-ICP gegenchecken - keine grobe
      "ähnliche Firma"-Suche.
   d) Mit diesem Profil GEZIELT per WebSearch recherchieren (mehrere
      Suchanfragen aus unterschiedlichen Winkeln: Branchenverzeichnisse,
      Regionalsuche, "Wettbewerber von <Referenzfirma>"), pro Kandidat wie
      in Punkt 1 mehrere Quellen gegenchecken statt eines einzelnen Treffers.
   e) Vor dem Anlegen gegen bestehende Leads/Kunden prüfen (get_combined_leads/
      audit_vault_close_matches) - keine Dubletten.
   f) JEDEN so geprüften Treffer mit save_prospect anlegen (schreibt
      Vault-Lead UND Close-Lead in einem Schritt), notiz mit der konkreten
      Ähnlichkeitsbegründung zur Referenzfirma füllen.

Antworte auf Deutsch, direkt und knapp. Nutze IMMER die passenden Tools statt
zu behaupten, etwas nicht zu können - alle hier beschriebenen Aktionen sind
über native Tools oder die lead-agent-tools-MCP-Tools abgedeckt."""


def _subprocess_env() -> dict:
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token:
        raise ClaudeAgentError("CLAUDE_CODE_OAUTH_TOKEN fehlt im Container (einmalig `claude setup-token` ausführen).")
    # ANTHROPIC_API_KEY hat sonst stillschweigend Vorrang vor dem Abo-Token
    # (empirisch am Hauptbackend verifiziert, siehe claude_cli.py).
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    env["CLAUDE_PROJECT_DIR"] = str(APP_DIR)
    return env


def ensure_mcp_approval() -> None:
    """Trägt die MCP-Server-Freigabe für dieses Projekt in ~/.claude.json ein
    (kein TTY im Headless-Modus für den Freigabe-Dialog, sonst bliebe
    lead-agent-tools für immer "Pending approval") - Kopie des Verfahrens aus
    backend/app/services/claude_cli.py::ensure_mcp_approval(), idempotent,
    beim FastAPI-Startup aufgerufen (siehe server.py)."""
    config_path = Path.home() / ".claude.json"
    project_key = str(APP_DIR)
    try:
        data = json.loads(config_path.read_text()) if config_path.exists() else {}
    except (json.JSONDecodeError, OSError):
        data = {}
    projects = data.setdefault("projects", {})
    project = projects.setdefault(project_key, {})
    enabled = project.setdefault("enabledMcpjsonServers", [])
    if MCP_SERVER_NAME not in enabled:
        enabled.append(MCP_SERVER_NAME)
    project["hasTrustDialogAccepted"] = True
    config_path.write_text(json.dumps(data, indent=2))


def terminate_process_tree(proc: subprocess.Popen, timeout: float = 3.0) -> None:
    """Killt proc UND die von ihm gestartete Prozessgruppe (MCP-Server-
    Kindprozess) und reap't sie danach - Kopie von claude_cli.py, gleiche
    Zombie-Prozess-Begründung (siehe dortiger Kommentar, 2026-08-06)."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        pass


def _format_history(messages: list[dict], budget_chars: int = 12000) -> str:
    if len(messages) <= 1:
        return ""
    picked: list[str] = []
    used = 0
    for m in reversed(messages[:-1]):
        role = "Nutzer" if m.get("role") == "user" else "Assistent"
        line = f"{role}: {m.get('content', '')}"
        if used + len(line) > budget_chars and picked:
            break
        picked.append(line)
        used += len(line)
    picked.reverse()
    return "\n\n".join(picked)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_chat(messages: list[dict], model: str):
    """Ein frischer `claude -p`-Subprocess pro Nachricht (kein Warm-Pool wie
    beim Hauptbackend - der Lead-Agent hat kein Dauerlast-Chat-Volumen, das
    den Aufwand rechtfertigt; gleiche bewusste Vereinfachung wie
    dev-agent/server.py). Historie geht als Text-Transkript in den Prompt
    (kein --resume)."""
    resolved_model = model if model in ALLOWED_MODELS else DEFAULT_MODEL
    last_msg = messages[-1]["content"] if messages else ""
    history_block = _format_history(messages)
    prompt = last_msg
    if history_block:
        prompt = f"<bisherige_unterhaltung>\n{history_block}\n</bisherige_unterhaltung>\n\n{prompt}"

    cmd = [
        CLAUDE_BIN, "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model", resolved_model,
        "--system-prompt", SYSTEM_PROMPT,
        "--add-dir", str(get_settings().vault_path),
        "--tools", "Read,Glob,Grep,WebSearch",
        "--allowedTools", f"Read,Glob,Grep,WebSearch,mcp__{MCP_SERVER_NAME}__*",
        "--mcp-config", str(MCP_CONFIG_PATH),
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", "3.00",
    ]

    try:
        env = _subprocess_env()
    except ClaudeAgentError as ex:
        yield _sse({"error": str(ex)})
        yield "data: [DONE]\n\n"
        return

    try:
        proc = subprocess.Popen(
            cmd, env=env, cwd=str(APP_DIR),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, start_new_session=True,
        )
    except Exception as ex:
        yield _sse({"error": str(ex)})
        yield "data: [DONE]\n\n"
        return

    try:
        time.sleep(MCP_WARMUP_SECONDS)
        user_event = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}}
        proc.stdin.write(json.dumps(user_event) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        # Token-Deltas sind der primäre Pfad (empirisch am Hauptbackend
        # verifiziert, siehe claude_cli.py-Kommentar zu stream_event) - das
        # "assistant"-Event mit dem kompletten Block kommt danach trotzdem,
        # als Fallback falls der Delta-Stream einmal ausbleibt (andere
        # CLI-Version). delta_buffer verhindert, den bereits gestreamten Text
        # dann ein zweites Mal zu schicken.
        delta_buffer = ""
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = event.get("type")
            if etype == "stream_event":
                ev = event.get("event", {})
                ev_type = ev.get("type")
                if ev_type == "content_block_start":
                    delta_buffer = ""
                elif ev_type == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        delta_buffer += delta["text"]
                        yield _sse({"chunk": delta["text"]})
            elif etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    if block.get("type") == "text" and block.get("text") and block["text"] != delta_buffer:
                        yield _sse({"chunk": block["text"]})
            elif etype == "result":
                if event.get("is_error"):
                    yield _sse({"error": event.get("result", "Unbekannter Fehler")})
                yield _sse({"usage": event.get("usage"), "total_cost_usd": event.get("total_cost_usd")})
        proc.wait(timeout=600)
        if proc.returncode != 0:
            stderr = proc.stderr.read()
            yield _sse({"error": f"claude -p exit {proc.returncode}: {stderr[:500]}"})
    except Exception as ex:
        yield _sse({"error": str(ex)})
    finally:
        terminate_process_tree(proc)

    yield "data: [DONE]\n\n"
