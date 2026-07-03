---
tags:
  - Deployment
  - Docker
  - Traefik
  - Beschaffungsagent
  - Technische Dokumentation
quelle: Deployment-Anleitung Beschaffungsagent.pdf
datum: 2026-06-09
kategorie: Kunde
---

# Deployment-Anleitung Beschaffungsagent

Technische Deployment-Anleitung für den Schaufler Beschaffungsagenten mit Docker und Traefik als Reverse Proxy. Beschreibt das Einrichten neuer Multi-Instanzen inkl. Container-Konfiguration, DNS-Einträge, Umgebungsvariablen und Datenbankmanagement. Dient als Schritt-für-Schritt-Referenz für das operative Ausrollen des Systems auf Linux-Servern.

## Vollständiger Inhalt
Deployment-Anleitung
Schaufler Beschaffungsagent — Multi-Instanz Deployment mit Docker & Traefik
Inhalt
Voraussetzungen
Neue Instanz erstellen
docker-compose.yml anpassen
DNS-Eintrag anlegen
Umgebungsvariablen anpassen (.env)
config.yaml anpassen
Starten & Prüfen
Datenbank leeren (System zurücksetzen)
Instanz stoppen / löschen
Schnellreferenz
1. Voraussetzungen
Linux-Server mit Docker + Docker Compose installiert
Traefik läuft bereits als Reverse Proxy
Domain mit DNS-Zugang (z.B. Hostinger)
SSH-Zugang zum Server
2. Neue Instanz erstellen
2.1 P er SSH auf den Ser ver verbinden
ssh root@DEINE-SERVER-IP
2.2 Best ehendes S ystem k opier en
cp -r /pfad/zum/original /pfad/zum/neues-system
Beispiel:24.03.26, 16:02 Deployment-Anleitung Beschaffungsagent
file:///C:/Users/douioui/Documents/privat/Schaufler-Beschaffungsagent/docs/Deployment-Anleitung.html 1/11 cp -r ~/schaufler-agent/Schaufler-Beschaffungsagent ~/schaufler-
agent/Schaufler-Praesentation
2.3 Alle Dat en der neuen Instanz löschen
Wichtig: Dieser Schritt muss ausgeführt werden, damit die neue Instanz keine
Daten vom Original enthält.
# In das neue Verzeichnis wechseln
cd /pfad/zum/neues-system
# Datenbank komplett löschen
rm -f daten/agent.db
rm -f daten/agent.db-shm
rm -f daten/agent.db-wal
rm -f daten/agent.db-shm.bak
rm -f daten/agent.db-wal.bak
rm -f daten/agent.db.bak
# Test-DMS Daten löschen
rm -rf daten/test_dms
# Logs löschen
rm -f logs/*.log
# Dokumente löschen
rm -rf dokumente/auftragsbestaetigungen/*
rm -rf dokumente/messberichte/*
rm -rf dokumente/packlisten/*
rm -rf dokumente/versanddokumente/*24.03.26, 16:02 Deployment-Anleitung Beschaffungsagent
file:///C:/Users/douioui/Documents/privat/Schaufler-Beschaffungsagent/docs/Deployment-Anleitung.html 2/11 3. docker-compose.yml anpassen
In der neuen Instanz müssen 3 Dinge geändert werden:
3.1 Container -Namen
Jeder Container braucht einen eindeutigen Namen auf dem Server. Schema:
schaufler-KÜRZEL-api/frontend/agent
Service Original Neue Instanz (Beispiel)
api schaufler-api schaufler-praes-api
frontendschaufler-frontend schaufler-praes-frontend
agent schaufler-agent schaufler-praes-agent
3.2 T raefik -Labels (Domain + R outer-Name)
Im frontend-Service die Labels anpassen:
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.ROUTERNAME.rule=Host(`NEUE-DOMAIN`)"
  - "traefik.http.routers.ROUTERNAME.entrypoints=websecure"
  - "traefik.http.routers.ROUTERNAME.tls=true"
  - "traefik.http.routers.ROUTERNAME.tls.certresolver=myresolver"
  - 
"traefik.http.services.ROUTERNAME.loadbalancer.server.port=3000"
  - "traefik.docker.network=traefik_web"
Ersetze:
ROUTERNAME = eindeutiger Name (z.B. schaufler-praes)
NEUE-DOMAIN = Subdomain (z.B. kunde-x.prozessia.space)
Der certresolver-Name muss mit der Traefik-Konfiguration
übereinstimmen. Prüfen mit:
docker inspect TRAEFIK-CONTAINER --format '{{json .Config.Cmd}}'
3.3 Netzw erk-Name
Jede Instanz braucht ein eigenes internes Netzwerk:
networks:
  KÜRZEL-network:
    driver: bridge24.03.26, 16:0
