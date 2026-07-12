#!/usr/bin/env python3
"""
Interaktives Setup für Google & Microsoft Credentials.
Führt dich Schritt-für-Schritt durch die Konfiguration.

Ausführen: python3 setup_credentials.py
"""

import json
import os
import sys
from pathlib import Path

def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def google_setup():
    """Interaktives Google Credentials Setup"""
    print_section("📧 GOOGLE WORKSPACE SETUP")
    
    print("\n1️⃣  OAuth Client ID (für Gmail/Drive):")
    print("   → Gehe zu: https://console.cloud.google.com")
    print("   → APIs & Dienste → Credentials")
    print("   → Create Credentials → OAuth 2.0 Client ID")
    print("   → Application type: Desktop")
    print("   → Download as JSON")
    print("\n   Eintragen (Strg+D zum Beenden):")
    
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    
    google_creds = "".join(lines).strip()
    
    if google_creds:
        try:
            json.loads(google_creds)
            return {"GOOGLE_CREDENTIALS_JSON": google_creds}
        except json.JSONDecodeError:
            print("❌ Kein gültiges JSON. Übersprungen.")
            return {}
    
    return {}

def microsoft_setup():
    """Interaktives Microsoft Credentials Setup"""
    print_section("🔵 MICROSOFT 365 SETUP")
    
    print("\n Siehe auch: https://portal.azure.com → App-Registrierungen")
    print(" Oder: _agent/ms_setup.md\n")
    
    client_id = input("MS_CLIENT_ID: ").strip()
    tenant_id = input("MS_TENANT_ID: ").strip()
    client_secret = input("MS_CLIENT_SECRET (optional): ").strip()
    
    result = {}
    if client_id:
        result["MS_CLIENT_ID"] = client_id
    if tenant_id:
        result["MS_TENANT_ID"] = tenant_id
    if client_secret:
        result["MS_CLIENT_SECRET"] = client_secret
    
    return result

def twenty_setup():
    """Twenty CRM Setup"""
    print_section("🎯 TWENTY CRM SETUP")
    
    api_url = input("TWENTY_API_URL (z.B. https://your-instance.com/graphql): ").strip()
    api_key = input("TWENTY_API_KEY (Bearer Token): ").strip()
    
    result = {}
    if api_url:
        result["TWENTY_API_URL"] = api_url
    if api_key:
        result["TWENTY_API_KEY"] = api_key
    
    return result

def main():
    print_section("Prozessia Brain – Credentials Setup")
    print("💡 Tipp: Öffne .env.example in einem Editor als Referenz")
    
    backend_env = Path(__file__).parent / ".env"
    
    credentials = {}
    
    # Google
    print("\n🔹 Möchtest du Google Workspace konfigurieren? (y/n) ", end="")
    if input().lower().startswith("y"):
        credentials.update(google_setup())
    
    # Microsoft
    print("\n🔹 Möchtest du Microsoft 365 konfigurieren? (y/n) ", end="")
    if input().lower().startswith("y"):
        credentials.update(microsoft_setup())
    
    # Twenty CRM
    print("\n🔹 Möchtest du Twenty CRM konfigurieren? (y/n) ", end="")
    if input().lower().startswith("y"):
        credentials.update(twenty_setup())
    
    if not credentials:
        print("\n⚠️  Keine Credentials konfiguriert. Beende.")
        return
    
    # Schreibe in .env
    print_section("💾 Speichern")
    
    env_content = ""
    if backend_env.exists():
        env_content = backend_env.read_text()
    
    for key, value in credentials.items():
        if key in env_content:
            # Ersetze
            lines = env_content.split("\n")
            new_lines = []
            for line in lines:
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}")
                else:
                    new_lines.append(line)
            env_content = "\n".join(new_lines)
        else:
            # Anhängen
            env_content += f"\n{key}={value}\n"
    
    backend_env.write_text(env_content)
    print(f"✅ Gespeichert in: {backend_env}")
    
    print("\n🚀 Nächste Schritte:")
    print("   1. Backend starten: python -m uvicorn app.main:app --port 9000")
    print("   2. Frontend starten: cd frontend && npm run dev")
    print("   3. http://localhost:5173 im Browser öffnen")

if __name__ == "__main__":
    main()
