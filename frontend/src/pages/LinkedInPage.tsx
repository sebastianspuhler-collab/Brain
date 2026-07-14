import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ArrowUp } from "lucide-react";
import { api, streamPostChat, type ChatMessage } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

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
}

interface PostDetailData {
  id: string;
  tag: string;
  termin: string;
  idee: string;
  typ: string;
  text: string;
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
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 text-xs h-7 px-2"
          onClick={() => onWrite(idea)}
        >
          Schreiben
        </Button>
      </div>
    </div>
  );
}

/** Detail-/Bearbeitungsansicht für einen einzelnen geplanten Post: voller
 * Text (direkt editierbar + speicherbar) und ein Chat, um Claude bitten zu
 * können den Post zu überarbeiten ("mach den Hook kürzer" etc.). */
function PostDetail({ postId, onClose }: { postId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const detailQuery = useQuery({
    queryKey: ["li-post", postId],
    queryFn: () => api.get<PostDetailData>(`/api/linkedin/posts/${postId}`),
  });

  useEffect(() => {
    if (detailQuery.data?.text !== undefined) setText(detailQuery.data.text);
  }, [detailQuery.data?.text]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const saveDirect = useMutation({
    mutationFn: () => api.post(`/api/linkedin/posts/${postId}`, { text }),
    onSuccess: () => {
      toast.success("Post gespeichert");
      queryClient.invalidateQueries({ queryKey: ["li-posts"] });
      queryClient.invalidateQueries({ queryKey: ["li-post", postId] });
    },
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });

  async function sendChat() {
    const msg = input.trim();
    if (!msg || streaming) return;
    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: msg }];
    setMessages([...nextMessages, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);
    setError("");

    let assistantText = "";
    try {
      await streamPostChat(postId, nextMessages, (event) => {
        if (event.error) throw new Error(event.error);
        if (event.chunk) {
          assistantText += event.chunk;
          setMessages([...nextMessages, { role: "assistant", content: assistantText }]);
        }
        if (event.post_updated && event.text !== undefined) {
          setText(event.text);
          queryClient.invalidateQueries({ queryKey: ["li-posts"] });
        }
      });
    } catch {
      setError("Verbindung unterbrochen. Bitte erneut versuchen.");
    } finally {
      setStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  }

  return (
    <Card className="lg:col-span-2">
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>
          {detailQuery.data?.tag ? `${detailQuery.data.tag}: ` : ""}
          {detailQuery.data?.idee || "Post bearbeiten"}
        </CardTitle>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Schließen
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 lg:flex-row">
        <div className="flex-1 min-w-0">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="min-h-56 font-mono text-sm"
          />
          <div className="flex items-center justify-between mt-1.5">
            <p className="text-xs text-muted-foreground">{text.length} Zeichen</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => saveDirect.mutate()}
              disabled={saveDirect.isPending || text === detailQuery.data?.text}
            >
              {saveDirect.isPending ? "Speichere…" : "Speichern"}
            </Button>
          </div>
        </div>

        {/* Chat zur Überarbeitung */}
        <div className="flex flex-col w-full lg:w-80 shrink-0 border-t lg:border-t-0 lg:border-l border-border pt-3 lg:pt-0 lg:pl-4">
          <div className="flex-1 max-h-64 overflow-y-auto flex flex-col gap-2.5 pr-1">
            {messages.length === 0 && (
              <p className="text-xs text-muted-foreground">
                z.B. "Mach den Hook kürzer" oder "Formuliere Absatz 2 um"
              </p>
            )}
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="self-end max-w-[85%] rounded-2xl bg-muted px-3 py-1.5 text-xs">
                  {m.content}
                </div>
              ) : (
                <div key={i} className="text-xs text-foreground">
                  {m.content || (streaming && i === messages.length - 1 ? "…" : "")}
                </div>
              )
            )}
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div ref={bottomRef} />
          </div>
          <div className="flex items-end gap-1.5 mt-2 rounded-xl border border-border bg-card/60 px-2 py-1.5">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Änderung vorschlagen…"
              rows={1}
              disabled={streaming}
              className="min-h-8 max-h-32 resize-none border-0 bg-transparent px-1 py-1 text-xs shadow-none focus-visible:ring-0"
            />
            <Button
              size="icon"
              className="size-7 shrink-0 rounded-full"
              onClick={sendChat}
              disabled={streaming || !input.trim()}
            >
              <ArrowUp className="size-3.5" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function LinkedInPage() {
  const queryClient = useQueryClient();
  const [focus, setFocus] = useState("");
  const [draftText, setDraftText] = useState("");
  const [draftIdea, setDraftIdea] = useState<Idea | null>(null);
  const [scheduledAt, setScheduledAt] = useState("");
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);

  const ideasQuery = useQuery({
    queryKey: ["li-ideas"],
    queryFn: () => api.get<{ ideen: Idea[]; datum: string | null }>("/api/linkedin/ideas"),
  });
  const postsQuery = useQuery({
    queryKey: ["li-posts"],
    queryFn: () => api.get<{ posts: Post[]; datum: string | null }>("/api/linkedin/posts"),
  });

  const generateIdeas = useMutation({
    mutationFn: () => api.post("/api/linkedin/generate-ideas", { focus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["li-ideas"] });
      toast.success("Neue Ideen generiert");
    },
    onError: () => toast.error("Ideen-Generierung fehlgeschlagen"),
  });

  const generatePost = useMutation({
    mutationFn: (idea: Idea) =>
      api.post<{ ok?: boolean; posts?: { text: string }[]; error?: string }>(
        "/api/linkedin/generate-posts",
        { spec: `Schreibe einen vollständigen LinkedIn-Post zum Thema: "${idea.titel}". Hook: "${idea.hook}". Format: ${idea.format}. CTA: "${idea.cta}". Termin: nächster Dienstag oder Freitag, 09:30 Uhr.` }
      ),
    onSuccess: (data, idea) => {
      const text = data.posts?.[0]?.text ?? "";
      setDraftText(text);
      setDraftIdea(idea);
      if (!text) toast.error("Kein Text generiert");
      queryClient.invalidateQueries({ queryKey: ["li-posts"] });
    },
    onError: () => toast.error("Post-Generierung fehlgeschlagen"),
  });

  const pushBuffer = useMutation({
    mutationFn: () =>
      api.post<{ ok?: boolean; error?: unknown }>("/api/linkedin/push-buffer", {
        text: draftText,
        scheduled_at: scheduledAt || null,
      }),
    onSuccess: (data) => {
      if (data.ok) {
        toast.success("Post auf beide Kanäle gepusht (Sebastian + Prozessia)");
        setDraftText("");
        setDraftIdea(null);
        queryClient.invalidateQueries({ queryKey: ["li-posts"] });
      } else {
        toast.error("Buffer-Fehler: " + JSON.stringify(data.error));
      }
    },
    onError: () => toast.error("Push fehlgeschlagen"),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Geplante Beiträge */}
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
                    <Badge variant="outline" className="text-xs">{p.tag}</Badge>
                    <span className="text-xs text-muted-foreground">{p.termin.slice(0, 10)}</span>
                  </div>
                  <p className="text-sm font-medium">{p.idee}</p>
                  {p.text_preview && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{p.text_preview}</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Ideen */}
      <Card>
        <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
          <CardTitle>Ideen</CardTitle>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Fokus (optional)"
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              className="w-36"
            />
            <Button size="sm" onClick={() => generateIdeas.mutate()} disabled={generateIdeas.isPending}>
              {generateIdeas.isPending ? "..." : "Neue Ideen"}
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
                  onWrite={(idea) => generatePost.mutate(idea)}
                />
              ))}
            </div>
          )}
          {generatePost.isPending && (
            <p className="text-xs text-muted-foreground mt-2">Post wird geschrieben…</p>
          )}
        </CardContent>
      </Card>

      {/* Post-Detail: Bearbeiten + Chat (Klick auf einen geplanten Beitrag) */}
      {selectedPostId && (
        <PostDetail postId={selectedPostId} onClose={() => setSelectedPostId(null)} />
      )}

      {/* Entwurf + Buffer-Push (frisch aus einer Idee geschrieben) */}
      {(draftText || draftIdea) && (
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
            <CardTitle>
              Entwurf{draftIdea ? `: ${draftIdea.titel}` : ""}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                className="w-48 text-xs"
                title="Zeitpunkt (leer = nächster freier Slot)"
              />
              <Button
                size="sm"
                onClick={() => pushBuffer.mutate()}
                disabled={pushBuffer.isPending || !draftText.trim()}
              >
                {pushBuffer.isPending ? "Pushe…" : "In Buffer pushen"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setDraftText(""); setDraftIdea(null); }}>
                Verwerfen
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Textarea
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              className="min-h-48 font-mono text-sm"
              placeholder="Post-Text…"
            />
            <p className="text-xs text-muted-foreground mt-1.5">
              {draftText.length} Zeichen · Wird auf Sebastian- und Prozessia-Kanal gepusht
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
