import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface Space {
  kunde: string;
  score: number;
  ordner: Record<string, number>;
  fehlend: string[];
}

const ORDNER_LABEL: Record<string, string> = {
  Vertraege: "Verträge",
  Angebote: "Angebote",
  Meetings: "Meetings",
  Dokumente: "Dokumente",
};

function scoreColor(score: number): string {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  if (score >= 25) return "bg-orange-500";
  return "bg-red-500";
}

export function SpacesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["spaces"],
    queryFn: () => api.get<{ spaces: Space[] }>("/api/spaces"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Spaces</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-muted-foreground">
          Wie viele der vier Standard-Unterordner (Verträge, Angebote, Meetings, Dokumente)
          tatsächlich Dateien enthalten — rein faktenbasiert, keine KI-Schätzung. Ein niedriger Wert
          heißt nicht zwangsläufig, dass etwas fehlt: manche Engagements laufen z.B. ohne
          formellen Vertrag oder ohne separaten Angebots-Ordner.
        </p>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : !data?.spaces.length ? (
          <p className="text-sm text-muted-foreground">Keine Kundenordner gefunden.</p>
        ) : (
          <div className="flex flex-col divide-y divide-border">
            {data.spaces.map((s) => (
              <div key={s.kunde} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-foreground">{s.kunde}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-32 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn("h-full rounded-full", scoreColor(s.score))}
                        style={{ width: `${s.score}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">
                      {s.score}%
                    </span>
                  </div>
                </div>
                {s.fehlend.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Fehlt: {s.fehlend.map((f) => ORDNER_LABEL[f] ?? f).join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
