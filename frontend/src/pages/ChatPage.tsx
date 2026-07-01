import { useEffect, useRef, useState } from "react";
import { ArrowUp, BrainCircuit } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { streamChat, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const MODELS = [
  { id: "claude-sonnet-4-6", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

const SUGGESTIONS = [
  { title: "Offene Aufgaben", prompt: "Was steht diese Woche an?" },
  { title: "Mails zusammenfassen", prompt: "Fasse die neuesten E-Mails zusammen." },
  { title: "Kundenstatus", prompt: "Wie ist der aktuelle Stand bei Schaufler?" },
  { title: "Neues Memo", prompt: "Erstelle ein Memo zum heutigen Gespräch." },
];

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || streaming) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);
    setError("");

    const controller = new AbortController();
    abortRef.current = controller;

    let assistantText = "";
    try {
      await streamChat(
        nextMessages,
        model,
        (chunk) => {
          assistantText += chunk;
          setMessages([...nextMessages, { role: "assistant", content: assistantText }]);
        },
        controller.signal
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError("Verbindung unterbrochen. Bitte erneut versuchen.");
      }
    } finally {
      setStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
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
        {modelSelect}
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
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-3xl bg-muted px-4 py-2 text-sm text-foreground">
                  {m.content}
                </div>
              </div>
            ) : (
              <div key={i} className="flex gap-3">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <BrainCircuit className="size-3.5" />
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Brain</div>
                  <div className="prose prose-invert prose-sm max-w-none text-foreground">
                    <ReactMarkdown>
                      {m.content || (streaming && i === messages.length - 1 ? "…" : "")}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="sticky bottom-0 bg-background pt-2 pb-1">{inputBar}</div>
    </div>
  );
}
