// JSON Storage Service - Prozessia Content Engine
const fs = require('fs').promises;
const path = require('path');

const DATA_DIR = path.join(__dirname, '../data');

const DATEIEN = {
  posts: path.join(DATA_DIR, 'posts.json'),
  kalender: path.join(DATA_DIR, 'kalender.json'),
  ideen: path.join(DATA_DIR, 'ideen.json'),
};

/**
 * Liest eine JSON-Datei aus
 */
async function leseDatei(dateipfad, standard = []) {
  try {
    const inhalt = await fs.readFile(dateipfad, 'utf-8');
    return JSON.parse(inhalt);
  } catch (fehler) {
    // Datei existiert nicht oder ist leer - Standard zurückgeben
    console.log(`[Storage] ${dateipfad} nicht gefunden, nutze Standard`);
    return standard;
  }
}

/**
 * Schreibt Daten in eine JSON-Datei
 */
async function schreibeDatei(dateipfad, daten) {
  await fs.writeFile(dateipfad, JSON.stringify(daten, null, 2), 'utf-8');
}

// ---- POSTS ----

async function allePosts() {
  return leseDatei(DATEIEN.posts, []);
}

async function speicherePost(post) {
  const posts = await allePosts();
  const index = posts.findIndex(p => p.id === post.id);

  if (index >= 0) {
    // Post aktualisieren
    posts[index] = { ...posts[index], ...post, aktualisiertAm: new Date().toISOString() };
  } else {
    // Neuer Post
    posts.unshift({ ...post, erstelltAm: new Date().toISOString(), aktualisiertAm: new Date().toISOString() });
  }

  await schreibeDatei(DATEIEN.posts, posts);
  console.log(`[Storage] Post ${post.id} gespeichert`);
  return posts.find(p => p.id === post.id);
}

async function loeschePost(id) {
  const posts = await allePosts();
  const gefiltert = posts.filter(p => p.id !== id);
  await schreibeDatei(DATEIEN.posts, gefiltert);
  console.log(`[Storage] Post ${id} gelöscht`);
}

async function aktualisierePostStatus(id, status) {
  const posts = await allePosts();
  const index = posts.findIndex(p => p.id === id);
  if (index >= 0) {
    posts[index].status = status;
    posts[index].aktualisiertAm = new Date().toISOString();
    await schreibeDatei(DATEIEN.posts, posts);
  }
}

// ---- KALENDER ----

async function kalenderDaten() {
  return leseDatei(DATEIEN.kalender, {});
}

async function speichereKalenderEintrag(datum, postId) {
  const kalender = await kalenderDaten();
  if (!kalender[datum]) kalender[datum] = [];
  if (!kalender[datum].includes(postId)) {
    kalender[datum].push(postId);
  }
  await schreibeDatei(DATEIEN.kalender, kalender);
  console.log(`[Storage] Kalender-Eintrag für ${datum} gespeichert`);
}

async function entferneKalenderEintrag(datum, postId) {
  const kalender = await kalenderDaten();
  if (kalender[datum]) {
    kalender[datum] = kalender[datum].filter(id => id !== postId);
    if (kalender[datum].length === 0) delete kalender[datum];
  }
  await schreibeDatei(DATEIEN.kalender, kalender);
}

// ---- IDEEN ----

async function alleIdeen() {
  return leseDatei(DATEIEN.ideen, []);
}

async function speichereIdeen(ideen) {
  await schreibeDatei(DATEIEN.ideen, ideen);
  console.log(`[Storage] ${ideen.length} Ideen gespeichert`);
}

module.exports = {
  allePosts, speicherePost, loeschePost, aktualisierePostStatus,
  kalenderDaten, speichereKalenderEintrag, entferneKalenderEintrag,
  alleIdeen, speichereIdeen,
};
