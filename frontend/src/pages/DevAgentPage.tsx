import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUp, ExternalLink, FileText, Loader2, Paperclip, Terminal, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { ApiError, chatAttach, chatSessions, streamDevAgentChat, type ChatAttachment, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

// Fester Host-Port-Bereich statt Subdomain (DNS ist auf dem VPS nicht
// wildcard, siehe Umsetzungsplan 2026-07-25) - der Sandbox-Container
// veröffentlicht 8100-8120 direkt auf die VPS-IP.
const VPS_HOST = "72.61.80.20";
const PORT_PATTERN = /\bPort\s+(\d{4,5})\b/i;

// Muss zu dev-agent/server.py::ALLOWED_MODELS passen (Umsetzungsplan 2026-07-26).
const MODELS = [
  { id: "claude-sonnet-5", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

const SUGGESTIONS = [
  { title: "Neues Projekt", prompt: "Lege ein neues kleines Vite-React-Projekt an und starte einen Dev-Server dafür." },
  { title: "Bestehendes Projekt fortsetzen", prompt: "Welche Projekte gibt es schon in /workspace? Gib mir eine kurze Übersicht." },
  { title: "Feature ergänzen", prompt: "Ergänze im zuletzt bearbeiteten Projekt eine neue Funktion: " },
  { title: "Nach GitHub pushen", prompt: "Committe die Änderungen im aktuellen Projekt und pushe sie nach GitHub." },
];

function previewLink(content: string): string | null {
  const match = content.match(PORT_PATTERN);
  return match ? `http://${VPS_HOST}:${match[1]}` : null;
}

export function DevAgentPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [loadingSession, setLoadingSession] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const attachInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Chat-Verlauf pro Agent (Umsetzungsplan 2026-07-26): Historie laden, sobald
  // eine Session in der URL steht - gleiches Muster wie ChatPage.tsx, nutzt
  // dieselbe chat_sessions.py-Persistenz über die reservierte DEV_AGENT_ID.
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingSession(true);
    chatSessions
      .get(sessionId)
      .then((data) => {
        if (cancelled) return;
        setMessages(data.messages ?? []);
        if (data.model) setModel(data.model);
      })
      .catch(() => {
        if (!cancelled) toast.error("Chat konnte nicht geladen werden");
      })
      .finally(() => {
        if (!cancelled) setLoadingSession(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  async function send(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || streaming) return;

    let activeSessionId = sessionId;
    if (!activeSessionId) {
      activeSessionId = crypto.randomUUID();
      setSearchParams({ session: activeSessionId }, { replace: true });
    }

    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: text, attachments: pendingAttachments.length ? pendingAttachments : undefined },
    ];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput("");
    setPendingAttachments([]);
    setStreaming(true);
    setError("");

    const controller = new AbortController();
    abortRef.current = controller;

    let assistantText = "";
    try {
      await streamDevAgentChat(
        nextMessages,
        model,
        (chunk) => {
          assistantText += chunk;
          setMessages([...nextMessages, { role: "assistant", content: assistantText }]);
        },
        controller.signal,
        activeSessionId
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError("Verbindung zum Entwickler-Agenten unterbrochen. Bitte erneut versuchen.");
      }
    } finally {
      setStreaming(false);
      window.dispatchEvent(new CustomEvent("brain:sessions-changed"));
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  // Datei-Anhang nur für diesen Turn (Umsetzungsplan 2026-07-27) - gleiches
  // Muster wie ChatPage.tsx: Text wird vorab extrahiert (POST /api/chat/attach)
  // und nur in den Prompt dieser einen Nachricht eingebettet, kein echter
  // Datei-Zugriff für den Agenten in /workspace.
  async function handleChatAttach(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || attaching) return;
    setAttaching(true);
    try {
      const result = await chatAttach.upload(file);
      setPendingAttachments((prev) => [...prev, result]);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Datei konnte nicht gelesen werden");
    } finally {
      setAttaching(false);
    }
  }

  function removeAttachment(filename: string) {
    setPendingAttachments((prev) => prev.filter((a) => a.filename !== filename));
  }

  const modelSelect = (
    <Select value={model} onValueChange={(value) => value && setModel(value)} disabled={streaming}>
      <SelectTrigger
        size="sm"
        className="h-7 w-auto gap-1 border-none bg-transparent px-2 text-xs text-muted-foreground shadow-none hover:bg-muted hover:text-foreground"
      >
        <SelectValue>{(value: string) => MODELS.find((m) => m.id === value)?.label ?? value}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {MODELS.map((m) => (
          <SelectItem key={m.id} value={m.id}>
            {m.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );

  const inputBar = (
    <div className="flex flex-col rounded-3xl border border-border bg-card/60 shadow-lg backdrop-blur-sm transition focus-within:border-ring/50">
      {pendingAttachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 pt-3">
          {pendingAttachments.map((a) => (
            <span
              key={a.filename}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs text-foreground"
            >
              <FileText className="size-3.5 shrink-0" />
              <span className="max-w-40 truncate">{a.filename}</span>
              <button
                type="button"
                onClick={() => removeAttachment(a.filename)}
                className="shrink-0 text-muted-foreground hover:text-destructive"
                title="Anhang entfernen"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Aufgabe für den Entwickler-Agenten…"
        rows={1}
        disabled={streaming}
        className="min-h-[48px] max-h-52 resize-none border-0 bg-transparent px-4 py-3.5 text-sm shadow-none focus-visible:ring-0"
      />
      <div className="flex items-center justify-between px-2 pb-2">
        <div className="flex items-center gap-1">
          {modelSelect}
          <input
            ref={attachInputRef}
            type="file"
            className="hidden"
            onChange={handleChatAttach}
            disabled={attaching}
          />
          <Button
            size="icon"
            variant="ghost"
            className="size-7 rounded-full text-muted-foreground hover:text-foreground"
            onClick={() => attachInputRef.current?.click()}
            disabled={attaching}
            title="Datei an diese Nachricht anhängen (nur für diese Anfrage)"
          >
            {attaching ? <Loader2 className="size-4 animate-spin" /> : <Paperclip className="size-4" />}
          </Button>
        </div>
        <Button size="icon" className="size-8 rounded-full" onClick={() => send()} disabled={streaming || !input.trim()}>
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </div>
  );

  if (loadingSession) {
    return (
      <div className="flex h-[calc(100vh-6.5rem)] w-full items-center justify-center text-sm text-muted-foreground">
        Chat wird geladen…
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="mx-auto flex h-[calc(100vh-6.5rem)] w-full max-w-2xl flex-col items-center justify-center gap-6 px-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex size-11 items-center justify-center rounded-full bg-accent">
            <Terminal className="size-5 text-accent-foreground" />
          </div>
          <h1 className="font-display text-3xl text-foreground">Entwicklung</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Läuft isoliert in einer eigenen Sandbox mit Zugriff auf einen eigenen{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">Prozessia-Dev</code>-Ordner - kein Zugriff auf den
            Vault oder andere Systeme.
          </p>
        </div>
        <div className="w-full">{inputBar}</div>
        <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.title}
              onClick={() => send(s.prompt)}
              className="rounded-xl border border-border px-3.5 py-2.5 text-left transition hover:bg-muted"
            >
              <div className="text-sm font-medium text-foreground">{s.title}</div>
              <div className="text-xs text-muted-foreground line-clamp-1">{s.prompt}</div>
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-6.5rem)] w-full max-w-3xl flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="flex flex-col gap-6 px-1 py-4">
          {messages.map((m, i) => {
            const isThinking = streaming && i === messages.length - 1 && !m.content;
            const link = m.role === "assistant" ? previewLink(m.content) : null;
            return m.role === "user" ? (
              <div key={i} className="flex flex-col items-end gap-1.5">
                {!!m.attachments?.length && (
                  <div className="flex max-w-[80%] flex-wrap justify-end gap-1.5">
                    {m.attachments.map((a) => (
                      <span
                        key={a.filename}
                        className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground"
                      >
                        <FileText className="size-3 shrink-0" />
                        <span className="max-w-32 truncate">{a.filename}</span>
                      </span>
                    ))}
                  </div>
                )}
                <div className="max-w-[80%] rounded-3xl rounded-br-md bg-muted px-4 py-2 text-sm text-foreground">
                  {m.content}
                </div>
              </div>
            ) : (
              <div key={i} className="flex gap-3">
                <div className="relative flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                  {isThinking && (
                    <>
                      <span className="absolute inset-0 rounded-full border border-primary animate-[brain-pulse_1.6s_ease-out_infinite]" />
                      <span
                        className="absolute inset-0 rounded-full border border-primary animate-[brain-pulse_1.6s_ease-out_infinite]"
                        style={{ animationDelay: "0.8s" }}
                      />
                    </>
                  )}
                  <Terminal className="relative size-3.5" />
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Entwickler-Agent</div>
                  {!isThinking && (
                    <div className="prose prose-invert prose-sm max-w-none text-foreground">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  )}
                  {link && (
                    <a
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-primary/30 px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                    >
                      <ExternalLink className="size-3" />
                      Vorschau öffnen ({link.replace("http://", "")})
                    </a>
                  )}
                </div>
              </div>
            );
          })}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="sticky bottom-0 bg-background pt-2 pb-1">{inputBar}</div>
    </div>
  );
}
