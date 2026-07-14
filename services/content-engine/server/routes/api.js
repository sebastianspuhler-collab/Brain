// API Routes - Prozessia Content Engine
const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

const claudeService = require('../services/claudeService');
const imageService = require('../services/imageService');
const newsService = require('../services/newsService');
const storage = require('../services/storageService');

// ============================================================
// NEWS SCANNER
// ============================================================

/**
 * GET /api/news - RSS Feeds scannen und bewerten
 */
router.get('/news', async (req, res) => {
  try {
    console.log('[API] News-Scan gestartet');

    // RSS Feeds parallel scannen
    const artikel = await newsService.scanneAlleFeeds();

    if (artikel.length === 0) {
      return res.json({ artikel: newsService.FALLBACK_ARTIKEL, quelle: 'fallback' });
    }

    // Claude bewertet die Artikel auf Relevanz (max erste 15 für Kosteneffizienz)
    const zuBewertende = artikel.slice(0, 15);
    let bewertungen = [];

    try {
      bewertungen = await claudeService.bewerteNewsArtikel(zuBewertende);
    } catch (err) {
      console.warn('[API] Claude-Bewertung fehlgeschlagen, nutze unbewertet:', err.message);
      // Fallback: Alle Artikel mit Relevanz 5
      bewertungen = zuBewertende.map((_, i) => ({ index: i, relevanz: 5, begruendung: 'Bewertung nicht verfügbar' }));
    }

    const topArtikel = newsService.filtereTopArtikel(zuBewertende, bewertungen, 5);

    console.log(`[API] News-Scan abgeschlossen: ${topArtikel.length} Top-Artikel`);
    res.json({ artikel: topArtikel, gesamt: artikel.length });
  } catch (fehler) {
    console.error('[API] Fehler beim News-Scan:', fehler.message);
    res.status(500).json({ fehler: 'News konnten nicht geladen werden. Bitte versuche es erneut.' });
  }
});

// ============================================================
// IDEEN GENERATOR
// ============================================================

/**
 * POST /api/ideen/generieren - 5 neue Ideen generieren
 */
router.post('/ideen/generieren', async (req, res) => {
  try {
    console.log('[API] Starte Ideen-Generierung');
    const { newsArtikel = [] } = req.body;

    const ideen = await claudeService.generiereIdeen(newsArtikel);

    // Ideen mit IDs versehen und speichern
    const ideenMitId = ideen.map(idee => ({
      ...idee,
      id: uuidv4(),
      erstelltAm: new Date().toISOString(),
    }));

    await storage.speichereIdeen(ideenMitId);

    console.log(`[API] ${ideenMitId.length} Ideen generiert und gespeichert`);
    res.json({ ideen: ideenMitId });
  } catch (fehler) {
    console.error('[API] Fehler bei Ideen-Generierung:', fehler.message);
    res.status(500).json({ fehler: 'Ideen konnten nicht generiert werden. Prüfe den API-Key.' });
  }
});

/**
 * GET /api/ideen - Gespeicherte Ideen abrufen
 */
router.get('/ideen', async (req, res) => {
  try {
    const ideen = await storage.alleIdeen();
    res.json({ ideen });
  } catch (fehler) {
    console.error('[API] Fehler beim Laden der Ideen:', fehler.message);
    res.status(500).json({ fehler: 'Ideen konnten nicht geladen werden.' });
  }
});

// ============================================================
// POST GENERATOR
// ============================================================

/**
 * POST /api/post/generieren - LinkedIn Text-Post schreiben
 */
router.post('/post/generieren', async (req, res) => {
  try {
    const { idee, zusatzInfos = '' } = req.body;

    if (!idee) {
      return res.status(400).json({ fehler: 'Keine Idee übergeben.' });
    }

    console.log('[API] Generiere Post für:', idee.hook);
    const result = await claudeService.schreibeTextPost(idee, zusatzInfos);

    // Post speichern
    const post = {
      id: uuidv4(),
      ideeId: idee.id,
      hook: idee.hook,
      format: 'TEXT',
      branche: idee.branche,
      saeule: idee.saeule,
      text: result.post,
      kommentar: result.kommentar,
      status: 'Entwurf',
    };

    const gespeicherterPost = await storage.speicherePost(post);
    console.log('[API] Post gespeichert mit ID:', post.id);
    res.json({ post: gespeicherterPost });
  } catch (fehler) {
    console.error('[API] Fehler bei Post-Generierung:', fehler.message);
    res.status(500).json({ fehler: 'Post konnte nicht generiert werden. Prüfe den API-Key.' });
  }
});

// ============================================================
// KARUSSELL GENERATOR
// ============================================================

/**
 * POST /api/karussell/generieren - Karussell generieren (Text + Bilder)
 */
router.post('/karussell/generieren', async (req, res) => {
  try {
    const { idee } = req.body;

    if (!idee) {
      return res.status(400).json({ fehler: 'Keine Idee übergeben.' });
    }

    console.log('[API] Generiere Karussell für:', idee.hook);

    // Karussell-Slides von Claude generieren
    const karussellDaten = await claudeService.generiereKarussell(idee);

    // Bilder für jeden Slide generieren (wenn OpenAI Key vorhanden)
    let bilder = [];
    if (process.env.OPENAI_API_KEY && process.env.OPENAI_API_KEY !== 'sk-...') {
      try {
        bilder = await imageService.generiereAlleKarussellBilder(karussellDaten.slides);
      } catch (bildFehler) {
        console.warn('[API] Bildgenerierung fehlgeschlagen:', bildFehler.message);
        bilder = new Array(karussellDaten.slides.length).fill(null);
      }
    } else {
      console.log('[API] Kein OpenAI Key - überspringe Bildgenerierung');
      bilder = new Array(karussellDaten.slides.length).fill(null);
    }

    // Slides mit Bildern kombinieren
    const slidesWithBilder = karussellDaten.slides.map((slide, i) => ({
      ...slide,
      bild: bilder[i] || null,
    }));

    // Karussell als Post speichern
    const post = {
      id: uuidv4(),
      ideeId: idee.id,
      hook: idee.hook,
      format: 'KARUSSELL',
      branche: idee.branche,
      saeule: idee.saeule,
      slides: slidesWithBilder,
      status: 'Entwurf',
    };

    const gespeicherterPost = await storage.speicherePost(post);
    console.log('[API] Karussell gespeichert mit ID:', post.id);
    res.json({ post: gespeicherterPost });
  } catch (fehler) {
    console.error('[API] Fehler bei Karussell-Generierung:', fehler.message);
    res.status(500).json({ fehler: 'Karussell konnte nicht generiert werden.' });
  }
});

// ============================================================
// POSTS / BIBLIOTHEK
// ============================================================

/**
 * GET /api/posts - Alle Posts abrufen
 */
router.get('/posts', async (req, res) => {
  try {
    const { format, saeule, branche, status, suche } = req.query;
    let posts = await storage.allePosts();

    // Filter anwenden
    if (format) posts = posts.filter(p => p.format === format);
    if (saeule) posts = posts.filter(p => p.saeule === saeule);
    if (branche) posts = posts.filter(p => p.branche === branche);
    if (status) posts = posts.filter(p => p.status === status);
    if (suche) {
      const suchBegriff = suche.toLowerCase();
      posts = posts.filter(p =>
        (p.hook && p.hook.toLowerCase().includes(suchBegriff)) ||
        (p.text && p.text.toLowerCase().includes(suchBegriff))
      );
    }

    res.json({ posts });
  } catch (fehler) {
    console.error('[API] Fehler beim Laden der Posts:', fehler.message);
    res.status(500).json({ fehler: 'Posts konnten nicht geladen werden.' });
  }
});

/**
 * PUT /api/posts/:id - Post aktualisieren
 */
router.put('/posts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const aktualisierung = req.body;
    const post = { ...aktualisierung, id };
    const gespeichert = await storage.speicherePost(post);
    res.json({ post: gespeichert });
  } catch (fehler) {
    console.error('[API] Fehler beim Aktualisieren:', fehler.message);
    res.status(500).json({ fehler: 'Post konnte nicht aktualisiert werden.' });
  }
});

/**
 * PATCH /api/posts/:id/status - Status ändern
 */
router.patch('/posts/:id/status', async (req, res) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    await storage.aktualisierePostStatus(id, status);
    res.json({ erfolg: true });
  } catch (fehler) {
    console.error('[API] Fehler beim Status-Update:', fehler.message);
    res.status(500).json({ fehler: 'Status konnte nicht geändert werden.' });
  }
});

/**
 * DELETE /api/posts/:id - Post löschen
 */
router.delete('/posts/:id', async (req, res) => {
  try {
    const { id } = req.params;
    await storage.loeschePost(id);
    console.log(`[API] Post ${id} gelöscht`);
    res.json({ erfolg: true });
  } catch (fehler) {
    console.error('[API] Fehler beim Löschen:', fehler.message);
    res.status(500).json({ fehler: 'Post konnte nicht gelöscht werden.' });
  }
});

// ============================================================
// CONTENT KALENDER
// ============================================================

/**
 * GET /api/kalender - Kalender-Daten abrufen
 */
router.get('/kalender', async (req, res) => {
  try {
    const kalender = await storage.kalenderDaten();
    const posts = await storage.allePosts();

    // Kalender mit Post-Details anreichern
    const angereichert = {};
    for (const [datum, postIds] of Object.entries(kalender)) {
      angereichert[datum] = postIds.map(id => posts.find(p => p.id === id)).filter(Boolean);
    }

    res.json({ kalender: angereichert });
  } catch (fehler) {
    console.error('[API] Fehler beim Laden des Kalenders:', fehler.message);
    res.status(500).json({ fehler: 'Kalender konnte nicht geladen werden.' });
  }
});

/**
 * POST /api/kalender - Post auf Datum setzen
 */
router.post('/kalender', async (req, res) => {
  try {
    const { datum, postId } = req.body;
    await storage.speichereKalenderEintrag(datum, postId);
    res.json({ erfolg: true });
  } catch (fehler) {
    console.error('[API] Fehler beim Kalender-Eintrag:', fehler.message);
    res.status(500).json({ fehler: 'Kalender-Eintrag konnte nicht gespeichert werden.' });
  }
});

/**
 * DELETE /api/kalender - Post von Datum entfernen
 */
router.delete('/kalender', async (req, res) => {
  try {
    const { datum, postId } = req.body;
    await storage.entferneKalenderEintrag(datum, postId);
    res.json({ erfolg: true });
  } catch (fehler) {
    console.error('[API] Fehler beim Entfernen aus Kalender:', fehler.message);
    res.status(500).json({ fehler: 'Eintrag konnte nicht entfernt werden.' });
  }
});

module.exports = router;
