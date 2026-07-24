import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowUp, Bot, BrainCircuit, FileText, Paperclip } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { agents as agentsApi, api, chatSessions, streamChat, type Agent, type ChatMessage, type ChatSource } from "@/api/client";
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

  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [agentsList, setAgentsList] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    // Erste Nachricht eines neuen Chats -> Session-ID erzeugen und in der URL
    // hinterlegen, damit ein Reload denselben Chat wieder findet.
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      activeSessionId = crypto.randomUUID();
      setSearchParams({ session: activeSessionId }, { replace: true });
    }

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput("");
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
            title="Datei anhängen (wird im Wissen abgelegt)"
          >
            <Paperclip className="size-4" />
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
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-3xl bg-muted px-4 py-2 text-sm text-foreground">
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
                  {!isThinking && (
                    <div className="prose prose-invert prose-sm max-w-none text-foreground">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
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
