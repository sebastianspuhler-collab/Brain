---
tags:
  - n8n
  - Workflow
  - Präsentation
  - Gamma
  - Automatisierung
quelle: Gamma Presentation (1).json
datum: 2026-06-09
kategorie: Sales
---

# Gamma Presentation (1)

Ein n8n-Workflow (JSON-Export) zur automatischen Generierung von Präsentationen über die Gamma-Plattform. Der Workflow enthält ein Web-Formular, in dem Titel und Beschreibung der gewünschten Präsentation eingegeben werden können. Das UI ist mit einem futuristischen Neon-Design angepasst.

## Vollständiger Inhalt
[JSON-Datei] {
  "name": "Gamma Presentation",
  "nodes": [
    {
      "parameters": {
        "formTitle": "Generate Presentation ",
        "formDescription": "Generate any presentation you want ",
        "formFields": {
          "values": [
            {
              "fieldLabel": "Presentation Title ",
              "placeholder": "Enter presentation title ",
              "requiredField": true
            },
            {
              "fieldLabel": "Presentation Description",
              "placeholder": "What do you want the presentation to be about? ",
              "requiredField": true
            }
          ]
        },
        "options": {
          "customCss": "/* This section adds the bold, neon effect to your title */\n.n8n-form-html h1 {\n    color: #ffffff;\n    font-weight: bold; /* Makes the title bold as requested */\n    text-align: center;\n    margin-bottom: 20px; /* Adds some space below the title */\n    /* Neon glow effect inspired by your banner */\n    text-shadow:\n        0 0 5px #fff,\n        0 0 10px #fff,\n        0 0 15px #33FF99,\n        0 0 20px #33FF99,\n        0 0 25px #33FF99,\n        0 0 30px #33FF99;\n}\n\n\n:root {\n\t/* Font and size variables are kept as requested */\n\t--font-family: 'Open Sans', sans-serif;\n\t--font-weight-normal: 400;\n\t--font-weight-bold: 600;\n\t--font-size-body: 12px;\n\t--font-size-label: 14px;\n\t--font-size-test-notice: 12px;\n\t--font-size-input: 14px;\n\t--font-size-header: 20px;\n\t--font-size-paragraph: 14px;\n\t--font-size-link: 12px;\n\t--font-size-error: 12px;\n\t--font-size-html-h1: 28px;\n\t--font-size-html-h2: 20px;\n\t--font-size-html-h3: 16px;\n\t--font-size-html-h4: 14px;\n\t--font-size-html-h5: 12px;\n\t--font-size-html-h6: 10px;\n\t--font-size-subheader: 14px;\n\n\t/* Colors - Updated to match your banner's futuristic/neon theme */\n\t--color-background: #100E19; /* Dark space background */\n\t--color-card-bg: #1C1A2A; /* Slightly lighter card background */\n\t--color-card-border: #8A2BE2; /* Purple accent for borders */\n\t--color-card-shadow: rgba(51, 255, 153, 0.15); /* Neon green glow */\n\t--color-header: #F0F0F0; /* Main header text color (title is styled separately) */\n\t--color-label: #E0E0E0; /* Light text for labels */\n\t--color-input-border: #4a4a6a; /* Muted purple for input borders */\n\t--color-input-text: #000000; /* Black text for inside inputs (CHANGED AS REQUESTED) */\n\t--color-focus-border: #33FF99; /* Neon green for focus highlight */\n\t--color-submit-btn-bg: #33FF99; /* Neon green submit button */\n\t--color-submit-btn-text: #100E19; /* Dark text on button for contrast */\n\t--color-link: #A78BFA; /* Lighter purple for links */\n\t--color-html-text: #F0F0F0; /* General text color */\n\t--color-html-link: #33FF99; /* Neon green for links in HTML blocks */\n\t--color-header-subtext: #A0A0A0; /* Dimmer grey for sub-headers */\n\t--color-required: #33FF99; /* Neon green for required field indicators */\n\t--color-error: #FF4747; /* A bright re
