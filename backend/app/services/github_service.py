"""GitHub-Repository-Automatisierung fürs Kunden-Onboarding: Fork der
Produkt-Repos (Beschaffungsagent/Stücklistenagent) oder ein frisches Repo
für individuelle Projekte, inkl. Issues aus dem KI-Ticketplan."""
from github import Github

from app.config import get_settings


def slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("_", "-")


def _org():
    settings = get_settings()
    client = Github(settings.github_token)
    return client.get_organization(settings.github_org)


def _features_markdown(features: list[str], neue_funktion: str) -> str:
    md = "# Enthaltene Features\n\n" + "\n".join(f"- {f}" for f in features)
    if neue_funktion:
        md += f"\n\n## Neue Funktion\n\n{neue_funktion}"
    return md


def fork_product_repo(source_repo: str, kundenname: str, suffix: str, features: list[str], neue_funktion: str) -> dict:
    """Forkt ein bestehendes Produkt-Repo (Beschaffungsagent/Stücklistenagent) für einen Kunden."""
    org = _org()
    source = org.get_repo(source_repo)
    new_name = f"{slugify(kundenname)}-{suffix}"
    fork = org.create_fork(source, name=new_name)
    fork.create_file("FEATURES.md", "Add FEATURES.md", _features_markdown(features, neue_funktion))
    return {"repo_name": fork.full_name, "repo_url": fork.html_url}


def create_project_repo(repo_name: str, readme_content: str, ticket_plan: list[dict]) -> dict:
    """Erstellt ein neues privates Repo für ein individuelles Projekt inkl. README + Tickets."""
    org = _org()
    repo = org.create_repo(name=repo_name, private=True, auto_init=True)
    repo.create_file("README.md", "Initial README", readme_content)
    for ticket in ticket_plan:
        repo.create_issue(
            title=ticket.get("title", "Ticket"),
            body=ticket.get("description", ""),
            labels=[ticket["type"]] if ticket.get("type") else [],
        )
    return {"repo_name": repo.full_name, "repo_url": repo.html_url}
