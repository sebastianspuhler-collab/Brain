import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamChat, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MODELS = [
  { id: "claude-sonnet-4-6", label: "Sonnet" },
  { id: "claude-opus-4-8", label: "Opus" },
];

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0].id);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  async function send() {
    const text = input.trim();
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

  return (
    <Card className="flex h-[calc(100vh-6.5rem)] flex-col">
      <CardContent className="flex flex-1 flex-col gap-3 overflow-hidden p-4">
        <ScrollArea className="flex-1 pr-4">
          <div className="flex flex-col gap-3">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Frag mich etwas über Kunden, Aufgaben, E-Mails oder Dokumente.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={cn(
                  "max-w-[85%] rounded-lg px-4 py-2 text-sm",
                  m.role === "user"
                    ? "self-end bg-primary text-primary-foreground"
                    : "self-start bg-secondary text-secondary-foreground prose prose-invert prose-sm max-w-none"
                )}
              >
                <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? "…" : "")}</ReactMarkdown>
              </div>
            ))}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        </ScrollArea>
        <div className="flex items-end gap-2">
          <Select value={model} onValueChange={(value) => value && setModel(value)} disabled={streaming}>
            <SelectTrigger className="w-32 shrink-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODELS.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nachricht an Brain..."
            rows={2}
            disabled={streaming}
            className="flex-1 resize-none"
          />
          <Button onClick={send} disabled={streaming || !input.trim()}>
            Senden
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
