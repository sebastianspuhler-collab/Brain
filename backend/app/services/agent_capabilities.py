"""Fähigkeits-Gruppen für Agenten-Berechtigungen (Umsetzungsplan 2026-07-25).

Bisher hatte jeder Agent-Aufruf Zugriff auf alle Tools, unabhängig von seiner
Konfiguration. Diese Datei bildet die Brücke: Gruppen-Keys (auf dem Agent
gespeichert, agents_service.py) werden hier auf konkrete native Tool-Namen
und MCP-Tool-Namen (mcp_server.py) expandiert, die claude_cli.spawn_process()
dann als --tools/--allowedTools übergibt. Gruppen-Keys statt roher
Tool-Namen, damit sich die Zuordnung später ändern lässt, ohne agents.json
migrieren zu müssen.

Bewusst KEIN Ordner-/Zuständigkeitsbereich-Scoping hier (Sebastian
2026-07-25, nach Live-Test auf dem VPS): --add-dir schränkt den echten
Datei-Zugriff des claude-CLI-Subprozesses nicht ein (rein additiv, keine
Sandbox) - ein Zuständigkeitsbereich wird stattdessen im Zusatz-Prompt
(system_prompt_zusatz) formuliert. ordner_filter bleibt wie bisher nur eine
Einschränkung der RAG-Suche (rag.search_with_sources())."""

NATIVE_TOOL_GROUPS: dict[str, list[str]] = {
    "files_read": ["Read", "Glob", "Grep"],
    "files_write": ["Write", "Edit"],
    "web_recherche": ["WebSearch"],
}

MCP_TOOL_GROUPS: dict[str, list[str]] = {
    "linkedin": [
        "push_to_buffer", "generate_linkedin_ideas", "generate_linkedin_posts",
        "write_linkedin_post_draft", "list_linkedin_ideas", "list_linkedin_posts",
        "revise_linkedin_post", "schedule_linkedin_post", "set_linkedin_direction",
        "generate_carousel",
    ],
    "youtube": ["list_youtube_videos", "generate_youtube_metadata", "push_youtube_to_buffer"],
    "email_anhaenge": ["search_emails", "download_attachment"],
    "meetings_suche": ["search_meetings"],
}

CAPABILITY_GROUPS: dict[str, list[str]] = {**NATIVE_TOOL_GROUPS, **MCP_TOOL_GROUPS}

CAPABILITY_LABELS: dict[str, str] = {
    "files_read": "Dateien lesen",
    "files_write": "Dateien schreiben",
    "web_recherche": "Web-Recherche",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "email_anhaenge": "E-Mail/Anhänge",
    "meetings_suche": "Meetings-Suche",
}


def expand(group_keys: list[str] | None) -> tuple[list[str], list[str]] | None:
    """None => uneingeschränkt (Aufrufer lässt --tools/--allowedTools bei
    spawn_process()'s eigenen Defaults). Eine (ggf. leere) Liste => genau
    diese Tools, sonst nichts. Gibt (native_tools, allowed_tools) zurück:
    native Tool-Namen landen in beiden (--tools UND --allowedTools), MCP-Tool-
    Namen (namespaced) nur in allowed_tools - --tools listet laut
    claude_cli.py nur native Namen, MCP-Verfügbarkeit läuft über
    --mcp-config, Freigabe einzelner MCP-Tools über --allowedTools."""
    if group_keys is None:
        return None
    native: list[str] = []
    mcp: list[str] = []
    for key in group_keys:
        if key in NATIVE_TOOL_GROUPS:
            native.extend(NATIVE_TOOL_GROUPS[key])
        elif key in MCP_TOOL_GROUPS:
            mcp.extend(f"mcp__prozessia-tools__{name}" for name in MCP_TOOL_GROUPS[key])
    return native, native + mcp
