---
tags:
  - n8n-Workflow
  - Social-Media-Automatisierung
  - RSS-Feed
  - Content-Generierung
  - KI-Automatisierung
quelle: Automated Social Media Content Generation from News Sources.json
datum: 2026-06-09
kategorie: Produkt
---

# Automated Social Media Content Generation from News Sources

Dieses Dokument ist ein n8n-Workflow zur automatisierten Erstellung von Social-Media-Inhalten aus RSS-Nachrichtenquellen. Der Workflow wird täglich um 8:00 Uhr ausgelöst, liest einen konfigurierbaren RSS-Feed aus und verarbeitet die Nachrichtenartikel für die Content-Generierung. Konfigurationsdaten wie Feed-URL und Google-Sheet-IDs werden über Platzhalter eingebunden.

## Vollständiger Inhalt
[JSON-Datei] {
  "name": "Automated Social Media Content Generation from News Sources",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "triggerAtHour": 8
            }
          ]
        }
      },
      "id": "fe685181-cb0b-4cbc-a2a8-17d3fa62ebf0",
      "name": "Daily Trigger 08:00",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [
        0,
        0
      ]
    },
    {
      "parameters": {
        "assignments": {
          "assignments": [
            {
              "id": "id-1",
              "name": "rssUrl",
              "value": "<__PLACEHOLDER_VALUE__RSS Feed URL (e.g., https://feeds.feedburner.com/TechCrunch/)__>",
              "type": "string"
            },
            {
              "id": "id-2",
              "name": "googleSheetId",
              "value": "<__PLACEHOLDER_VALUE__Google Sheet ID for ContentIdeas__>",
              "type": "string"
            },
            {
              "id": "id-3",
              "name": "contentPostsSheetId",
              "value": "<__PLACEHOLDER_VALUE__Google Sheet ID for ContentPosts__>",
              "type": "string"
            }
          ]
        },
        "includeOtherFields": true,
        "options": {}
      },
      "id": "f6599390-d5a0-4b01-ba30-f20cea8a9f81",
      "name": "Workflow Configuration",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4,
      "position": [
        224,
        0
      ]
    },
    {
      "parameters": {
        "url": "={{ $('Workflow Configuration').first().json.rssUrl }}",
        "options": {
          "response": {
            "response": {}
          }
        }
      },
      "id": "ddaa7594-38d8-45e9-a417-54d695e20def",
      "name": "Fetch News RSS Feed",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.3,
      "position": [
        448,
        0
      ]
    },
    {
      "parameters": {
        "jsCode": "const items = $input.all();\nconst output = [];\n\nfor (const item of items) {\n  const data = item.json;\n  \n  // Handle different RSS feed structures\n  let newsItems = [];\n  \n  if (data.rss && data.rss.channel && data.rss.channel.item) {\n    newsItems = Array.isArray(data.rss.channel.item) ? data.rss.channel.item : [data.rss.channel.item];\n  } else if (data.feed && data.feed.entry) {\n    newsItems = Array.isArray(data.feed.entry) ? data.feed.entry : [data.feed.entry];\n  } else if (Array.isArray(data.items)) {\n    newsItems = data.items;\n  } else if (data.items) {\n    newsItems = [data.items];\n  }\n  \n  for (const newsItem of newsItems) {\n    output.push({\n      json: {\n        title: newsItem.title || newsItem.title?.[0] || '',\n        description: newsItem.description || newsItem.summary || newsItem.description?.[0] || newsItem.summary?.[0] || '',\n        link: newsItem.link || newsItem.link?.[0]?.['$']?.href || newsItem.link?.[0] || '',\n        pubDate: newsItem.pubDate || newsItem.p
