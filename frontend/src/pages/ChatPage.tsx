import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUp, BookPlus, Bot, BrainCircuit, FileText, Loader2, Paperclip, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
// GitHub-Flavored Markdown (2026-07-27): ohne dieses Plugin rendert react-markdown
// nur CommonMark - Tabellen kamen als rohe Pipe-Zeilen durch, ebenso Durchstreichen
// und Aufgabenlisten. Brain antwortet aber regelmäßig in Tabellenform.
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import {
  agents as agentsApi,
  api,
  ApiError,
  chatAttach,
  chatSessions,
  streamChat,
  type Agent,
  type ChatAttachment,
  type ChatMessage,
  type ChatSource,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

// UI-seitige Erweiterung von ChatMessage um Quellenangaben (Umsetzungsplan-Memo
// 2026-07-16, Punkt D1) - rein für die Anzeige, wird nicht ans Backend gesendet
// (extra Felder werden dort ignoriert, aber wir senden ohnehin nur role/content).
type UiMessage = ChatMessage & { sources?: ChatSource[] };

const MODELS = [
  { id: "claude-sonnet-5", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

interface UploadResult {
  filename: string;
  processed: number;
  errors: number;
  output: string;
  new_indexed: number;
}

const SUGGESTIONS = [
  { title: "Offene Aufgaben", prompt: "Was steht diese Woche an?" },
  { title: "Mails zusammenfassen", prompt: "Fasse die neuesten E-Mails zusammen." },
  { title: "Kundenstatus", prompt: "Wie ist der aktuelle Stand bei Schaufler?" },
  { title: "Neues Memo", prompt: "Erstelle ein Memo zum heutigen Gespräch." },
];

export function ChatPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session");
  const agentFromUrl = searchParams.get("agent");

  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<ChatAttachment[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [agentsList, setAgentsList] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Eigene benannte Agenten (Umsetzungsplan-Memo 2026-07-16, Punkt D2) - rein
  // optional wählbar, "Standard" (kein Agent) verhält sich exakt wie bisher.
  useEffect(() => {
    agentsApi.list().then(setAgentsList).catch(() => {});
  }, []);

  const activeAgent = agentsList.find((a) => a.id === agentId) ?? null;
  useEffect(() => {
    if (activeAgent?.model) setModel(activeAgent.model);
  }, [activeAgent]);

  // Chat-Historie laden, sobald eine Session in der URL steht (?session=<id>) -
  // z.B. nach Klick in der Verlauf-Liste in der Sidebar oder nach einem Reload.
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
        // Eigener Chat pro Agent (Umsetzungsplan 2026-07-25): die Session-Datei
        // ist maßgeblich, sobald sie existiert. Der URL-Parameter greift nur
        // beim allerersten Besuch einer frisch erzeugten, noch leeren Session
        // (nach Klick auf "Chat öffnen" bei einem Agenten ohne Verlauf).
        if (data.agent_id) setAgentId(data.agent_id);
        else if (agentFromUrl) setAgentId(agentFromUrl);
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
  }, [sessionId, agentFromUrl]);

  async function send(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || streaming) return;

    // Erste Nachricht eines neuen Chats -> Session-ID erzeugen und in der URL
    // hinterlegen, damit ein Reload denselben Chat wieder findet.
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
    let assistantSources: ChatSource[] = [];
    try {
      await streamChat(
        nextMessages,
        model,
        (chunk) => {
          assistantText += chunk;
          setMessages([...nextMessages, { role: "assistant", content: assistantText, sources: assistantSources }]);
        },
        controller.signal,
        activeSessionId,
        (sources) => {
          assistantSources = sources;
          setMessages([...nextMessages, { role: "assistant", content: assistantText, sources: assistantSources }]);
        },
        agentId || undefined
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError("Verbindung unterbrochen. Bitte erneut versuchen.");
      }
    } finally {
      setStreaming(false);
      // Sidebar-Verlauf über den neuen/aktualisierten Chat informieren (die Session
      // wird serverseitig asynchron gespeichert, siehe chat.py:_stream_chat).
      window.dispatchEvent(new CustomEvent("brain:sessions-changed"));
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || uploading) return;
    setUploading(true);
    try {
      const result = await api.upload<UploadResult>("/api/upload", file);
      toast.success(`„${result.filename}" verarbeitet und im Wissen abgelegt`);
    } catch {
      toast.error("Datei-Upload fehlgeschlagen");
    } finally {
      setUploading(false);
    }
  }

  // Datei-Anhang für die nächste Nachricht (Umsetzungsplan 2026-07-27): Text
  // landet direkt im Prompt dieses einen Turns (siehe chat.py::_format_attachments).
  // Seit 2026-07-28 ("jede Uploadfläche im System ist eine Inbox") landet die
  // Datei ZUSÄTZLICH in der Inbox (result.persisted) - Einsortierung passiert
  // asynchron im Hintergrund (Inbox-Watcher, ~30s), nicht mehr synchron in
  // diesem Request (hat das Anhängen sonst spürbar verlangsamt). Deshalb kein
  // "als Transkript erkannt"-Toast mehr - die endgültige Einordnung steht bei
  // der Antwort hier noch gar nicht fest.
  async function handleChatAttach(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || attaching) return;
    setAttaching(true);
    try {
      const result = await chatAttach.upload(file);
      setPendingAttachments((prev) => [...prev, result]);
      if (result.persisted) {
        toast.success(`„${result.filename}" wird ins Wissen übernommen`);
      }
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
    <Select value={model} onValueChange={(value) => value && setModel(value)} disabled={streaming || !!activeAgent?.model}>
      <SelectTrigger
        size="sm"
        className="h-7 w-auto gap-1 border-none bg-transparent px-2 text-xs text-muted-foreground shadow-none hover:bg-muted hover:text-foreground"
      >
        <SelectValue>
          {(value: string) =>
            MODELS.find((m) => m.id === value)?.label ??
            // Einfache Anfragen werden serverseitig automatisch an Haiku umgeleitet
            // (siehe chat.py HAIKU_MODEL) - hier nur hübsch anzeigen, kein eigener
            // Menüpunkt, weil die Weiterleitung automatisch passiert.
            (value === "claude-haiku-4-5-20251001" ? "Haiku (automatisch)" : value)
          }
        </SelectValue>
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

  const agentSelect = agentsList.length > 0 && (
    <Select value={agentId || "standard"} onValueChange={(v) => v && setAgentId(v === "standard" ? "" : v)} disabled={streaming}>
      <SelectTrigger
        size="sm"
        className="h-7 w-auto gap-1 border-none bg-transparent px-2 text-xs text-muted-foreground shadow-none hover:bg-muted hover:text-foreground"
      >
        <Bot className="size-3.5" />
        <SelectValue>
          {(v: string) => (v === "standard" ? "Standard" : (agentsList.find((a) => a.id === v)?.name ?? v))}
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="standard">Standard</SelectItem>
        {agentsList.map((a) => (
          <SelectItem key={a.id} value={a.id}>
            {a.name}
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
        placeholder="Nachricht an Brain…"
        rows={1}
        disabled={streaming}
        className="min-h-[48px] max-h-52 resize-none border-0 bg-transparent px-4 py-3.5 text-sm shadow-none focus-visible:ring-0"
      />
      <div className="flex items-center justify-between px-2 pb-2">
        <div className="flex items-center gap-1">
          {modelSelect}
          {agentSelect}
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
            title="Datei an diese Nachricht anhängen (wird sofort für diese Anfrage genutzt UND dauerhaft im Wissen abgelegt)"
          >
            {attaching ? <Loader2 className="size-4 animate-spin" /> : <Paperclip className="size-4" />}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileSelect}
            disabled={uploading}
          />
          <Button
            size="icon"
            variant="ghost"
            className="size-7 rounded-full text-muted-foreground hover:text-foreground"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            title="Datei dauerhaft ins Wissen aufnehmen (RAG-Index)"
          >
            <BookPlus className="size-4" />
          </Button>
          {uploading && <span className="text-xs text-muted-foreground">Wird verarbeitet…</span>}
        </div>
        <Button
          size="icon"
          className="size-8 rounded-full"
          onClick={() => send()}
          disabled={streaming || !input.trim()}
        >
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
            <BrainCircuit className="size-5 text-accent-foreground" />
          </div>
          <h1 className="font-display text-3xl text-foreground">Womit kann ich helfen?</h1>
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
              <div className="text-xs text-muted-foreground">{s.prompt}</div>
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
                  <BrainCircuit className="relative size-3.5" />
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Brain</div>
                  {/* prose-invert nur im Dunkelmodus: seit der helle Modus der
                      Standard ist (main.tsx, defaultTheme="light"), färbte die
                      Invert-Palette Überschriften, Fettes, Listenpunkte, Code
                      und Links fast weiß - auf hellem Grund unlesbar bzw.
                      "verrückt". Fließtext blieb nur zufällig sichtbar, weil
                      text-foreground danebensteht. */}
                  {!isThinking && (
                    <div className="prose dark:prose-invert prose-sm max-w-none text-foreground">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  )}
                  {!!m.sources?.length && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.sources.map((s) => (
                        <span
                          key={s.path}
                          title={s.path}
                          className="inline-flex max-w-56 items-center gap-1 truncate rounded-full border border-border bg-muted/60 px-2 py-0.5 text-[11px] text-muted-foreground"
                        >
                          <FileText className="size-3 shrink-0" />
                          <span className="truncate">{s.path.split("/").pop()}</span>
                        </span>
                      ))}
                    </div>
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
