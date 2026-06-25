---
tags: [dashboard]
---

# Prozessia Dashboard

## Aktive Kunden
```dataview
TABLE firma, hosting, produkt, erp
FROM "Kunden"
WHERE contains(tags, "aktiv")
SORT firma ASC
```

## Warm Leads
```dataview
TABLE firma, ansprechpartner, thema, naechster_termin
FROM "Kunden"
WHERE contains(tags, "warm")
SORT naechster_termin ASC
```

## Offene Aufgaben (alle Kunden)
```dataview
TASK
FROM "Kunden"
WHERE !completed
```

## Letzte Memos
```dataview
TABLE file.mtime AS "Geändert"
FROM "Memos"
SORT file.mtime DESC
LIMIT 10
```
