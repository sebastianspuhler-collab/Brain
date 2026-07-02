"""Kunden-Onboarding-Automatisierung: Sebastian füllt nach einem gewonnenen
Deal ein Formular aus, der Rest läuft automatisch (Drive-Ordner, Vertrag,
AVV, GitHub-Repo, Team-Benachrichtigung) - als SSE-Stream mit Live-Status."""
import asyncio
import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.deps import get_current_user
from app.services import avv_service, contract_service, drive_service, email_service, github_service, onboarding_ai

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

PRODUCT_REPOS = {
    "beschaffungsagent": ("Schaufler-Beschaffungsagent", "beschaffungsagent", avv_service.BESCHAFFUNGSAGENT_AVV),
    "stuecklistenagent": ("Stuecklistenagent", "stuecklistenagent", avv_service.STUECKLISTENAGENT_AVV),
}


def _sse(step: str, status: str, **extra) -> str:
    payload = {"step": step, "status": status, **extra}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _resolve_produkt_info(data: dict) -> tuple[str, str, list[str]]:
    """Gibt (produkt_name, produkt_beschreibung_fuer_vertrag, features) zurück."""
    projekttyp = data.get("projekttyp")
    if projekttyp in PRODUCT_REPOS:
        avv_data = PRODUCT_REPOS[projekttyp][2]
        return avv_data["produkt_name"], avv_data["produkt_beschreibung"], data.get("features", [])
    # neues_projekt: kommt aus der (ggf. vom Nutzer editierten) KI-Analyse
    return (
        data.get("produkt_name", ""),
        data.get("contract_description") or data.get("produkt_beschreibung", ""),
        data.get("features", []),
    )


def _resolve_avv_data(data: dict) -> dict:
    projekttyp = data.get("projekttyp")
    if projekttyp in PRODUCT_REPOS:
        return PRODUCT_REPOS[projekttyp][2]
    return {
        "produkt_name": data.get("produkt_name", ""),
        "produkt_beschreibung": data.get("produkt_beschreibung", ""),
        "ki_dienst_beschreibung": data.get("ki_dienst_beschreibung", ""),
        "unterauftragnehmer_ki_firma": data.get("unterauftragnehmer_ki_firma", ""),
        "unterauftragnehmer_ki_land": data.get("unterauftragnehmer_ki_land", ""),
        "unterauftragnehmer_ki_region": data.get("unterauftragnehmer_ki_region", ""),
        "unterauftragnehmer_ki_leistung": data.get("unterauftragnehmer_ki_leistung", ""),
    }


def _build_readme(data: dict) -> str:
    lines = [f"# {data.get('project_title') or data.get('kundenname', '')}", "", data.get("contract_description", ""), ""]
    if data.get("tech_stack"):
        lines += ["## Tech-Stack", ""] + [f"- {t}" for t in data["tech_stack"]] + [""]
    if data.get("implementation_plan"):
        lines += ["## Implementierungsplan", ""]
        for phase in data["implementation_plan"]:
            lines.append(f"### {phase.get('phase', '')}: {phase.get('title', '')} ({phase.get('duration', '')})")
            lines += [f"- [ ] {task}" for task in phase.get("tasks", [])]
            lines.append("")
    return "\n".join(lines)


async def _run_onboarding(data: dict, files: list[tuple[str, bytes]], toggles: dict):
    drive_link = ""
    github_link = ""
    folders: dict[str, str] = {}
    kundenname = data.get("kundenname", "")

    if toggles.get("drive_folders"):
        yield _sse("drive_folders", "running", message="Erstelle Drive Ordnerstruktur...")
        try:
            result = await asyncio.to_thread(drive_service.create_customer_folder_structure, kundenname)
            folders = result["folders"]
            drive_link = result["root_link"]
            yield _sse("drive_folders", "done", link=drive_link)
        except Exception as ex:
            yield _sse("drive_folders", "error", message=str(ex))
            yield _sse("complete", "error", drive_link=drive_link, github_link=github_link)
            return

    if toggles.get("file_upload") and files:
        yield _sse("file_upload", "running", message="Lade Dateien hoch...")
        try:
            target = folders.get("01_Onboarding/Kundendokumente")
            if target:
                for filename, content in files:
                    await asyncio.to_thread(drive_service.upload_file, target, filename, content)
            yield _sse("file_upload", "done")
        except Exception as ex:
            yield _sse("file_upload", "error", message=str(ex))
            yield _sse("complete", "error", drive_link=drive_link, github_link=github_link)
            return

    if toggles.get("contract"):
        yield _sse("contract", "running", message="Generiere Dienstleistungsvertrag...")
        try:
            produkt_name, produkt_beschreibung, features = _resolve_produkt_info(data)
            contract_md = contract_service.generate_contract(data, produkt_name, produkt_beschreibung, features)
            vertraege_folder = folders.get("00_Verträge")
            if vertraege_folder:
                await asyncio.to_thread(
                    drive_service.upload_file,
                    vertraege_folder,
                    f"Dienstleistungsvertrag_{kundenname}.md",
                    contract_md.encode("utf-8"),
                    "text/markdown",
                )
            yield _sse("contract", "done")
        except Exception as ex:
            yield _sse("contract", "error", message=str(ex))

    if toggles.get("avv"):
        yield _sse("avv", "running", message="Generiere AVV...")
        try:
            avv_data = _resolve_avv_data(data)
            replacements = avv_service.build_replacements(data, avv_data)
            docx_bytes = await asyncio.to_thread(avv_service.fill_avv, replacements)
            vertraege_folder = folders.get("00_Verträge")
            if vertraege_folder:
                await asyncio.to_thread(
                    drive_service.upload_file,
                    vertraege_folder,
                    f"AVV_{kundenname}.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            yield _sse("avv", "done")
        except Exception as ex:
            yield _sse("avv", "error", message=str(ex))

    if toggles.get("github"):
        yield _sse("github", "running", message="Erstelle GitHub Repository...")
        try:
            projekttyp = data.get("projekttyp")
            if projekttyp in PRODUCT_REPOS:
                source_repo, suffix, _ = PRODUCT_REPOS[projekttyp]
                result = await asyncio.to_thread(
                    github_service.fork_product_repo,
                    source_repo,
                    kundenname,
                    suffix,
                    data.get("features", []),
                    data.get("neue_funktion", ""),
                )
            else:
                result = await asyncio.to_thread(
                    github_service.create_project_repo,
                    data.get("repo_name", github_service.slugify(kundenname)),
                    _build_readme(data),
                    data.get("ticket_plan", []),
                )
            github_link = result["repo_url"]
            yield _sse("github", "done", link=github_link)
        except Exception as ex:
            yield _sse("github", "error", message=str(ex))

    if toggles.get("notification"):
        yield _sse("notification", "running", message="Sende Email-Notification...")
        try:
            activated = [k for k, v in toggles.items() if v]
            await asyncio.to_thread(email_service.send_onboarding_notification, data, drive_link, github_link, activated)
            yield _sse("notification", "done")
        except Exception as ex:
            yield _sse("notification", "warning", message=str(ex))

    yield _sse("complete", "done", drive_link=drive_link, github_link=github_link)


@router.post("/analyze")
async def analyze_project(
    beschreibung: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    user: str = Depends(get_current_user),
):
    file_contents = [(f.filename or "datei", await f.read()) for f in files]
    return await asyncio.to_thread(onboarding_ai.analyze_new_project, beschreibung, file_contents)


@router.post("")
async def start_onboarding(
    data: str = Form(...),
    toggles: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    user: str = Depends(get_current_user),
):
    parsed_data = json.loads(data)
    parsed_toggles = json.loads(toggles)
    file_contents = [(f.filename or "datei", await f.read()) for f in files]

    return StreamingResponse(
        _run_onboarding(parsed_data, file_contents, parsed_toggles),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
