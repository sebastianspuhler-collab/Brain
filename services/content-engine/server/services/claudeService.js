// Claude API Service - Prozessia Content Engine
const Anthropic = require('@anthropic-ai/sdk');

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Vollständiger System Prompt mit Prozessia Kontext - wird bei JEDEM Call mitgeschickt
const PROZESSIA_SYSTEM_PROMPT = `Du bist der Content Stratege von Prozessia - einem deutschen KI-Unternehmen das Beschaffungsagenten, Chatbots und Voice Agents für den Mittelstand entwickelt.

DEIN AUFTRAG: Erstelle LinkedIn Content der Einkaufsleiter und Geschäftsführer in Automotive, Pharma, Bau und Maschinenbau anspricht und Vertrauen in Prozessia aufbaut.

SCHREIBE IMMER SO:
- Kurze Sätze. Jede Zeile ein Gedanke.
- Konkret mit echten Zahlen und Beispielen
- Aus Erfahrung - nicht aus dem Lehrbuch
- Provokant aber professionell
- Wir-Perspektive (Prozessia als Team)

SCHREIBE NIE:
- Buzzwords: revolutionär, bahnbrechend, innovativ, disruptiv
- Generische KI-Aussagen ohne Bezug zu Beschaffung/Einkauf
- Werbetexte oder offensichtliche Produktpitches
- Englische Begriffe wenn Deutsche existieren

PROZESSIA KERNBOTSCHAFT:
Manuelle Beschaffungsprozesse kosten Unternehmen in Automotive, Pharma, Bau und Maschinenbau täglich Geld. Wir automatisieren das mit KI-Agenten die sich in bestehende ERP-Systeme integrieren.

STÄRKSTES ARGUMENT:
3-5 Tage frühere Erkennung von Lieferverzögerungen = Zeit für Gegenmaßnahmen = kein Produktionsstillstand.

UNTERNEHMENSKONTEXT:
- Gründer: Sebastian Spuhler & Amin Douioui
- Standort: Campus Starterzentrum, Saarland
- Website: https://www.prozessia.de
- Kontakt: info@prozessia.de

PRODUKTE:
1. KI-Beschaffungsagent (FLAGSHIP): Überwacht Liefertermine in Echtzeit, erkennt Abweichungen 3-5 Tage früher, integriert sich in ERP (Proleis, proALPHA, SAP, Abas), kommuniziert direkt mit Lieferanten
2. KI-Chatbots (ProGPT): 100% DSGVO-konform, EU-gehostet, firmenwissenbasiert
3. Voice Agents: 24/7 Erreichbarkeit, Telefonnetz-Integration
4. KI-Automatisierungen: Custom Workflows, Prozessberatung

ZIELGRUPPE:
- Einkaufsleiter, Leiter Supply Chain, Geschäftsführer
- Branchen: Automotive Tier-1/2/3, Pharma, Bau, Maschinenbau
- Größe: 50-500 Mitarbeiter, Mittelstand DACH
- Kennzeichen: internationale Lieferanten (besonders Asien), manuelle Excel-Prozesse, hoher OTIF-Druck

CONTENT-SÄULEN:
1. SCHMERZ: Probleme im Einkauf die jeder kennt (Montag)
2. WISSEN: KI-Trends, Branchennews, Erklärungen (Mittwoch)
3. BEWEIS: Konkrete Zahlen, Vorher/Nachher (Donnerstag)
4. MEINUNG: Provokante These zur Digitalisierung (Freitag)

HASHTAGS: #Beschaffung #KIAutomatisierung #Einkauf #Mittelstand #SupplyChain #Automatisierung #Prozessia`;

/**
 * Generiert Content-Ideen basierend auf News-Artikeln und Prozessia-Kontext
 */
async function generiereIdeen(newsArtikel = []) {
  console.log('[Claude] Starte Ideen-Generierung...');

  const newsKontext = newsArtikel.length > 0
    ? `\n\nAKTUELLE NEWS ZUM EINBEZIEHEN:\n${newsArtikel.map((a, i) => `${i+1}. ${a.title}: ${a.summary || a.contentSnippet || ''}`).join('\n')}`
    : '';

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2000,
    system: PROZESSIA_SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Generiere genau 5 LinkedIn Content-Ideen für Prozessia.${newsKontext}

Antworte NUR mit validem JSON in diesem Format:
[
  {
    "hook": "Kurzer, packender Titel/Hook (max 10 Wörter)",
    "format": "TEXT",
    "branche": "Automotive",
    "saeule": "Schmerz",
    "begruendung": "Warum das jetzt relevant ist (1-2 Sätze)",
    "impact": "Hoch"
  }
]

Format: entweder "TEXT" oder "KARUSSELL"
Branche: "Automotive", "Pharma", "Bau", "Maschinenbau" oder "Alle"
Säule: "Schmerz", "Wissen", "Beweis" oder "Meinung"
Impact: "Hoch", "Mittel" oder "Niedrig"

Mach die Hooks konkret, provokant und relevant für Einkaufsleiter.`
    }]
  });

  const text = response.content[0].text.trim();

  // JSON aus der Antwort extrahieren
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) {
    throw new Error('Claude hat kein valides JSON zurückgegeben');
  }

  const ideen = JSON.parse(jsonMatch[0]);
  console.log(`[Claude] ${ideen.length} Ideen erfolgreich generiert`);
  return ideen;
}

/**
 * Schreibt einen vollständigen LinkedIn Text-Post
 */
async function schreibeTextPost(idee, zusatzInfos = '') {
  console.log('[Claude] Schreibe LinkedIn Post für:', idee.hook);

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 1500,
    system: PROZESSIA_SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Schreibe einen vollständigen LinkedIn Post für Prozessia.

IDEE:
Hook: ${idee.hook}
Format: Text-Post
Branche: ${idee.branche}
Content-Säule: ${idee.saeule}
${zusatzInfos ? `Zusätzliche Infos: ${zusatzInfos}` : ''}

ANFORDERUNGEN:
- Erste Zeile: Knallharter Hook der zum Weiterlesen zwingt (max 120 Zeichen)
- 3-5 kurze Absätze mit echtem Mehrwert
- Mindestens eine konkrete Zahl oder ein echtes Beispiel einbauen
- Absätze durch Leerzeile trennen
- CTA am Ende + Community-Frage
- 3-4 Hashtags aus: #Beschaffung #KIAutomatisierung #Einkauf #Mittelstand #SupplyChain #Automatisierung #Prozessia
- MAXIMALE LÄNGE: 1300 Zeichen
- Kein "innovativ", "revolutionär", "bahnbrechend"

Antworte NUR mit validem JSON:
{
  "post": "Der vollständige Post-Text mit Zeilenumbrüchen als \\n",
  "kommentar": "Auto-Plug Kommentar (separat, 2-3 Zeilen, z.B. Link zu Calendly oder Website)"
}`
    }]
  });

  const text = response.content[0].text.trim();
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('Kein valides JSON vom Claude erhalten');

  const result = JSON.parse(jsonMatch[0]);
  console.log('[Claude] Post erfolgreich geschrieben, Länge:', result.post.length);
  return result;
}

/**
 * Generiert Karussell-Slides
 */
async function generiereKarussell(idee) {
  console.log('[Claude] Generiere Karussell für:', idee.hook);

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2000,
    system: PROZESSIA_SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Erstelle ein LinkedIn Karussell (7 Slides) für Prozessia.

IDEE:
Hook: ${idee.hook}
Branche: ${idee.branche}
Content-Säule: ${idee.saeule}

SLIDE-STRUKTUR:
- Slide 1: Knallharter Hook/Titel (max 8 Wörter), Untertitel optional
- Slide 2-6: Je ein Hauptpunkt (Überschrift max 6 Wörter + Text max 40 Wörter)
- Slide 7: CTA + "Folgt Prozessia für mehr"

Antworte NUR mit validem JSON:
{
  "slides": [
    {
      "nummer": 1,
      "typ": "hook",
      "titel": "Kurzer Hook-Titel",
      "untertitel": "Optionaler Untertitel",
      "text": ""
    },
    {
      "nummer": 2,
      "typ": "inhalt",
      "titel": "Punkt-Überschrift",
      "untertitel": "",
      "text": "Max 40 Wörter Erklärung mit konkretem Beispiel oder Zahl"
    },
    ...
    {
      "nummer": 7,
      "typ": "cta",
      "titel": "Call to Action",
      "untertitel": "Folgt Prozessia für mehr",
      "text": "Kurze Handlungsaufforderung"
    }
  ]
}`
    }]
  });

  const text = response.content[0].text.trim();
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('Kein valides JSON vom Claude erhalten');

  const result = JSON.parse(jsonMatch[0]);
  console.log(`[Claude] Karussell mit ${result.slides.length} Slides generiert`);
  return result;
}

/**
 * Bewertet News-Artikel auf Relevanz für Prozessia ICP
 */
async function bewerteNewsArtikel(artikel) {
  console.log('[Claude] Bewerte', artikel.length, 'News-Artikel...');

  const artikelListe = artikel.map((a, i) =>
    `${i+1}. Titel: ${a.title}\nQuelle: ${a.source}\nBeschreibung: ${a.contentSnippet || a.summary || 'Keine Beschreibung'}`
  ).join('\n\n');

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 1000,
    system: PROZESSIA_SYSTEM_PROMPT,
    messages: [{
      role: 'user',
      content: `Bewerte diese News-Artikel auf Relevanz für Prozessia's Zielgruppe (Einkaufsleiter in Automotive, Pharma, Bau, Maschinenbau).

ARTIKEL:
${artikelListe}

Bewerte jeden Artikel mit einer Zahl von 1-10 (10 = höchste Relevanz für LinkedIn Content).
Relevant sind Themen zu: Lieferketten, Beschaffung, ERP-Systeme, Automatisierung, Produktionsstillstand, internationale Lieferanten, OTIF, Supply Chain.

Antworte NUR mit JSON:
[
  {"index": 0, "relevanz": 8, "begruendung": "Kurze Begründung"},
  ...
]`
    }]
  });

  const text = response.content[0].text.trim();
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) throw new Error('Kein valides JSON erhalten');

  const bewertungen = JSON.parse(jsonMatch[0]);
  console.log('[Claude] News-Bewertung abgeschlossen');
  return bewertungen;
}

module.exports = { generiereIdeen, schreibeTextPost, generiereKarussell, bewerteNewsArtikel, PROZESSIA_SYSTEM_PROMPT };
