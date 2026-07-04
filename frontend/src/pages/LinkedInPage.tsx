import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
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
  tag: string;
  termin: string;
  idee: string;
  text_preview: string;
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

export function LinkedInPage() {
  const queryClient = useQueryClient();
  const [focus, setFocus] = useState("");
  const [draftText, setDraftText] = useState("");
  const [draftIdea, setDraftIdea] = useState<Idea | null>(null);
  const [scheduledAt, setScheduledAt] = useState("");

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
              {postsQuery.data.posts.map((p, i) => (
                <div key={i} className="flex flex-col gap-1 border-b border-border pb-3 last:border-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">{p.tag}</Badge>
                    <span className="text-xs text-muted-foreground">{p.termin.slice(0, 10)}</span>
                  </div>
                  <p className="text-sm font-medium">{p.idee}</p>
                  {p.text_preview && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{p.text_preview}</p>
                  )}
                </div>
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

      {/* Entwurf + Buffer-Push */}
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
