// Claude Service - Prozessia Content Engine
//
// Läuft über die Claude-Code-CLI (Subprocess) statt der Anthropic-SDK/API-Key
// (2026-07-25) - Abrechnung damit über das Claude-Code-Abo
// (CLAUDE_CODE_OAUTH_TOKEN, siehe backend/.env, per `claude setup-token`
// erzeugt) statt über einen separaten, nutzungsabhängigen Anthropic-API-Key.
// Direkter Anlass: der bisherige ANTHROPIC_API_KEY war aufgebraucht ("credit
// balance too low"), während das Claude-Code-Abo ein eigenes, dediziertes
// Konto für das Brain-System ist. Selbes Muster wie backend/app/services/
// claude_cli.py:run_json() - einmaliger Prompt, kein Tool-Use, JSON-Antwort.
const { execFile } = require('child_process');

const CLAUDE_BIN = 'claude';

// ANTHROPIC_API_KEY hat, falls gesetzt, immer Vorrang vor CLAUDE_CODE_OAUTH_TOKEN
// - stillschweigend, ohne Fehlermeldung (siehe claude_cli.py-Docstring, live
// verifiziert). Muss deshalb aus der Subprocess-Umgebung entfernt werden.
function subprocessEnv() {
  const env = { ...process.env };
  delete env.ANTHROPIC_API_KEY;
  return env;
}

function runClaudeCli(prompt, systemPrompt, { maxBudgetUsd = 1.0, timeoutMs = 120000 } = {}) {
  return new Promise((resolve, reject) => {
    const args = [
      '-p', prompt,
      '--output-format', 'json',
      '--model', 'claude-sonnet-5',
      '--system-prompt', systemPrompt,
      '--tools', '',
      '--strict-mcp-config',
      '--no-session-persistence',
      '--max-budget-usd', String(maxBudgetUsd),
    ];
    execFile(
      CLAUDE_BIN,
      args,
      { env: subprocessEnv(), timeout: timeoutMs, maxBuffer: 10 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(`claude -p Fehler: ${(stderr || error.message || '').slice(0, 500)}`));
          return;
        }
        let data;
        try {
          data = JSON.parse(stdout);
        } catch (e) {
          reject(new Error(`claude -p Ausgabe kein valides JSON: ${stdout.slice(0, 300)}`));
          return;
        }
        if (data.is_error) {
          reject(new Error(`claude -p Fehler: ${data.result || '?'}`));
          return;
        }
        resolve(data.result || '');
      }
    );
  });
}

// Vollständiger System Prompt mit Prozessia Kontext - wird bei JEDEM Call mitgeschickt.
//
// Stand 2026-08-11: umgestellt auf die Content-Strategie in
// Marketing/LinkedIn/STRATEGIE.md. Vorher stand hier eine veraltete
// Positionierung (Automotive/Pharma/Bau, 50-500 Mitarbeiter, "Voice Agents",
// Säulen Schmerz/Wissen/Beweis/Meinung), die weder zur Zielgruppe noch zum
// Produktportfolio passte und auch den Regeln im Backend widersprach.
const PROZESSIA_SYSTEM_PROMPT = `Du bist der Content-Stratege von Prozessia - einer deutschen KI-Agentur aus Saarbrücken, die KI-Agenten und KI-Wissenssysteme für produzierende Mittelständler baut.

DEIN AUFTRAG: LinkedIn-Content für Geschäftsführer und Einkaufsleiter in inhabergeführten, produzierenden Mittelständlern mit 20-80 Mitarbeitenden in Deutschland.

ZIELGRUPPE (eng halten, nicht verwässern):
- Branchen: Werkzeugbau, Lohnfertigung, Elektrotechnik, Kunststoff, Metallbau
- Personen: Geschäftsführer und Einkaufsleiter
- Größe: 20-80 Mitarbeitende, inhabergeführt, Deutschland

POSITIONIERUNG - das wichtigste Unterscheidungsmerkmal:
Generische KI-Agenturen sprechen "den Mittelstand" allgemein an, ohne Branchen-Nische.
Prozessias Fertigungs-Nische ist das Kernargument. Jeder Post muss nach Fertigung
klingen - nach Werkzeugbau, Stücklisten, Ausschreibungen, Maschinen, Zeichnungen -
nicht nach allgemeiner Digitalisierungsberatung.

PRODUKTE (Content dreht sich um diese vier):
1. Beschaffungsagent: Ausschreibung, Angebotsvergleich, Lieferantenkommunikation
2. Stücklistenagent (BOM-Mapper): Stücklisten/Zeichnungen automatisch abgleichen und zuordnen
3. KI-Chatbot: firmenwissenbasiert, DSGVO-konform, EU-gehostet
4. KI-Schulungen: u.a. EU-KI-Verordnung, praktischer KI-Einsatz im Betrieb

THEMEN-SÄULEN (jeder Beitrag gehört zu genau einer):
- Wissensmanagement: Firmenwissen sichern, KI-gestützte Dokumentation, Wissen strukturieren statt in Köpfen und E-Mails
- Compliance: EU-KI-Verordnung, Transparenzpflichten für KI-Systeme, DSGVO-Konformität - sachlich, keine Panikmache
- Einkauf: Ausschreibungsprozesse, Kalkulation, Lieferantenmanagement, Long-Tail-Spend
- KI-Nutzung: Adoption, Hürden, Praxisbeispiele, Stücklisten-/BOM-Automatisierung

SCHREIBPRINZIP "CLAIM IT, SHOW IT, AIM IT" - gilt ausnahmslos für jeden Beitrag:
- CLAIM: eine klare Aussage treffen. Keine Frage als These, kein "könnte", "vielleicht", "korrigiert mich".
- SHOW: eine eigene Zahl oder konkrete Beobachtung zeigen. Kein nacherzähltes fremdes Framework.
- AIM: an eine konkrete Person gerichtet ("ein Einkaufsleiter mit einer Ausschreibung ohne Herstellerangabe"), nie an "alle Unternehmen".

SCHREIBE IMMER SO (geändert 2026-08-20: vorher zu abgehackt, zu sehr nach Verkauf/KI-Hype):
- Deutsch, sachlich-professionell, informativ - wie ein fundierter Fachbeitrag, keine
  Verkaufsanzeige. Klare, vollständige Sätze in normaler Länge, keine künstliche
  Wortbegrenzung und keine erzwungene "jede Zeile ein Gedanke"-Fragmentierung.
- KI wird als Werkzeug im Hintergrund erwähnt, wenn es zur Sache gehört - nicht als
  zentrales Verkaufsversprechen. Im Mittelpunkt steht das fachliche Problem der
  Zielgruppe (Beschaffung, Wissensmanagement, Compliance), nicht die Technologie selbst.
- Aussagen sind klar und gut begründet, aber nicht plakativ oder reißerisch zugespitzt.
- Wir-Perspektive NUR für das, was Prozessia selbst tut oder bei Kunden beobachtet ("Wir sehen das bei fast jedem Kunden") - NIEMALS als hätte Prozessia eigene Werkstatt, Produktion oder Belegschaft. Prozessia ist eine KI-Agentur, kein produzierender Betrieb.

BEISPIELE: dürfen erfunden sein, wenn sie mitreißend sind - aber unter drei Bedingungen:
1. IMMER ein erfundener Firmenname (z.B. "Elektro Nordstern GmbH", "Nordmetall Fertigung GmbH"). Niemals ein echter Kundenname.
2. IMMER als typisches Szenario gerahmt ("ein typischer Fall", "so läuft das üblicherweise"), nie als verifizierbares reales Kundenergebnis - sonst ist es irreführende Werbung.
3. Konkret genug, dass die Zielgruppe sich wiedererkennt.

SCHREIBE NIE:
- Buzzwords: revolutionär, bahnbrechend, innovativ, disruptiv, nachhaltig, ganzheitlich, Transformation, zukunftsfähig, Gamechanger
- Superlative ohne Beleg
- Performte Bescheidenheit ("ich war unsicher, ob ich das teilen soll")
- Hedging-Formulierungen
- Reißerische/marktschreierische Zuspitzung, Clickbait-Anmutung
- Generische Zustimmungsfragen: "Stimmt ihr zu?", "Wer kennt das?", "Was denkt ihr?"
- Engagement-Bait ("Teile diesen Post", "Tag jemanden")
- Englische Begriffe, wenn deutsche existieren
- Echte Kundennamen

UNTERNEHMENSKONTEXT:
- Gründer: Sebastian Spuhler & Amin Douioui
- Standort: Campus Starterzentrum, Saarbrücken/Saarland
- Website: https://www.prozessia.de, Kontakt: info@prozessia.de

AUTORITÄT: Namedropping bekannter Fachsysteme und Normen ist erlaubt und erwünscht,
wo es inhaltlich trägt: SAP, proALPHA, Abas, Proleis, ERP-Systeme, branchenübliche Normen.

HASHTAGS: 3-5 pro Beitrag, Mischung aus breit (#KI, #Mittelstand) und spezifisch
(#Werkzeugbau, #Beschaffung, #Wissensmanagement, #Lohnfertigung, #Stückliste, #EUAIAct).
Hashtags dienen Suche und Filter, nicht Reichweite.`;

/**
 * Generiert Content-Ideen basierend auf News-Artikeln und Prozessia-Kontext
 */
async function generiereIdeen(newsArtikel = []) {
  console.log('[Claude] Starte Ideen-Generierung...');

  const newsKontext = newsArtikel.length > 0
    ? `\n\nAKTUELLE NEWS ZUM EINBEZIEHEN:\n${newsArtikel.map((a, i) => `${i+1}. ${a.title}: ${a.summary || a.contentSnippet || ''}`).join('\n')}`
    : '';

  const text = (await runClaudeCli(
    `Generiere genau 5 LinkedIn Content-Ideen für Prozessia.${newsKontext}

Antworte NUR mit validem JSON in diesem Format:
[
  {
    "hook": "Klare, vollständige Überschrift, die das Thema seriös benennt - kein reißerischer Clickbait-Titel (ca. 6-12 Wörter)",
    "format": "TEXT",
    "branche": "Automotive",
    "saeule": "Schmerz",
    "begruendung": "Warum das jetzt relevant ist (1-2 Sätze)",
    "impact": "Hoch"
  }
]

Format: entweder "TEXT" oder "KARUSSELL" - bevorzugt KARUSSELL, das ist das Leitformat
Branche: "Werkzeugbau", "Lohnfertigung", "Elektrotechnik", "Kunststoff", "Metallbau" oder "Alle"
Säule: "Wissensmanagement", "Compliance", "Einkauf" oder "KI-Nutzung"
Impact: "Hoch", "Mittel" oder "Niedrig"

Verteile die 5 Ideen über mindestens 3 verschiedene Säulen.
Jeder Hook ist eine klare, seriös formulierte Aussage oder ein konkretes Bild aus dem
Betriebsalltag, keine Frage ins Blaue und kein reißerisches Fragment.`,
    PROZESSIA_SYSTEM_PROMPT
  )).trim();

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

  const text = (await runClaudeCli(
    `Schreibe einen vollständigen LinkedIn Post für Prozessia.

IDEE:
Hook: ${idee.hook}
Format: Text-Post
Branche: ${idee.branche}
Content-Säule: ${idee.saeule}
${zusatzInfos ? `Zusätzliche Infos: ${zusatzInfos}` : ''}

ANFORDERUNGEN:
- Erste Zeile: vermittelt sofort und seriös, worum es geht (max 120 Zeichen) - vollständiger, klarer Satz oder eine präzise echte Frage, kein reißerisches Fragment, keine Statistik als allererster Satz.
- 3-5 Absätze mit echtem Mehrwert, klare vollständige Sätze statt abgehackter Häppchen, Absätze durch Leerzeile getrennt
- Mindestens eine konkrete Zahl. Beispiele mit erfundenem Firmennamen und als typisches Szenario gerahmt, nie als Prozessias eigene Situation oder als verifizierbares Kundenergebnis
- Eine Ergebnis-Zeile allein auf einer Zeile im Format **Ergebnis: ...**
- Abschlussfrage, die nur mit echter Berufserfahrung beantwortbar ist. Keine generische Zustimmungsfrage, keine "Kontaktiert uns"-Floskel
- 3-5 Hashtags, Mischung aus breit (#KI, #Mittelstand) und spezifisch (#Werkzeugbau, #Beschaffung, #Wissensmanagement)
- MAXIMALE LÄNGE: 1300 Zeichen
- Kein Link im Text - Links gehören in den ersten Kommentar
- Kein "innovativ", "revolutionär", "bahnbrechend", "Transformation", "ganzheitlich"

Antworte NUR mit validem JSON:
{
  "post": "Der vollständige Post-Text mit Zeilenumbrüchen als \\n",
  "kommentar": "Auto-Plug Kommentar (separat, 2-3 Zeilen, z.B. Link zu Calendly oder Website)"
}`,
    PROZESSIA_SYSTEM_PROMPT
  )).trim();

  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('Kein valides JSON vom Claude erhalten');

  const result = JSON.parse(jsonMatch[0]);
  console.log('[Claude] Post erfolgreich geschrieben, Länge:', result.post.length);
  return result;
}

/**
 * Generiert Karussell-Slides UND den Begleittext (Caption).
 *
 * Slide-Dramaturgie und Begleittext-Aufbau folgen Marketing/LinkedIn/
 * STRATEGIE.md (§4 und §6), abgeleitet aus dem Vorbild-Karussell von
 * Wolfgang Lang: Hook -> Problem -> Zahlen -> Vertiefung -> Konsequenz -> CTA.
 * Die Caption entsteht hier mit, statt sie im Backend aus Slide-Titeln
 * zusammenzusetzen - der zusammengesetzte Text erfüllte die Caption-Struktur
 * nie und wiederholte nur die Slides.
 *
 * **fett** markiert Kernbegriffe und Zahlen mitten im Satz; der Renderer
 * (backend/app/services/carousel_service.py) setzt sie in den fetten
 * Schriftschnitt, so wie im Vorbild.
 */
async function generiereKarussell(idee) {
  console.log('[Claude] Generiere Karussell für:', idee.hook);

  const text = (await runClaudeCli(
    `Erstelle ein LinkedIn-Dokument-Karussell (7 Slides) plus Begleittext für Prozessia.

IDEE:
Hook: ${idee.hook}
Branche: ${idee.branche}
Themen-Säule: ${idee.saeule}

SLIDE-DRAMATURGIE (genau diese Reihenfolge):
- Slide 1 (hook): Titel max 7 Wörter, Untertitel spitzt das Problem zu. text bleibt leer.
- Slide 2 (problem): Wie es heute im Betrieb tatsächlich läuft. Titel max 5 Wörter.
- Slide 3 (zahlen): Die Zahlen dahinter. 2-3 konkrete Zahlen, die zentrale Zahl **fett**.
- Slide 4-6 (vertiefung): je ein Aspekt - warum es passiert, was es kostet, was daran anders geht.
- Slide 7 (cta): Was der Leser jetzt konkret tun kann. Kein "Folgt uns für mehr".

REGELN FÜR SLIDE-TEXTE:
- Titel: max 5-7 Wörter, normale Groß-/Kleinschreibung, keine Versalien, seriös formuliert
  statt reißerisch zugespitzt.
- text: max 45 Wörter, klare vollständige Sätze (Kürze ergibt sich aus dem Platz auf der
  Slide, nicht aus erzwungener Fragment-Sprache).
- Pro Slide höchstens EINE **fett**-Markierung, nur für die Kernzahl oder den Kernbegriff.
- Absatzwechsel innerhalb von text mit \\n\\n.
- Mindestens zwei Slides nennen eine konkrete Zahl.
- Erfundene Firmennamen sind erlaubt, aber als typisches Szenario gerahmt.
- KEINE Bindestriche in Wortzusammensetzungen (Sebastian, 2026-08-17) - "Beschaffungs-Tools"
  wird zu "Beschaffungstools" oder "Tools für die Beschaffung", nicht als Kompositum mit
  Bindestrich getrennt. Gedankenstriche in normalen Sätzen (" - ") sind davon nicht betroffen.

BEGLEITTEXT (Feld "caption") - GENAU diese Reihenfolge, das ist die Post-Struktur:
1. Kurze Einleitung oder Frage, die das Problem umreißt (1-2 Zeilen)
2. 2-3 konkrete Zahlen oder Fakten
3. Eine Ergebnis-Zeile, allein auf einer Zeile, im Format: **Ergebnis: ...**
4. Optional ein Satz mit einem bekannten Fachsystem oder einer Norm (SAP, proALPHA, ERP, branchenübliche Normen) - nur wenn es inhaltlich trägt
5. Kurzer Einordnungs-Absatz, 2-3 Sätze
6. Abschlussfrage, die nur mit echter Berufserfahrung beantwortbar ist und die Aussage stützt. Keine generische Zustimmungsfrage.
7. 3-5 Hashtags, Mischung aus breit und spezifisch

CAPTION-FORMAT:
- Leerzeile zwischen den Blöcken, damit der Text auf LinkedIn luftig wirkt.
- Kein Link im Text.
- Maximal 1300 Zeichen.
- Nur die Ergebnis-Zeile wird mit **...** markiert, sonst keine Fett-Markierung in der Caption.
- KEINE Bindestriche in Wortzusammensetzungen (siehe Slide-Regeln oben) - gilt genauso für die Caption.

Antworte NUR mit validem JSON:
{
  "slides": [
    { "nummer": 1, "typ": "hook", "titel": "...", "untertitel": "...", "text": "" },
    { "nummer": 2, "typ": "problem", "titel": "...", "untertitel": "", "text": "..." },
    { "nummer": 3, "typ": "zahlen", "titel": "...", "untertitel": "...", "text": "..." },
    { "nummer": 4, "typ": "vertiefung", "titel": "...", "untertitel": "", "text": "..." },
    { "nummer": 5, "typ": "vertiefung", "titel": "...", "untertitel": "", "text": "..." },
    { "nummer": 6, "typ": "vertiefung", "titel": "...", "untertitel": "", "text": "..." },
    { "nummer": 7, "typ": "cta", "titel": "...", "untertitel": "", "text": "..." }
  ],
  "caption": "Der vollständige Begleittext mit Zeilenumbrüchen als \\n"
}`,
    PROZESSIA_SYSTEM_PROMPT,
    { maxBudgetUsd: 1.5, timeoutMs: 180000 }
  )).trim();

  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error('Kein valides JSON vom Claude erhalten');

  const result = JSON.parse(jsonMatch[0]);
  console.log(`[Claude] Karussell mit ${result.slides.length} Slides + Caption (${(result.caption || '').length} Zeichen) generiert`);
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

  const text = (await runClaudeCli(
    `Bewerte diese News-Artikel auf Relevanz für Prozessias Zielgruppe (Geschäftsführer und Einkaufsleiter in produzierenden Mittelständlern mit 20-80 Mitarbeitenden: Werkzeugbau, Lohnfertigung, Elektrotechnik, Kunststoff, Metallbau).

ARTIKEL:
${artikelListe}

Bewerte jeden Artikel mit einer Zahl von 1-10 (10 = höchste Relevanz für LinkedIn Content).
Relevant sind Themen entlang der vier Themen-Säulen: Wissensmanagement im Betrieb,
KI-Compliance und EU-KI-Verordnung, Einkauf und Beschaffung (Ausschreibung, Kalkulation,
Lieferantenmanagement, Long-Tail-Spend), KI-Nutzung im Mittelstand inklusive
Stücklisten-/BOM-Automatisierung. Studien mit konkreten Zahlen sind wertvoller als Meinungsstücke.
Artikel über Konzerne ohne Übertragbarkeit auf 20-80-Mitarbeiter-Betriebe sind kaum relevant.

Antworte NUR mit JSON:
[
  {"index": 0, "relevanz": 8, "begruendung": "Kurze Begründung"},
  ...
]`,
    PROZESSIA_SYSTEM_PROMPT,
    { maxBudgetUsd: 0.5 }
  )).trim();

  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) throw new Error('Kein valides JSON erhalten');

  const bewertungen = JSON.parse(jsonMatch[0]);
  console.log('[Claude] News-Bewertung abgeschlossen');
  return bewertungen;
}

module.exports = { generiereIdeen, schreibeTextPost, generiereKarussell, bewerteNewsArtikel, PROZESSIA_SYSTEM_PROMPT };
