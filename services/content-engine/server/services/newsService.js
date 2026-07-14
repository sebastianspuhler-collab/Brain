// RSS News Scanner Service - Prozessia Content Engine
const Parser = require('rss-parser');

const parser = new Parser({
  timeout: 10000, // 10 Sekunden Timeout
  customFields: {
    item: ['media:content', 'enclosure'],
  },
});

// RSS Feeds für Prozessia-relevante Branchen
const RSS_FEEDS = [
  {
    url: 'https://www.beschaffung-aktuell.de/feed/',
    name: 'Beschaffung Aktuell',
    branche: 'Beschaffung',
  },
  {
    url: 'https://www.automobil-industrie.vogel.de/rss/news.xml',
    name: 'Automobil Industrie',
    branche: 'Automotive',
  },
  {
    url: 'https://www.pharmazeutische-zeitung.de/feed/',
    name: 'Pharmazeutische Zeitung',
    branche: 'Pharma',
  },
  {
    url: 'https://www.springerprofessional.de/feed/rss',
    name: 'Springer Professional',
    branche: 'Allgemein',
  },
];

// Fallback-Artikel wenn kein Feed erreichbar
const FALLBACK_ARTIKEL = [
  {
    title: 'Lieferkettenprobleme im Automotive-Sektor nehmen zu',
    source: 'Prozessia Research',
    branche: 'Automotive',
    contentSnippet: 'Tier-1 und Tier-2 Zulieferer berichten von steigendem Druck durch verspätete Lieferungen aus Asien.',
    link: 'https://www.prozessia.de',
    pubDate: new Date().toISOString(),
    isFallback: true,
  },
  {
    title: 'ERP-Integration: Mittelstand kämpft mit veralteten Systemen',
    source: 'Prozessia Research',
    branche: 'Alle',
    contentSnippet: 'Viele Unternehmen nutzen Excel parallel zum ERP-System - ein teurer Fehler.',
    link: 'https://www.prozessia.de',
    pubDate: new Date().toISOString(),
    isFallback: true,
  },
  {
    title: 'OTIF-Quoten unter Druck: Pharma-Branche reagiert',
    source: 'Prozessia Research',
    branche: 'Pharma',
    contentSnippet: 'On-Time-In-Full Anforderungen steigen weiter - manuelle Prozesse reichen nicht mehr.',
    link: 'https://www.prozessia.de',
    pubDate: new Date().toISOString(),
    isFallback: true,
  },
];

/**
 * Liest einen einzelnen RSS-Feed aus
 */
async function leseFeed(feedConfig) {
  try {
    console.log(`[News] Lese Feed: ${feedConfig.name}...`);
    const feed = await parser.parseURL(feedConfig.url);

    const artikel = feed.items.slice(0, 5).map(item => ({
      title: item.title || 'Kein Titel',
      source: feedConfig.name,
      branche: feedConfig.branche,
      contentSnippet: item.contentSnippet || item.summary || '',
      link: item.link || '',
      pubDate: item.pubDate || new Date().toISOString(),
      relevanz: 0, // Wird später von Claude bewertet
      isFallback: false,
    }));

    console.log(`[News] ${artikel.length} Artikel von ${feedConfig.name} geladen`);
    return artikel;
  } catch (fehler) {
    // Graceful fallback - Feed-Fehler nicht den ganzen Prozess stoppen lassen
    console.warn(`[News] Feed ${feedConfig.name} nicht erreichbar: ${fehler.message}`);
    return [];
  }
}

/**
 * Scannt alle RSS Feeds und gibt Artikel zurück
 */
async function scanneAlleFeeds() {
  console.log('[News] Starte RSS Feed-Scan...');

  const feedVersprechen = RSS_FEEDS.map(feed => leseFeed(feed));
  const alleArtikel = await Promise.all(feedVersprechen);

  // Alle Artikel zusammenführen
  const flacheArtikel = alleArtikel.flat();

  if (flacheArtikel.length === 0) {
    // Fallback wenn kein Feed erreichbar
    console.warn('[News] Keine Feeds erreichbar - nutze Fallback-Artikel');
    return FALLBACK_ARTIKEL;
  }

  // Duplikate nach Titel entfernen
  const eindeutigeArtikel = flacheArtikel.reduce((acc, artikel) => {
    const exists = acc.some(a => a.title === artikel.title);
    if (!exists) acc.push(artikel);
    return acc;
  }, []);

  console.log(`[News] ${eindeutigeArtikel.length} eindeutige Artikel gefunden`);
  return eindeutigeArtikel;
}

/**
 * Gibt die Top N Artikel nach Relevanz zurück
 */
function filtereTopArtikel(artikel, bewertungen, anzahl = 5) {
  // Bewertungen den Artikeln zuordnen
  const bewertet = artikel.map((artikel, index) => {
    const bewertung = bewertungen.find(b => b.index === index);
    return {
      ...artikel,
      relevanz: bewertung ? bewertung.relevanz : 0,
      begruendung: bewertung ? bewertung.begruendung : '',
    };
  });

  // Nach Relevanz sortieren und Top N zurückgeben
  return bewertet
    .sort((a, b) => b.relevanz - a.relevanz)
    .slice(0, anzahl);
}

module.exports = { scanneAlleFeeds, filtereTopArtikel, FALLBACK_ARTIKEL };
