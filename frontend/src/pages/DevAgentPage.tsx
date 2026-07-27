import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { RotateCcw, Terminal as TerminalIcon, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

// Muss zu dev-agent/server.py::ALLOWED_MODELS/ALLOWED_EFFORTS passen
// (Umsetzungsplan 2026-07-27).
const MODELS = [
  { id: "claude-sonnet-5", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];
const EFFORTS = [
  { id: "", label: "Standard" },
  { id: "low", label: "Low" },
  { id: "medium", label: "Medium" },
  { id: "high", label: "High" },
  { id: "xhigh", label: "XHigh" },
  { id: "max", label: "Max" },
];

function wsUrl(sessionId: string, model: string, effort: string): string {
  const base = API_BASE || `${location.protocol}//${location.host}`;
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/api/ws/dev-agent/${sessionId}?model=${encodeURIComponent(model)}&effort=${encodeURIComponent(effort)}`;
}

// Entwicklungs-Agent als echtes interaktives Claude-Code-Terminal
// (Umsetzungsplan 2026-07-27) - ersetzt die bisherige Chat-Bubble-Simulation
// (jeder Turn ein frischer Headless-Prozess, Tool-Aufrufe unsichtbar) durch
// einen dauerhaften, an ein PTY gebundenen `claude`-Prozess pro Sitzung, per
// WebSocket 1:1 mit xterm.js verbunden. Modellwechsel/Effort/weitere Befehle
// laufen ab Verbindungsaufbau über die echten Slash-Commands der CLI selbst
// (/model, /effort, /clear, /compact, ...) - keine eigene UI dafür nötig.
export function DevAgentPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");

  const [phase, setPhase] = useState<"config" | "terminal">(sessionId ? "terminal" : "config");
  const [model, setModel] = useState(MODELS[0].id);
  const [effort, setEffort] = useState("");
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [uploading, setUploading] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  function startTerminal() {
    const id = sessionId ?? crypto.randomUUID();
    if (!sessionId) setSearchParams({ session: id }, { replace: true });
    setConnectionError("");
    setPhase("terminal");
  }

  function restartTerminal() {
    setSearchParams({ session: crypto.randomUUID() }, { replace: true });
    setPhase("config");
    setConnected(false);
  }

  useEffect(() => {
    if (phase !== "terminal" || !sessionId || !containerRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: "var(--font-mono), ui-monospace, monospace",
      theme: { background: "#0d0d0d", foreground: "#e5e5e5" },
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    const ws = new WebSocket(wsUrl(sessionId, model, effort));
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    function sendResize() {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
      }
    }

    ws.onopen = () => {
      setConnected(true);
      setConnectionError("");
      sendResize();
      term.focus();
    };
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "error") {
            setConnectionError(msg.message);
            term.write(`\r\n\x1b[31m${msg.message}\x1b[0m\r\n`);
          }
        } catch {
          term.write(event.data);
        }
      } else {
        term.write(new Uint8Array(event.data));
      }
    };
    ws.onclose = () => {
      setConnected(false);
      term.write("\r\n\x1b[90m[Verbindung getrennt]\x1b[0m\r\n");
    };
    ws.onerror = () => {
      setConnectionError("Verbindung zum Entwickler-Agenten fehlgeschlagen.");
    };

    const dataDisposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }));
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
      sendResize();
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      dataDisposable.dispose();
      ws.close();
      term.dispose();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, sessionId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || uploading) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/dev-agent/upload`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      toast.success(`„${result.filename}" liegt jetzt in /workspace`);
    } catch {
      toast.error("Datei-Upload fehlgeschlagen");
    } finally {
      setUploading(false);
    }
  }

  if (phase === "config") {
    return (
      <div className="mx-auto flex h-[calc(100vh-6.5rem)] w-full max-w-md flex-col items-center justify-center gap-6 px-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex size-11 items-center justify-center rounded-full bg-accent">
            <TerminalIcon className="size-5 text-accent-foreground" />
          </div>
          <h1 className="font-display text-3xl text-foreground">Entwicklung</h1>
          <p className="max-w-sm text-sm text-muted-foreground">
            Startet ein echtes, interaktives Claude-Code-Terminal in einer isolierten Sandbox mit Zugriff auf einen
            eigenen <code className="rounded bg-muted px-1 py-0.5 text-xs">Prozessia-Dev</code>-Ordner - kein Zugriff
            auf den Vault oder andere Systeme. Modell und Denk-Aufwand lassen sich danach jederzeit direkt im
            Terminal mit <code className="rounded bg-muted px-1 py-0.5 text-xs">/model</code>/
            <code className="rounded bg-muted px-1 py-0.5 text-xs">/effort</code> ändern.
          </p>
        </div>
        <div className="flex w-full flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">Modell</span>
            <Select value={model} onValueChange={(v) => v && setModel(v)}>
              <SelectTrigger className="w-40">
                <SelectValue>{(v: string) => MODELS.find((m) => m.id === v)?.label ?? v}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {MODELS.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">Denk-Aufwand</span>
            <Select value={effort} onValueChange={(v) => v !== null && setEffort(v)}>
              <SelectTrigger className="w-40">
                <SelectValue>{(v: string) => EFFORTS.find((e) => e.id === v)?.label ?? "Standard"}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {EFFORTS.map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button className="w-full" onClick={startTerminal}>
          Terminal starten
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-6.5rem)] w-full max-w-5xl flex-col gap-2">
      <div className="flex items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <span
            className={cn("size-2 rounded-full", connected ? "bg-emerald-500" : "bg-muted-foreground/40")}
            title={connected ? "Verbunden" : "Nicht verbunden"}
          />
          <span className="text-sm font-medium text-foreground">Entwicklung</span>
          {connectionError && <span className="text-xs text-destructive">{connectionError}</span>}
        </div>
        <div className="flex items-center gap-1">
          <input ref={uploadInputRef} type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
          <Button
            size="sm"
            variant="outline"
            onClick={() => uploadInputRef.current?.click()}
            disabled={uploading}
            title="Datei in /workspace legen"
          >
            <Upload className="size-3.5" />
            {uploading ? "Lädt…" : "Datei hochladen"}
          </Button>
          <Button size="sm" variant="ghost" onClick={restartTerminal} title="Neue Sitzung starten">
            <RotateCcw className="size-3.5" />
            Neu
          </Button>
        </div>
      </div>
      <div ref={containerRef} className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-border bg-[#0d0d0d] p-2" />
    </div>
  );
}
