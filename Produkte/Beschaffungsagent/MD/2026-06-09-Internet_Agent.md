---
tags:
  - n8n
  - KI-Agent
  - Google Gemini
  - Airtop
  - Browser-Automatisierung
quelle: Internet_Agent.json
datum: 2026-06-09
kategorie: Produkt
---

# Internet_Agent

JSON-Export eines n8n-Workflows namens 'Internet-Agent', der einen browserbasierten KI-Agenten implementiert. Der Workflow nutzt Google Gemini 2.5 Flash als Sprachmodell, Airtop für Browser-Sessions und Fenstersteuerung sowie einen Memory-Buffer für Gesprächskontext. Der Agent kann über Chat-Nachrichten ausgelöst werden und ist in der Lage, Webseiten aufzurufen und zu verarbeiten.

## Vollständiger Inhalt
[JSON-Datei] {
  "name": "Internet-Agent",
  "nodes": [
    {
      "parameters": {
        "options": {}
      },
      "type": "@n8n/n8n-nodes-langchain.chatTrigger",
      "typeVersion": 1.1,
      "position": [
        200,
        -160
      ],
      "id": "4dde6ee1-e813-4bcc-9ef7-e92d3e07f2b6",
      "name": "When chat message received",
      "webhookId": "5098f362-c62a-4b7b-9370-0129f90e8553"
    },
    {
      "parameters": {},
      "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow",
      "typeVersion": 1.3,
      "position": [
        440,
        300
      ],
      "id": "aa0e94f4-2c2f-4063-ae42-4099ee43409a",
      "name": "Memory"
    },
    {
      "parameters": {
        "modelName": "models/gemini-2.5-flash-preview-04-17",
        "options": {}
      },
      "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini",
      "typeVersion": 1,
      "position": [
        300,
        300
      ],
      "id": "fc6f49c7-0c3d-4695-af59-82d30d27bcc7",
      "name": "Google Gemini Chat Model",
      "credentials": {
        "googlePalmApi": {
          "id": "AqH11RGGAEKsWLFF",
          "name": "Google Gemini(PaLM) Api account"
        }
      }
    },
    {
      "parameters": {
        "profileName": "={{ $json.profile_name }}",
        "additionalFields": {}
      },
      "id": "a4f5f13e-9505-41b6-a8e9-ff8e6bdc91ef",
      "name": "Session",
      "type": "n8n-nodes-base.airtop",
      "position": [
        380,
        -320
      ],
      "typeVersion": 1,
      "credentials": {
        "airtopApi": {
          "id": "xqAhqADK2aYvvtbL",
          "name": "Airtop account"
        }
      }
    },
    {
      "parameters": {
        "resource": "window",
        "url": "={{ $('When Executed by Another Workflow').item.json.url }}",
        "getLiveView": true,
        "additionalFields": {}
      },
      "id": "98850403-e61b-42bb-8380-35819fad3e5d",
      "name": "Window",
      "type": "n8n-nodes-base.airtop",
      "position": [
        660,
        -320
      ],
      "typeVersion": 1,
      "credentials": {
        "airtopApi": {
          "id": "xqAhqADK2aYvvtbL",
          "name": "Airtop account"
        }
      }
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "0a0680af-39bd-4bc7-b9cd-84c1766c79a1",
              "name": "sessionId",
              "type": "string",
              "value": "={{ $('Session').item.json.sessionId }}"
            },
            {
              "id": "13940ee8-c1d4-4718-a7b4-176c44c097b7",
              "name": "windowId",
              "type": "string",
              "value": "={{ $('Window').item.json.data.windowId }}"
            },
            {
              "id": "a0f2005c-2cd2-4a8d-891b-a4759b72a124",
              "name": "output",
              "type": "string",
              "value": "Session and window created successfully"
            }
          ]
        },
        "options": {}
      },
      "id": "3aa24336-405f-419a-9354-b9
