import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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

export function LinkedInPage() {
  const queryClient = useQueryClient();
  const [focus, setFocus] = useState("");

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

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Geplante Beiträge</CardTitle>
        </CardHeader>
        <CardContent>
          {!postsQuery.data?.posts.length ? (
            <p className="text-sm text-muted-foreground">Keine Beiträge in der Pipeline.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-32">Termin</TableHead>
                  <TableHead>Idee</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {postsQuery.data.posts.map((p, i) => (
                  <TableRow key={i}>
                    <TableCell className="whitespace-nowrap">
                      {p.tag} {p.termin.slice(0, 10)}
                    </TableCell>
                    <TableCell>{p.idee}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
          <CardTitle>Ideen</CardTitle>
          <div className="flex items-center gap-2">
            <Input placeholder="Fokus (optional)" value={focus} onChange={(e) => setFocus(e.target.value)} className="w-40" />
            <Button size="sm" onClick={() => generateIdeas.mutate()} disabled={generateIdeas.isPending}>
              {generateIdeas.isPending ? "..." : "Neue Ideen"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!ideasQuery.data?.ideen.length ? (
            <p className="text-sm text-muted-foreground">Noch keine Ideen generiert.</p>
          ) : (
            <ul className="space-y-3">
              {ideasQuery.data.ideen.map((idea, i) => (
                <li key={i} className="border-b border-border pb-2 last:border-0">
                  <div className="text-sm font-medium">
                    <span className="text-primary">[{idea.kategorie}]</span> {idea.titel}
                  </div>
                  <div className="text-xs text-muted-foreground">{idea.hook}</div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
