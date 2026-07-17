import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface KundeStatus {
  kunde: string;
  letztes_meeting: string | null;
  tage_seit_meeting: number | null;
  ampel: "gruen" | "gelb" | "rot" | "grau";
  offene_aufgaben: number;
}

interface LinkedInStatus {
  geplante_posts: number;
  gepushte_posts: number;
  offene_ideen: number;
  naechster_post: { termin: string; idee: string } | null;
}

const AMPEL_COLOR: Record<KundeStatus["ampel"], string> = {
  gruen: "bg-emerald-500",
  gelb: "bg-amber-500",
  rot: "bg-red-500",
  grau: "bg-muted-foreground/40",
};

// Zeigt nur die Zeit seit der letzten erfassten Aktivität (Meeting, Dokument,
// Vertrag, E-Mail-Korrespondenz) - keine Bewertung der Kundenbeziehung. Ein
// "rot" kann genauso gut ein stabiles, ruhig laufendes Projekt ohne
// Gesprächsbedarf bedeuten wie tatsächlichen Nachfassbedarf.
const AMPEL_LABEL: Record<KundeStatus["ampel"], string> = {
  gruen: "Letzte Aktivität < 30 Tage her",
  gelb: "Letzte Aktivität 30-90 Tage her",
  rot: "Letzte Aktivität > 90 Tage her",
  grau: "Keine Aktivität erfasst",
};

function formatDatum(datum: string | null): string {
  if (!datum) return "–";
  const [y, m, d] = datum.split("-");
  return `${d}.${m}.${y}`;
}

function formatTermin(iso: string): string {
  const [date, time] = iso.split("T");
  const [y, m, d] = date.split("-");
  return `${d}.${m}.${y}${time ? " " + time.slice(0, 5) : ""}`;
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border p-3">
      <span className="text-2xl font-semibold tabular-nums text-foreground">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

export function DashboardPage() {
  const { data: kundenData, isLoading: kundenLoading } = useQuery({
    queryKey: ["dashboard-kunden-status"],
    queryFn: () => api.get<{ kunden: KundeStatus[] }>("/api/dashboard/kunden-status"),
  });
  const { data: li, isLoading: liLoading } = useQuery({
    queryKey: ["dashboard-linkedin-status"],
    queryFn: () => api.get<LinkedInStatus>("/api/dashboard/linkedin-status"),
  });

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>LinkedIn-Status</CardTitle>
        </CardHeader>
        <CardContent>
          {liLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="Geplante Posts" value={li?.geplante_posts ?? 0} />
              <StatTile label="Gepushte Posts" value={li?.gepushte_posts ?? 0} />
              <StatTile label="Offene Ideen" value={li?.offene_ideen ?? 0} />
              <div className="flex flex-col gap-1 rounded-xl border border-border p-3">
                <span className="text-sm font-medium text-foreground">
                  {li?.naechster_post ? formatTermin(li.naechster_post.termin) : "–"}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {li?.naechster_post?.idee ?? "Kein Post geplant"}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Kunden-Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">
            Zeigt nur die Zeit seit der letzten erfassten Aktivität (Meeting, Dokument, Vertrag
            oder E-Mail-Korrespondenz), keine Bewertung der Kundenbeziehung — ein stabiles Projekt
            ohne Gesprächsbedarf sieht hier genauso aus wie eines, bei dem tatsächlich
            nachgefasst werden sollte.
          </p>
          {kundenLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : !kundenData?.kunden.length ? (
            <p className="text-sm text-muted-foreground">Keine Kunden gefunden.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>Kunde</TableHead>
                  <TableHead>Letzte Aktivität</TableHead>
                  <TableHead className="w-32">Offene Aufgaben</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kundenData.kunden.map((k) => (
                  <TableRow key={k.kunde}>
                    <TableCell>
                      <span
                        className={cn("inline-block size-2.5 rounded-full", AMPEL_COLOR[k.ampel])}
                        title={AMPEL_LABEL[k.ampel]}
                      />
                    </TableCell>
                    <TableCell className="font-medium text-foreground">{k.kunde}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDatum(k.letztes_meeting)}
                      {k.tage_seit_meeting !== null && (
                        <span className="ml-1.5 text-xs">({k.tage_seit_meeting} Tage)</span>
                      )}
                    </TableCell>
                    <TableCell className="tabular-nums">{k.offene_aufgaben || "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
