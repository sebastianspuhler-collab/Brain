import { Fragment, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Archive, ArchiveRestore, Pencil } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type Ampel = "gruen" | "gelb" | "rot" | "grau";

interface KundeStatus {
  kunde: string;
  letztes_meeting: string | null;
  tage_seit_meeting: number | null;
  ampel: Ampel;
  ampel_automatisch: Ampel;
  offene_aufgaben: number;
  vollstaendigkeit: number;
  archiviert: boolean;
  notiz: string;
}

interface LinkedInStatus {
  geplante_posts: number;
  gepushte_posts: number;
  offene_ideen: number;
  naechster_post: { termin: string; idee: string } | null;
}

const AMPEL_COLOR: Record<Ampel, string> = {
  gruen: "bg-emerald-500",
  gelb: "bg-amber-500",
  rot: "bg-red-500",
  grau: "bg-muted-foreground/40",
};

// Zeigt nur die Zeit seit der letzten erfassten Aktivität (Meeting, Dokument,
// Vertrag, E-Mail-Korrespondenz) - keine Bewertung der Kundenbeziehung. Ein
// "rot" kann genauso gut ein stabiles, ruhig laufendes Projekt ohne
// Gesprächsbedarf bedeuten wie tatsächlichen Nachfassbedarf.
const AMPEL_LABEL: Record<Ampel, string> = {
  gruen: "Letzte Aktivität < 30 Tage her",
  gelb: "Letzte Aktivität 30-90 Tage her",
  rot: "Letzte Aktivität > 90 Tage her",
  grau: "Keine Aktivität erfasst",
};

const AMPEL_OVERRIDE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Automatisch" },
  { value: "gruen", label: "Grün" },
  { value: "gelb", label: "Gelb" },
  { value: "rot", label: "Rot" },
];

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

function useKundenMeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      kunde: string;
      body: { archiviert?: boolean; ampel_override?: string; notiz?: string };
    }) => api.post(`/api/dashboard/kunden/${encodeURIComponent(vars.kunde)}/meta`, vars.body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard-kunden-status"] }),
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });
}

export function DashboardPage() {
  const [zeigeArchivierte, setZeigeArchivierte] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [notizDraft, setNotizDraft] = useState("");
  const [ampelDraft, setAmpelDraft] = useState("");

  const { data: kundenData, isLoading: kundenLoading } = useQuery({
    queryKey: ["dashboard-kunden-status", zeigeArchivierte],
    queryFn: () =>
      api.get<{ kunden: KundeStatus[] }>(
        `/api/dashboard/kunden-status?zeige_archivierte=${zeigeArchivierte}`,
      ),
  });
  const { data: li, isLoading: liLoading } = useQuery({
    queryKey: ["dashboard-linkedin-status"],
    queryFn: () => api.get<LinkedInStatus>("/api/dashboard/linkedin-status"),
  });

  const meta = useKundenMeta();

  function startEdit(k: KundeStatus) {
    setEditing(k.kunde);
    setNotizDraft(k.notiz);
    setAmpelDraft(k.ampel !== k.ampel_automatisch ? k.ampel : "");
  }

  function saveEdit(kunde: string) {
    meta.mutate(
      { kunde, body: { notiz: notizDraft, ampel_override: ampelDraft } },
      { onSuccess: () => setEditing(null) },
    );
  }

  function toggleArchiv(k: KundeStatus) {
    meta.mutate(
      { kunde: k.kunde, body: { archiviert: !k.archiviert } },
      {
        onSuccess: () => {
          toast.success(k.archiviert ? `${k.kunde} wieder sichtbar` : `${k.kunde} archiviert`);
          if (editing === k.kunde) setEditing(null);
        },
      },
    );
  }

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
        <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
          <CardTitle>Kunden-Status</CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Archivierte anzeigen</span>
            <Switch checked={zeigeArchivierte} onCheckedChange={(c) => setZeigeArchivierte(c === true)} />
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">
            Zeigt die Situation pro Kunde: Aktivität, Vollständigkeit der Standard-Unterordner
            (Verträge/Angebote/Meetings/Dokumente) und offene Aufgaben. Notiz und Ampel lassen sich
            manuell überschreiben, wenn die automatische Einschätzung nicht zur Realität passt.
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
                  <TableHead className="w-28">Vollständigkeit</TableHead>
                  <TableHead className="w-32">Offene Aufgaben</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kundenData.kunden.map((k) => (
                  <Fragment key={k.kunde}>
                    <TableRow className={cn(k.archiviert && "opacity-60")}>
                      <TableCell>
                        <span
                          className={cn("inline-block size-2.5 rounded-full", AMPEL_COLOR[k.ampel])}
                          title={
                            k.ampel !== k.ampel_automatisch
                              ? `Manuell gesetzt (automatisch: ${AMPEL_LABEL[k.ampel_automatisch]})`
                              : AMPEL_LABEL[k.ampel]
                          }
                        />
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        {k.kunde}
                        {k.notiz && (
                          <p className="line-clamp-1 text-xs font-normal text-muted-foreground">{k.notiz}</p>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDatum(k.letztes_meeting)}
                        {k.tage_seit_meeting !== null && (
                          <span className="ml-1.5 text-xs">({k.tage_seit_meeting} Tage)</span>
                        )}
                      </TableCell>
                      <TableCell className="tabular-nums">{k.vollstaendigkeit}%</TableCell>
                      <TableCell className="tabular-nums">{k.offene_aufgaben || "–"}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => (editing === k.kunde ? setEditing(null) : startEdit(k))}
                            title="Notiz / Ampel bearbeiten"
                          >
                            <Pencil className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => toggleArchiv(k)}
                            title={k.archiviert ? "Wieder sichtbar machen" : "Archivieren"}
                          >
                            {k.archiviert ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {editing === k.kunde && (
                      <TableRow>
                        <TableCell colSpan={6} className="bg-muted/30">
                          <div className="flex flex-col gap-3 py-2 sm:flex-row sm:items-end">
                            <div className="flex flex-1 flex-col gap-1.5">
                              <span className="text-xs text-muted-foreground">Notiz</span>
                              <Textarea
                                value={notizDraft}
                                onChange={(e) => setNotizDraft(e.target.value)}
                                placeholder="z.B. 'pausiert bis August'"
                                className="min-h-16"
                              />
                            </div>
                            <div className="flex w-full flex-col gap-1.5 sm:w-44">
                              <span className="text-xs text-muted-foreground">Ampel-Override</span>
                              <Select value={ampelDraft} onValueChange={setAmpelDraft}>
                                <SelectTrigger>
                                  <SelectValue>
                                    {(v: string) =>
                                      AMPEL_OVERRIDE_OPTIONS.find((o) => o.value === v)?.label ?? "Automatisch"
                                    }
                                  </SelectValue>
                                </SelectTrigger>
                                <SelectContent>
                                  {AMPEL_OVERRIDE_OPTIONS.map((o) => (
                                    <SelectItem key={o.value} value={o.value}>
                                      {o.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <Button onClick={() => saveEdit(k.kunde)} disabled={meta.isPending}>
                              {meta.isPending ? "Speichere…" : "Speichern"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
