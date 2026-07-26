---
tags:
  - technisch
  - html
  - unklar
  - kein-kundenbezug
  - bundler
quelle: Aegis AI Core - Standalone.html
datum: 2026-07-26
kategorie: Memo
---

# Aegis AI Core - Standalone

## Zusammenfassung
HTML-Datei eines 'Bundled Page'-Templates (technischer JS-Bundler-Loader mit Manifest/Template-Mechanismus). Enthält keinen erkennbaren Geschäftsinhalt, nur generischen Boilerplate-Code zum Entpacken einer gebündelten Web-Anwendung namens 'Aegis AI Core'.

## Vollständiger Inhalt

 
 
   
   Bundled Page 
   
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #f2f2f3; display: flex; align-items: center; justify-content: center; min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    #__bundler_loading { position: fixed; bottom: 20px; right: 20px; font: 13px/1.4 -apple-system, BlinkMacSystemFont, sans-serif; color: #666; background: #fff; padding: 8px 14px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.12); z-index: 10000; }
    #__bundler_thumbnail { position: fixed; inset: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f2f2f3; z-index: 9999; }
    #__bundler_thumbnail svg { width: 100%; height: 100%; object-fit: contain; }
    #__bundler_placeholder { color: #999; font-size: 14px; }
   
   
     #__bundler_loading { display: none; } 
     
      This page requires JavaScript to display.
     
   
 
 
   
   
     
     
     A 
     
       
       
       
       
     
   
 
   Unpacking... 

   
    
document.addEventListener('DOMContentLoaded', async function() {
  const loading = document.getElementById('__bundler_loading');
  function setStatus(msg) { if (loading) loading.textContent = msg; }

  const FONT_MIME = /^(font[/]|application[/](x-)?font-|application[/]vnd\.ms-fontobject)/i;
  const MIME_TOKEN = /^[\w.+-]+[/][\w.+-]+$/;
  function toBase64(bytes) {
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(bin);
  }

  // Error sink persists across replaceWith since it's on window, not the DOM.
  window.addEventListener('error', function(e) {
    // Failed resource loads (CSP-blocked links, scripts, images) fire plain
    // events at the element — warn only; real JS errors carry message/error.
    if (!e.message && !e.error && e.target && e.target !== window) {
      console.warn('[bundle] resource failed to load:',
        e.target.tagName, String(e.target.src || e.target.href || ''));
      return;
    }
    var p = document.body || document.documentElement;
    var d = document.getElementById('__bundler_err') || p.appendChild(document.createElement('div'));
    d.id = '__bundler_err';
    d.style.cssText = 'position:fixed;bottom:12px;left:12px;right:12px;font:12px/1.4 ui-monospace,monospace;background:#2a1215;color:#ff8a80;padding:10px 14px;border-radius:8px;border:1px solid #5c2b2e;z-index:99999;white-space:pre-wrap;max-height:40vh;overflow:auto';
    d.textContent = (d.textContent ? d.textContent + String.fromCharCode(10) : '') +
      '[bundle] ' + (e.message || e.type) +
      (e.filename ? ' (' + e.filename.slice(0, 60) + ':' + e.lineno + ')' : '');
  }, true);

  try {
    const manifestEl = document.querySelector('script[type="__bundler/manifest"]');
    const templateEl = document.querySelector('script[type="__bundler/template"]');
    if (!manifestEl || !templat
