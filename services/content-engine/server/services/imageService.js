// DALL-E 3 Bildgenerierung Service - Prozessia Content Engine
const OpenAI = require('openai');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Basis-Prompt für alle Karussell-Bilder (Prozessia Brand)
const BASE_IMAGE_PROMPT = `Professional B2B illustration for LinkedIn carousel, dark navy blue background (#0A0F1E), minimalist design, tech industry, supply chain and procurement theme, no text in image, clean geometric shapes, high quality professional look, abstract visualization, blue and orange accent colors`;

// Cache für bereits generierte Bilder (base64) - verhindert doppelte API-Calls
const bildCache = new Map();

/**
 * Generiert ein Bild für einen Karussell-Slide via DALL-E 3
 */
async function generiereKarussellBild(slideContext, slideNummer) {
  const cacheKey = `${slideNummer}_${slideContext.substring(0, 50)}`;

  // Cache prüfen - keine erneute Generierung wenn bereits vorhanden
  if (bildCache.has(cacheKey)) {
    console.log(`[DALL-E] Bild für Slide ${slideNummer} aus Cache geladen`);
    return bildCache.get(cacheKey);
  }

  console.log(`[DALL-E] Generiere Bild für Slide ${slideNummer}...`);

  const kontextPrompt = `${BASE_IMAGE_PROMPT}, themed around: ${slideContext}`;

  const response = await openai.images.generate({
    model: 'dall-e-3',
    prompt: kontextPrompt,
    n: 1,
    size: '1024x1024',
    response_format: 'b64_json',
    quality: 'standard',
    style: 'vivid',
  });

  const bildBase64 = response.data[0].b64_json;
  const bildUrl = `data:image/png;base64,${bildBase64}`;

  // In Cache speichern
  bildCache.set(cacheKey, bildUrl);
  console.log(`[DALL-E] Bild für Slide ${slideNummer} erfolgreich generiert`);

  return bildUrl;
}

/**
 * Generiert Bilder für alle Slides eines Karussells
 */
async function generiereAlleKarussellBilder(slides) {
  console.log(`[DALL-E] Starte Bildgenerierung für ${slides.length} Slides...`);

  const bildVersprechen = slides.map((slide, index) => {
    const kontext = `${slide.titel} ${slide.text || ''}`.trim();
    return generiereKarussellBild(kontext, index + 1)
      .catch(fehler => {
        // Fehler pro Slide abfangen - nicht den ganzen Prozess stoppen
        console.error(`[DALL-E] Fehler bei Slide ${index + 1}:`, fehler.message);
        return null; // Null zurückgeben bei Fehler
      });
  });

  const bilder = await Promise.all(bildVersprechen);
  console.log(`[DALL-E] ${bilder.filter(Boolean).length}/${slides.length} Bilder erfolgreich generiert`);

  return bilder;
}

/**
 * Cache leeren (z.B. bei Server-Neustart)
 */
function leereCache() {
  bildCache.clear();
  console.log('[DALL-E] Bild-Cache geleert');
}

module.exports = { generiereKarussellBild, generiereAlleKarussellBilder, leereCache };
