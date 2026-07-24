import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowUp, BrainCircuit } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, streamLinkedInChat, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatusPill } from "@/components/shared/status-pill";

interface Idea {
  titel: string;
  hook: string;
  kategorie: string;
  format: string;
  cta: string;
}

interface Post {
  id: string;
  tag: string;
  termin: string;
  idee: string;
  text_preview: string;
  pushed?: boolean;
}

interface PostDetailData {
  id: string;
  tag: string;
  termin: string;
  idee: string;
  typ: string;
  text: string;
  pushed?: boolean;
}

interface Carousel {
  id: string;
  source_post_id: string | null;
  hook: string;
  branche: string;
  slide_titles: string[];
  thumb_url: string | null;
  pdf_url: string | null;
  due_at: string | null;
  anzahl_gepusht: number;
  created_at: string;
}

const SUGGESTIONS = [
  { title: "Neue Ideen", prompt: "Generiere 10 neue LinkedIn-Ideen." },
  { title: "Was ist geplant?", prompt: "Was ist aktuell geplant?" },
  { title: "Karussell erstellen", prompt: "Erstelle ein Karussell zum Thema Stücklistenprüfung, Branche Werkzeugbau." },
  { title: "Richtung setzen", prompt: "Setz den Fokus für die nächsten Ideen auf: " },
];

/** Der große, primäre Chat für die gesamte LinkedIn-Sektion: Ideen, Posts,
 * Karusselle, Richtung - alles über eine Konversation steuerbar (siehe
 * backend linkedin_service.chat_linkedin()). State lebt in LinkedInPage, damit
 * Klicks außerhalb des Chats (z.B. "Schreiben" bei einer Idee) Nachrichten
 * einspeisen können. */
function LinkedInChat({
  messages,
  streaming,
  error,
  onSend,
}: {
  messages: ChatMessage[];
  streaming: boolean;
  error: string;
  onSend: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function submit() {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    onSend(text);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const inputBar = (
    <div className="flex flex-col rounded-3xl border border-border bg-card/60 shadow-lg backdrop-blur-sm transition focus-within:border-ring/50">
      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="z.B. 'Erstelle 10 neue Ideen zu Compliance' oder 'Plane den letzten Post für morgen 12 Uhr'…"
        rows={1}
        disabled={streaming}
        className="min-h-[48px] max-h-52 resize-none border-0 bg-transparent px-4 py-3.5 text-sm shadow-none focus-visible:ring-0"
      />
      <div className="flex items-center justify-end px-2 pb-2">
        <Button size="icon" className="size-8 rounded-full" onClick={submit} disabled={streaming || !input.trim()}>
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </div>
  );

  if (messages.length === 0) {
    return (
      <Card className="flex h-[calc(100vh-8rem)] flex-col justify-center gap-6 px-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex size-11 items-center justify-center rounded-full bg-accent">
            <BrainCircuit className="size-5 text-accent-foreground" />
          </div>
          <h2 className="font-display text-2xl text-foreground">LinkedIn steuern</h2>
          <p className="text-sm text-muted-foreground max-w-md">
            Ideen generieren, Posts schreiben, einplanen oder als Karussell erstellen - alles im Gespräch.
          </p>
        </div>
        <div className="mx-auto w-full max-w-lg">{inputBar}</div>
        <div className="mx-auto grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.title}
              onClick={() => onSend(s.prompt)}
              className="rounded-xl border border-border px-3.5 py-2.5 text-left transition hover:bg-muted"
            >
              <div className="text-sm font-medium text-foreground">{s.title}</div>
              <div className="text-xs text-muted-foreground line-clamp-1">{s.prompt}</div>
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-destructive text-center">{error}</p>}
      </Card>
    );
  }

  return (
    <Card className="flex h-[calc(100vh-8rem)] flex-col p-0">
      <div className="flex-1 overflow-y-auto px-4">
        <div className="flex flex-col gap-6 py-4">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-3xl rounded-br-md bg-muted px-4 py-2 text-sm text-foreground">
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
                    <ReactMarkdown>{m.content || (streaming && i === messages.length - 1 ? "…" : "")}</ReactMarkdown>
                  </div>
                </div>
              </div>
            )
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="px-3 pb-3 pt-1">{inputBar}</div>
    </Card>
  );
}

function IdeaCard({ idea, onWrite }: { idea: Idea; onWrite: (idea: Idea) => void }) {
  return (
    <div className="flex flex-col gap-1.5 border-b border-border pb-3 last:border-0 last:pb-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-medium">
            <span className="text-primary mr-1">[{idea.kategorie}]</span>
            {idea.titel}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">{idea.hook}</div>
        </div>
        <Button size="sm" variant="outline" className="shrink-0 text-xs h-7 px-2" onClick={() => onWrite(idea)}>
          Schreiben
        </Button>
      </div>
    </div>
  );
}

/** Schnelle manuelle Ansicht/Bearbeitung eines gespeicherten Posts (Klick in
 * "Geplante Beiträge"). Kein eigener Chat mehr hier - Konversation läuft
 * ausschließlich über den großen LinkedInChat oben. */
function PostDetailSheet({ postId, onClose }: { postId: string | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");

  const detailQuery = useQuery({
    queryKey: ["li-post", postId],
    queryFn: () => api.get<PostDetailData>(`/api/linkedin/posts/${postId}`),
    enabled: !!postId,
  });

  useEffect(() => {
    if (detailQuery.data?.text !== undefined) setText(detailQuery.data.text);
  }, [detailQuery.data?.text]);

  const saveDirect = useMutation({
    mutationFn: () => api.post(`/api/linkedin/posts/${postId}`, { text }),
    onSuccess: () => {
      toast.success("Post gespeichert");
      queryClient.invalidateQueries({ queryKey: ["li-posts"] });
      queryClient.invalidateQueries({ queryKey: ["li-post", postId] });
    },
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });

  return (
    <Sheet open={!!postId} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-lg flex flex-col gap-4 p-4">
        <SheetHeader className="p-0">
          <SheetTitle>
            {detailQuery.data?.tag ? `${detailQuery.data.tag}: ` : ""}
            {detailQuery.data?.idee || "Post bearbeiten"}
          </SheetTitle>
          <div className="flex items-center gap-1.5 pt-1">
            <StatusPill variant={detailQuery.data?.pushed ? "success" : "neutral"}>
              {detailQuery.data?.pushed ? "In Buffer geplant" : "Noch nicht geplant"}
            </StatusPill>
            {detailQuery.data?.termin && (
              <span className="text-xs text-muted-foreground">{detailQuery.data.termin.slice(0, 16).replace("T", " ")}</span>
            )}
          </div>
        </SheetHeader>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} className="min-h-72 flex-1 font-mono text-sm" />
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">{text.length} Zeichen</p>
          <Button size="sm" onClick={() => saveDirect.mutate()} disabled={saveDirect.isPending || text === detailQuery.data?.text}>
            {saveDirect.isPending ? "Speichere…" : "Speichern"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Planen, Umschreiben oder Karussell erstellen: einfach im Chat auf diesen Post beziehen (z.B. "Plane den Post zu{" "}
          {detailQuery.data?.idee ? `"${detailQuery.data.idee}"` : "..."} für morgen 12 Uhr").
        </p>
      </SheetContent>
    </Sheet>
  );
}

function CarouselCard({ c }: { c: Carousel }) {
  return (
    <div className="flex gap-3 border-b border-border pb-3 last:border-0 last:pb-0">
      {c.thumb_url ? (
        <img src={c.thumb_url} alt={c.hook} className="size-20 shrink-0 rounded-lg object-cover border border-border" />
      ) : (
        <div className="size-20 shrink-0 rounded-lg bg-muted" />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium line-clamp-2">{c.hook}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {c.branche} · {c.slide_titles.length} Slides · {c.anzahl_gepusht > 0 ? "eingeplant" : "nicht gepusht"}
        </p>
        {c.pdf_url && (
          <a href={c.pdf_url} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">
            PDF ansehen
          </a>
        )}
      </div>
    </div>
  );
}

export function LinkedInPage() {
  const queryClient = useQueryClient();
  const [focus, setFocus] = useState("");
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");

  const ideasQuery = useQuery({
    queryKey: ["li-ideas"],
    queryFn: () => api.get<{ ideen: Idea[]; datum: string | null }>("/api/linkedin/ideas"),
  });
  const postsQuery = useQuery({
    queryKey: ["li-posts"],
    queryFn: () => api.get<{ posts: Post[]; datum: string | null }>("/api/linkedin/posts"),
  });
  const carouselsQuery = useQuery({
    queryKey: ["li-carousels"],
    queryFn: () => api.get<{ karusselle: Carousel[] }>("/api/linkedin/carousels"),
  });

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ["li-ideas"] });
    queryClient.invalidateQueries({ queryKey: ["li-posts"] });
    queryClient.invalidateQueries({ queryKey: ["li-carousels"] });
  }

  async function sendChat(text: string) {
    if (streaming) return;
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setStreaming(true);
    setError("");

    let assistantText = "";
    try {
      await streamLinkedInChat(nextMessages, (event) => {
        if (event.error) throw new Error(event.error);
        if (event.chunk) {
          assistantText += event.chunk;
          setMessages([...nextMessages, { role: "assistant", content: assistantText }]);
        }
        if (event.state_changed) invalidateAll();
      });
    } catch {
      setError("Verbindung unterbrochen. Bitte erneut versuchen.");
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_400px]">
      <LinkedInChat messages={messages} streaming={streaming} error={error} onSend={sendChat} />

      <Tabs defaultValue="geplant" className="flex flex-col">
        <TabsList className="w-full">
          <TabsTrigger value="geplant" className="flex-1">Geplant</TabsTrigger>
          <TabsTrigger value="ideen" className="flex-1">Ideen</TabsTrigger>
          <TabsTrigger value="karusselle" className="flex-1">Karusselle</TabsTrigger>
        </TabsList>

        <TabsContent value="geplant">
          <Card>
            <CardHeader>
              <CardTitle>Geplante Beiträge</CardTitle>
            </CardHeader>
            <CardContent>
              {!postsQuery.data?.posts.length ? (
                <p className="text-sm text-muted-foreground">Keine Beiträge in der Pipeline.</p>
              ) : (
                <div className="flex flex-col gap-3">
                  {postsQuery.data.posts.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedPostId(p.id)}
                      className="flex flex-col gap-1 border-b border-border pb-3 last:border-0 text-left transition hover:opacity-80"
                    >
                      <div className="flex items-center gap-2">
                        <StatusPill variant="neutral">{p.tag}</StatusPill>
                        <span className="text-xs text-muted-foreground">{p.termin.slice(0, 10)}</span>
                        {p.pushed && <StatusPill variant="success">geplant</StatusPill>}
                      </div>
                      <p className="text-sm font-medium">{p.idee}</p>
                      {p.text_preview && <p className="text-xs text-muted-foreground line-clamp-2">{p.text_preview}</p>}
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ideen">
          <Card>
            <CardHeader className="flex-col items-start gap-2 space-y-0">
              <CardTitle>Ideen</CardTitle>
              <div className="flex w-full items-center gap-2">
                <Input
                  placeholder="Fokus (optional)"
                  value={focus}
                  onChange={(e) => setFocus(e.target.value)}
                  className="flex-1"
                />
                <Button
                  size="sm"
                  onClick={() => sendChat(focus.trim() ? `Generiere 10 neue Ideen mit Fokus auf: ${focus.trim()}` : "Generiere 10 neue Ideen.")}
                  disabled={streaming}
                >
                  Neue Ideen
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!ideasQuery.data?.ideen.length ? (
                <p className="text-sm text-muted-foreground">Noch keine Ideen generiert.</p>
              ) : (
                <div className="flex flex-col gap-3">
                  {ideasQuery.data.ideen.map((idea, i) => (
                    <IdeaCard
                      key={i}
                      idea={idea}
                      onWrite={(idea) =>
                        sendChat(
                          `Schreibe einen vollständigen LinkedIn-Post zum Thema: "${idea.titel}". Hook: "${idea.hook}". Format: ${idea.format}. CTA: "${idea.cta}".`
                        )
                      }
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="karusselle">
          <Card>
            <CardHeader>
              <CardTitle>Karusselle</CardTitle>
            </CardHeader>
            <CardContent>
              {!carouselsQuery.data?.karusselle.length ? (
                <p className="text-sm text-muted-foreground">
                  Noch keine Karusselle erstellt - im Chat z.B. "Erstelle ein Karussell zu ..." schreiben.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {carouselsQuery.data.karusselle.map((c) => (
                    <CarouselCard key={c.id} c={c} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <PostDetailSheet postId={selectedPostId} onClose={() => setSelectedPostId(null)} />
    </div>
  );
}
