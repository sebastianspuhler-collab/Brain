import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowUp, BrainCircuit, Image as ImageIcon } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, streamLinkedInChat, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { StatusPill, type StatusPillVariant } from "@/components/shared/status-pill";

interface Idea {
  titel: string;
  hook: string;
  kategorie: string;
  format: string;
  cta: string;
}

/** Ein Post aus dem echten Live-Buffer-Stand (GET /api/linkedin/posts?status=
 * draft|scheduled, siehe linkedin_service.get_merged_posts_by_status) - id ist
 * nur gesetzt, wenn diese Pipeline den Post lokal geschrieben hat (Text
 * editierbar); bei id=null (z.B. Karusselle, oder Drafts die Sebastian direkt
 * in Buffer anlegt) gibt es nur buffer_ids, keinen editierbaren Volltext. */
interface Post {
  id: string | null;
  buffer_ids?: string[];
  text_preview: string;
  status: string;
  due: string | null;
  has_media: boolean;
  source: "lokal" | "buffer";
  carousel_id?: string | null;
  thumb_url?: string | null;
  pdf_url?: string | null;
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

const STATUS_LABEL: Record<string, string> = {
  draft: "Entwurf",
  scheduled: "geplant",
  sent: "gesendet",
  lokal_ungeplant: "nur lokal",
  lokal_verwaist: "verwaist – bitte prüfen",
};

const STATUS_VARIANT: Record<string, StatusPillVariant> = {
  draft: "info",
  scheduled: "success",
  sent: "neutral",
  lokal_ungeplant: "neutral",
  lokal_verwaist: "danger",
};

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
                  <div className="prose dark:prose-invert prose-sm max-w-none text-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || (streaming && i === messages.length - 1 ? "…" : "")}</ReactMarkdown>
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
/** Bei lokal geschriebenen Text-Posts (post.id gesetzt) voll editierbar. Bei
 * Buffer-only-Posts (Karusselle, oder Drafts die Sebastian direkt in Buffer
 * anlegt - post.id ist null) gibt es keinen editierbaren Volltext, nur eine
 * schreibgeschützte Übersicht mit Design-Vorschau - Textänderungen/Planen
 * dafür laufen ausschließlich über den Chat. */
function PostDetailSheet({ post, onClose }: { post: Post | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const postId = post?.id ?? null;

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
    <Sheet open={!!post} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-lg flex flex-col gap-4 p-4">
        <SheetHeader className="p-0">
          <SheetTitle className="line-clamp-2">
            {postId ? detailQuery.data?.idee || "Post bearbeiten" : "Post-Details"}
          </SheetTitle>
          <div className="flex items-center gap-1.5 pt-1 flex-wrap">
            {post && (
              <StatusPill variant={STATUS_VARIANT[post.status] || "neutral"}>
                {STATUS_LABEL[post.status] || post.status}
              </StatusPill>
            )}
            {post?.has_media && <StatusPill variant="neutral">Karussell</StatusPill>}
            {post?.due && <span className="text-xs text-muted-foreground">{post.due.slice(0, 16).replace("T", " ")}</span>}
          </div>
        </SheetHeader>

        {postId ? (
          <>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} className="min-h-72 flex-1 font-mono text-sm" />
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{text.length} Zeichen</p>
              <Button size="sm" onClick={() => saveDirect.mutate()} disabled={saveDirect.isPending || text === detailQuery.data?.text}>
                {saveDirect.isPending ? "Speichere…" : "Speichern"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Einplanen oder Karussell erstellen: einfach im Chat auf diesen Post beziehen (z.B. "Plane den Post zu{" "}
              {detailQuery.data?.idee ? `"${detailQuery.data.idee}"` : "..."} für morgen 12 Uhr").
            </p>
          </>
        ) : (
          <>
            {post?.thumb_url && (
              <img src={post.thumb_url} alt="Karussell-Vorschau" className="w-full rounded-xl border border-border object-cover" />
            )}
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{post?.text_preview}</p>
            {post?.pdf_url && (
              <a href={post.pdf_url} target="_blank" rel="noreferrer" className="text-sm text-primary hover:underline">
                Vollständiges Karussell-PDF ansehen
              </a>
            )}
            <p className="text-xs text-muted-foreground">
              Dieser Post wurde nicht hier lokal geschrieben (z.B. ein Karussell oder direkt in Buffer angelegt) -
              Volltext, Termin-Änderung oder Löschen laufen nur über den Chat, z.B. "plane das Karussell zu{" "}
              {post?.text_preview ? `"${post.text_preview.slice(0, 40)}…"` : "..."} für Donnerstag ein".
            </p>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

/** Eine Post-Karte für Entwürfe/Geplant - Karussell-Thumbnail (falls vorhanden)
 * plus Status/Termin/Text-Vorschau. Klick öffnet immer die Detailansicht (auch
 * bei Buffer-only-Posts ohne lokale id, siehe PostDetailSheet), statt Text nur
 * abgeschnitten in der Liste stehen zu lassen. */
function PostCard({ post, onOpen }: { post: Post; onOpen: (post: Post) => void }) {
  const due = post.due ? post.due.slice(0, 16).replace("T", " ") : null;
  return (
    <button
      onClick={() => onOpen(post)}
      className="flex gap-3 border-b border-border pb-3 last:border-0 text-left transition hover:opacity-80"
    >
      {post.thumb_url ? (
        <img src={post.thumb_url} alt="" className="size-16 shrink-0 rounded-lg object-cover border border-border" />
      ) : post.has_media ? (
        <div className="flex size-16 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <ImageIcon className="size-5" />
        </div>
      ) : null}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <StatusPill variant={STATUS_VARIANT[post.status] || "neutral"}>{STATUS_LABEL[post.status] || post.status}</StatusPill>
          {post.has_media && <StatusPill variant="neutral">Karussell</StatusPill>}
          {due && <span className="text-xs text-muted-foreground">{due}</span>}
        </div>
        <p className="text-sm mt-1 line-clamp-2">{post.text_preview}</p>
      </div>
    </button>
  );
}

function PostList({ posts, emptyHint, onOpen }: { posts: Post[]; emptyHint: string; onOpen: (post: Post) => void }) {
  if (!posts.length) {
    return <p className="text-sm text-muted-foreground">{emptyHint}</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      {posts.map((p, i) => (
        <PostCard key={p.id ?? p.buffer_ids?.join(",") ?? i} post={p} onOpen={onOpen} />
      ))}
    </div>
  );
}

export function LinkedInPage() {
  const queryClient = useQueryClient();
  const [focus, setFocus] = useState("");
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");

  const ideasQuery = useQuery({
    queryKey: ["li-ideas"],
    queryFn: () => api.get<{ ideen: Idea[]; datum: string | null }>("/api/linkedin/ideas"),
  });
  const draftsQuery = useQuery({
    queryKey: ["li-posts", "draft"],
    queryFn: () => api.get<{ posts: Post[] }>("/api/linkedin/posts?status=draft"),
  });
  const scheduledQuery = useQuery({
    queryKey: ["li-posts", "scheduled"],
    queryFn: () => api.get<{ posts: Post[] }>("/api/linkedin/posts?status=scheduled"),
  });

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ["li-ideas"] });
    queryClient.invalidateQueries({ queryKey: ["li-posts"] });
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

      <Tabs defaultValue="ideen" className="flex flex-col">
        <TabsList className="w-full">
          <TabsTrigger value="ideen" className="flex-1">Ideen</TabsTrigger>
          <TabsTrigger value="entwuerfe" className="flex-1">
            Entwürfe{draftsQuery.data?.posts.length ? ` (${draftsQuery.data.posts.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="geplant" className="flex-1">
            Geplant{scheduledQuery.data?.posts.length ? ` (${scheduledQuery.data.posts.length})` : ""}
          </TabsTrigger>
        </TabsList>

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
                          `Mach aus dieser Idee einen fertigen Post: "${idea.titel}". Hook: "${idea.hook}". Format: ${idea.format}. CTA: "${idea.cta}".`
                        )
                      }
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entwuerfe">
          <Card>
            <CardHeader>
              <CardTitle>Entwürfe</CardTitle>
            </CardHeader>
            <CardContent>
              <PostList
                posts={draftsQuery.data?.posts ?? []}
                emptyHint='Noch keine Entwürfe - im Chat z.B. "mach aus Idee X einen Post" schreiben.'
                onOpen={setSelectedPost}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="geplant">
          <Card>
            <CardHeader>
              <CardTitle>Geplante Beiträge</CardTitle>
            </CardHeader>
            <CardContent>
              <PostList
                posts={scheduledQuery.data?.posts ?? []}
                emptyHint='Noch nichts eingeplant - im Chat z.B. "plane den Entwurf zu X für Dienstag ein" schreiben.'
                onOpen={setSelectedPost}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <PostDetailSheet post={selectedPost} onClose={() => setSelectedPost(null)} />
    </div>
  );
}
