"""
Microsoft Login via Device Code Flow
Keine Redirect URI nötig — funktioniert immer.
Start: python3 _agent/ms_login_device.py
"""
import json, sys
from pathlib import Path
import msal, requests

VAULT = Path.home() / "Documents" / "Prozessia-Brain"
CONFIG_PATH     = VAULT / "_agent" / "ms_config.json"
TOKEN_CACHE_PATH = VAULT / "_agent" / "ms_token_cache.bin"

SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Calendars.ReadWrite",
    "https://graph.microsoft.com/User.Read",
]

cfg = json.loads(CONFIG_PATH.read_text())
cache = msal.SerializableTokenCache()
if TOKEN_CACHE_PATH.exists():
    cache.deserialize(TOKEN_CACHE_PATH.read_text())

app = msal.PublicClientApplication(
    client_id=cfg["client_id"],
    authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
    token_cache=cache,
)

# Silent login falls Token noch gültig
accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if result and "access_token" in result:
        print(f"✓ Bereits angemeldet als {accounts[0]['username']}")
        sys.exit(0)

# Device Code Flow
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    print("Fehler:", flow.get("error_description", "Unbekannt"))
    sys.exit(1)

print("\n" + "="*50)
print("  Gehe auf:  https://microsoft.com/devicelogin")
print(f"  Code:      {flow['user_code']}")
print("="*50)
print("\nWarte auf Login...")

result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    print("Fehler:", result.get("error_description", "Login fehlgeschlagen"))
    sys.exit(1)

if cache.has_state_changed:
    TOKEN_CACHE_PATH.write_text(cache.serialize())

me = requests.get(
    "https://graph.microsoft.com/v1.0/me",
    headers={"Authorization": f"Bearer {result['access_token']}"}
).json()

print(f"\n✓ Angemeldet als {me.get('displayName')} ({me.get('mail') or me.get('userPrincipalName')})")
print("→ Kalender ist jetzt aktiv.\n")
