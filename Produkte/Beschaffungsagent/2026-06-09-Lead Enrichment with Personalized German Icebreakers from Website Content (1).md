---
tags:
  - n8n
  - Lead-Enrichment
  - Automatisierung
  - Icebreaker
  - KI-Workflow
quelle: Lead Enrichment with Personalized German Icebreakers from Website Content (1).json
datum: 2026-06-09
kategorie: Produkt
---

# Lead Enrichment with Personalized German Icebreakers from Website Content (1)

n8n-Workflow zur automatisierten Lead-Anreicherung mit personalisierten deutschen Icebreakern auf Basis von Website-Inhalten. Der Workflow bereinigt Lead-Daten, prüft E-Mail und Website-URL und extrahiert anschließend HTML-Inhalte zur Weiterverarbeitung per KI. Typisches Automatisierungs-Asset für den Vertriebseinsatz.

## Vollständiger Inhalt
[JSON-Datei] {
  "name": "Lead Enrichment with Personalized German Icebreakers from Website Content",
  "nodes": [
    {
      "parameters": {
        "options": {}
      },
      "id": "5650ecb7-4b78-4cc7-9743-abcc50046180",
      "name": "Split In Batches",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 3,
      "position": [
        1088,
        304
      ]
    },
    {
      "parameters": {
        "mode": "runOnceForEachItem",
        "jsCode": "// Clean Data (per item) – wie zuvor funktionierend\nconst d = { ...$json };\n\nfunction normalize(u) {\n  if (!u) return '';\n  u = String(u).trim();\n  if (!/^https?:\\/\\//i.test(u)) u = 'https://' + u;      // Schema ergänzen\n  u = u.replace(/^http:\\/\\//i, 'https://');              // https erzwingen\n  u = u.replace(/\\/+$/, '');                             // trailing slash weg\n  return u;\n}\n\nconst fn = (d.first_name || '').trim();\nconst firstClean = fn ? fn[0].toUpperCase() + fn.slice(1).toLowerCase() : '';\n\nconst origin = normalize(d.organization_website_url);\n\n// WICHTIG: bei “Run Once for Each Item”/Function Item EIN Objekt zurückgeben\nreturn {\n  json: {\n    ...d,\n    firstClean,\n    organization_website_url: origin || (d.organization_website_url || ''),\n    // für die nächsten Nodes (Fetch Page Content) setzen wir pageUrl gleich mit\n    pageUrl: origin || (d.organization_website_url || '')\n  }\n};\n"
      },
      "id": "1b3ca15c-d66d-4217-8ed1-52d893eb0837",
      "name": "Clean Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        1168,
        528
      ]
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict",
            "version": 2
          },
          "conditions": [
            {
              "id": "id-1",
              "leftValue": "={{ $('Clean Data').item.json.email }}",
              "operator": {
                "type": "string",
                "operation": "notEmpty"
              }
            },
            {
              "id": "id-2",
              "leftValue": "={{ $('Clean Data').item.json.organization_website_url }}",
              "operator": {
                "type": "string",
                "operation": "notEmpty"
              }
            }
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "id": "693f65d8-0851-4b0c-b09e-beb8b7140b32",
      "name": "Check Email and Website",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2.2,
      "position": [
        1520,
        352
      ]
    },
    {
      "parameters": {
        "operation": "extractHtmlContent",
        "dataPropertyName": "html_for_llm",
        "extractionValues": {
          "values": [
            {
              "key": "content",
              "cssSelector": "body",
              "returnValue": "html"
            }
          ]
        },
        
