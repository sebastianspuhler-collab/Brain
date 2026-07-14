// Prozessia Content Engine - Server Entry Point
require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const path = require('path');

const apiRoutes = require('./routes/api');

const app = express();
const PORT = process.env.PORT || 3001;

// ---- Middleware ----
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000', 'http://localhost:5174'],
  credentials: true,
}));
app.use(express.json({ limit: '10mb' })); // Großes Limit für base64 Bilder
app.use(express.urlencoded({ extended: true }));

// Rate Limiting für Claude API Calls - max 5 Requests pro Minute
const claudeLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 Minute
  max: 5,
  message: { fehler: 'Zu viele KI-Anfragen. Bitte warte eine Minute.' },
  standardHeaders: true,
  legacyHeaders: false,
});

// Rate Limiting nur für KI-intensive Routen
app.use('/api/ideen/generieren', claudeLimiter);
app.use('/api/post/generieren', claudeLimiter);
app.use('/api/karussell/generieren', claudeLimiter);

// ---- API Routes ----
app.use('/api', apiRoutes);

// Health Check
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    name: 'Prozessia Content Engine',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    apis: {
      claude: !!process.env.ANTHROPIC_API_KEY,
      openai: !!process.env.OPENAI_API_KEY,
    },
  });
});

// ---- Fehler-Handler ----
app.use((err, req, res, next) => {
  console.error('[Server] Unbehandelter Fehler:', err.message);
  res.status(500).json({
    fehler: 'Ein unerwarteter Fehler ist aufgetreten.',
    details: process.env.NODE_ENV === 'development' ? err.message : undefined,
  });
});

// ---- Server starten ----
app.listen(PORT, () => {
  console.log('');
  console.log('╔══════════════════════════════════════╗');
  console.log('║   Prozessia Content Engine           ║');
  console.log('║   KI-gestützter LinkedIn Planer      ║');
  console.log('╚══════════════════════════════════════╝');
  console.log('');
  console.log(`[Server] Läuft auf http://localhost:${PORT}`);
  console.log(`[Server] Claude API: ${process.env.ANTHROPIC_API_KEY ? 'Konfiguriert' : 'FEHLT - .env prüfen!'}`);
  console.log(`[Server] OpenAI API: ${process.env.OPENAI_API_KEY ? 'Konfiguriert' : 'Nicht gesetzt (Bilder deaktiviert)'}`);
  console.log('');
});

module.exports = app;
