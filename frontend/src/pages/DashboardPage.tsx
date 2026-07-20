import { Fragment, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Archive, ArchiveRestore, Pencil, RefreshCw, TriangleAlert } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type Status = "neuer_kontakt" | "erstgespraech" | "angebotsphase" | "auftrag" | "fulfillment" | "abgeschlossen";
type Sicherheit = "hoch" | "mittel" | "niedrig";

interface Eintrag {
  kunde: string;
  anzeige_name: string;
  typ: "kunde" | "lead";
  letztes_meeting: string | null;
  tage_seit_meeting: number | null;
  status: Status;
  status_automatisch: Status;
  sicherheit: Sicherheit;
  begruendung: string;
  quellen: string[];
  warnsignal: string | null;
  ist_relevant: boolean;
  relevanz_begruendung: string;
  offene_aufgaben: number;
  vollstaendigkeit: number | null;
  aktueller_stand: string;
  naechster_termin: { titel: string; start: string } | null;
  archiviert: boolean;
  notiz: string;
}

interface LinkedInStatus {
  geplante_posts: number;
  gepushte_posts: number;
  offene_ideen: number;
  naechster_post: { termin: string; idee: string } | null;
}

// Vertriebs-Pipeline statt Aktivitäts-Ampel (Sebastian, 2026-07-19: eine Ampel
// nach Aktivitäts-Recency sagt nichts über den echten Vertriebsstand). Nur die
// ersten vier Stufen werden automatisch aus Ordnerinhalten abgeleitet (siehe
// dashboard.py:_status_automatisch_kunde) - "fulfillment"/"abgeschlossen"
// lassen sich aus Dateipräsenz allein nicht verlässlich erkennen und sind nur
// über den manuellen Override erreichbar.
const STATUS_ORDER: Status[] = [
  "neuer_kontakt", "erstgespraech", "angebotsphase", "auftrag", "fulfillment", "abgeschlossen",
];
const STATUS_LABEL: Record<Status, string> = {
  neuer_kontakt: "Neuer Kontakt",
  erstgespraech: "Erstgespräch",
  angebotsphase: "Angebotsphase",
  auftrag: "Auftrag",
  fulfillment: "Fulfillment",
  abgeschlossen: "Abgeschlossen",
};
const STATUS_COLOR: Record<Status, string> = {
  neuer_kontakt: "bg-muted text-muted-foreground",
  erstgespraech: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
  angebotsphase: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  auftrag: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  fulfillment: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  abgeschlossen: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
};
const STATUS_OVERRIDE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Automatisch" },
  ...STATUS_ORDER.map((s) => ({ value: s, label: STATUS_LABEL[s] })),
];

// Sicherheit der automatischen Einschätzung (kunden_status_service.py) - bewusst
// sichtbar statt versteckt, damit "niedrig" (z.B. widersprüchliche Belege oder
// eine vom LLM zitierte, nicht existierende Quelle) auffällt statt unterzugehen.
const SICHERHEIT_DOT: Record<Sicherheit, string> = {
  hoch: "bg-emerald-500",
  mittel: "bg-amber-500",
  niedrig: "bg-red-500",
};
const SICHERHEIT_LABEL: Record<Sicherheit, string> = {
  hoch: "hohe Sicherheit",
  mittel: "mittlere Sicherheit",
  niedrig: "niedrige Sicherheit",
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

function StatusBadge({ eintrag }: { eintrag: Eintrag }) {
  const manuell = eintrag.status !== eintrag.status_automatisch;
  const titelTeile = [
    manuell ? `Manuell gesetzt (automatisch: ${STATUS_LABEL[eintrag.status_automatisch]})` : null,
    `${SICHERHEIT_LABEL[eintrag.sicherheit]}${eintrag.begruendung ? ": " + eintrag.begruendung : ""}`,
    eintrag.quellen.length ? `Quellen: ${eintrag.quellen.join(", ")}` : null,
  ].filter(Boolean);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium", STATUS_COLOR[eintrag.status])}
        title={titelTeile.join("\n")}
      >
        {STATUS_LABEL[eintrag.status]}
        {manuell && " *"}
      </span>
      <span
        className={cn("size-1.5 rounded-full", SICHERHEIT_DOT[eintrag.sicherheit])}
        title={SICHERHEIT_LABEL[eintrag.sicherheit]}
      />
      {eintrag.warnsignal && (
        <span title={eintrag.warnsignal}>
          <TriangleAlert
            className="size-3.5 shrink-0 text-amber-600 dark:text-amber-400"
            aria-label={eintrag.warnsignal}
          />
        </span>
      )}
    </span>
  );
}

function useKundenMeta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      kunde: string;
      body: {
        archiviert?: boolean;
        status_override?: string;
        notiz?: string;
        overrides?: Record<string, string>;
      };
    }) => api.post(`/api/dashboard/kunden/${encodeURIComponent(vars.kunde)}/meta`, vars.body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard-kunden-status"] }),
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });
}

function useKundenNeuBewerten() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kunde: string) => api.post(`/api/dashboard/kunden/${encodeURIComponent(kunde)}/neu-bewerten`, {}),
    onSuccess: (_data, kunde) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-kunden-status"] });
      toast.success(`${kunde} neu bewertet`);
    },
    onError: () => toast.error("Neubewertung fehlgeschlagen"),
  });
}

export function DashboardPage() {
  const [zeigeArchivierte, setZeigeArchivierte] = useState(false);
  const [zeigeIrrelevante, setZeigeIrrelevante] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [notizDraft, setNotizDraft] = useState("");
  const [statusDraft, setStatusDraft] = useState("");
  const [nameDraft, setNameDraft] = useState("");
  const [standDraft, setStandDraft] = useState("");

  const { data: kundenData, isLoading: kundenLoading } = useQuery({
    queryKey: ["dashboard-kunden-status", zeigeArchivierte, zeigeIrrelevante],
    queryFn: () =>
      api.get<{ kunden: Eintrag[] }>(
        `/api/dashboard/kunden-status?zeige_archivierte=${zeigeArchivierte}&zeige_irrelevante=${zeigeIrrelevante}`,
      ),
  });
  const { data: li, isLoading: liLoading } = useQuery({
    queryKey: ["dashboard-linkedin-status"],
    queryFn: () => api.get<LinkedInStatus>("/api/dashboard/linkedin-status"),
  });

  const meta = useKundenMeta();
  const neuBewerten = useKundenNeuBewerten();

  function startEdit(e: Eintrag) {
    setEditing(e.kunde);
    setNotizDraft(e.notiz);
    setStatusDraft(e.status !== e.status_automatisch ? e.status : "");
    setNameDraft(e.anzeige_name !== e.kunde ? e.anzeige_name : "");
    setStandDraft(e.aktueller_stand);
  }

  function saveEdit(kunde: string) {
    meta.mutate(
      {
        kunde,
        body: {
          notiz: notizDraft,
          status_override: statusDraft,
          overrides: { anzeige_name: nameDraft, aktueller_stand: standDraft },
        },
      },
      { onSuccess: () => setEditing(null) },
    );
  }

  function toggleArchiv(e: Eintrag) {
    meta.mutate(
      { kunde: e.kunde, body: { archiviert: !e.archiviert } },
      {
        onSuccess: () => {
          toast.success(e.archiviert ? `${e.kunde} wieder sichtbar` : `${e.kunde} archiviert`);
          if (editing === e.kunde) setEditing(null);
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
          <CardTitle>Kunden &amp; Interessenten</CardTitle>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Archivierte anzeigen</span>
              <Switch checked={zeigeArchivierte} onCheckedChange={(c) => setZeigeArchivierte(c === true)} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Irrelevante anzeigen</span>
              <Switch checked={zeigeIrrelevante} onCheckedChange={(c) => setZeigeIrrelevante(c === true)} />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">
            Kunden (Kunden/) und echte Einzel-Interessenten (Leads/, ohne Massen-Kontaktlisten) in
            einer Ansicht. Der Status wird automatisch aus allen Unterlagen (E-Mails, Dokumenten,
            Meeting-Mitschriften) hergeleitet, nicht nur aus Ordner-Anwesenheit - der Punkt neben dem
            Status zeigt die Sicherheit dieser Einschätzung (grün/gelb/rot), ein ⚠ ein erkanntes
            Warnsignal. Einträge, bei denen die KI keine echte Kunden-/Interessenten-Beziehung erkennt
            (z.B. ein Lieferant oder eine private Notiz im falschen Ordner), werden automatisch
            ausgeblendet - über "Irrelevante anzeigen" sichtbar machen. Die Notiz fließt zusätzlich als
            Hinweis in die Bewertung ein. Status, Anzeigename, Aktueller Stand und Notiz lassen sich
            jederzeit manuell überschreiben (mit * markiert), und mit dem Neu-bewerten-Button lässt sich
            die Einschätzung sofort aktualisieren, statt auf die nächste Dateiänderung zu warten.
          </p>
          {kundenLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : !kundenData?.kunden.length ? (
            <p className="text-sm text-muted-foreground">Keine Kunden/Interessenten gefunden.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Letzte Aktivität</TableHead>
                  <TableHead>Nächster Termin</TableHead>
                  <TableHead>Aktueller Stand</TableHead>
                  <TableHead className="w-24">Vollständig</TableHead>
                  <TableHead className="w-16">Aufgaben</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kundenData.kunden.map((e) => (
                  <Fragment key={e.kunde}>
                    <TableRow
                      className={cn(
                        (e.archiviert || !e.ist_relevant) && "opacity-60",
                        !e.ist_relevant && "border-l-2 border-dashed border-destructive/40",
                      )}
                    >
                      <TableCell>
                        <StatusBadge eintrag={e} />
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        <span title={e.anzeige_name !== e.kunde ? `Ordner/Datei: ${e.kunde}` : undefined}>
                          {e.anzeige_name}
                        </span>
                        <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                          {e.typ === "lead" ? "· Interessent" : ""}
                        </span>
                        {!e.ist_relevant && (
                          <p
                            className="line-clamp-1 text-xs font-normal text-destructive"
                            title={e.relevanz_begruendung}
                          >
                            ⚠ wahrscheinlich kein echter Kunde{e.relevanz_begruendung ? `: ${e.relevanz_begruendung}` : ""}
                          </p>
                        )}
                        {e.notiz && (
                          <p className="line-clamp-1 text-xs font-normal text-muted-foreground">{e.notiz}</p>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDatum(e.letztes_meeting)}
                        {e.tage_seit_meeting !== null && (
                          <span className="ml-1.5 text-xs">({e.tage_seit_meeting} Tage)</span>
                        )}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {e.naechster_termin ? (
                          <>
                            {formatTermin(e.naechster_termin.start)}
                            <p className="line-clamp-1 text-xs">{e.naechster_termin.titel}</p>
                          </>
                        ) : (
                          "–"
                        )}
                      </TableCell>
                      <TableCell className="max-w-52 truncate text-muted-foreground" title={e.aktueller_stand}>
                        {e.aktueller_stand || "–"}
                      </TableCell>
                      <TableCell className="tabular-nums">
                        {e.vollstaendigkeit === null ? "–" : `${e.vollstaendigkeit}%`}
                      </TableCell>
                      <TableCell className="tabular-nums">{e.offene_aufgaben || "–"}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => neuBewerten.mutate(e.kunde)}
                            disabled={neuBewerten.isPending}
                            title="Status jetzt neu bewerten (z.B. nach einem Telefonat)"
                          >
                            <RefreshCw className={cn("size-4", neuBewerten.isPending && "animate-spin")} />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => (editing === e.kunde ? setEditing(null) : startEdit(e))}
                            title="Notiz / Status bearbeiten"
                          >
                            <Pencil className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => toggleArchiv(e)}
                            title={e.archiviert ? "Wieder sichtbar machen" : "Archivieren"}
                          >
                            {e.archiviert ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {editing === e.kunde && (
                      <TableRow>
                        <TableCell colSpan={8} className="bg-muted/30">
                          <div className="flex flex-col gap-3 py-2 sm:flex-row sm:items-end sm:flex-wrap">
                            <div className="flex w-full flex-col gap-1.5 sm:w-44">
                              <span className="text-xs text-muted-foreground">Anzeigename</span>
                              <Input
                                value={nameDraft}
                                onChange={(ev) => setNameDraft(ev.target.value)}
                                placeholder={e.kunde}
                              />
                            </div>
                            <div className="flex w-full flex-col gap-1.5 sm:w-56">
                              <span className="text-xs text-muted-foreground">Aktueller Stand</span>
                              <Input
                                value={standDraft}
                                onChange={(ev) => setStandDraft(ev.target.value)}
                                placeholder="z.B. 'wartet auf Feedback zum Angebot'"
                              />
                            </div>
                            <div className="flex flex-1 flex-col gap-1.5">
                              <span className="text-xs text-muted-foreground">Notiz</span>
                              <Textarea
                                value={notizDraft}
                                onChange={(ev) => setNotizDraft(ev.target.value)}
                                placeholder="z.B. 'pausiert bis August'"
                                className="min-h-16"
                              />
                            </div>
                            <div className="flex w-full flex-col gap-1.5 sm:w-48">
                              <span className="text-xs text-muted-foreground">Status-Override</span>
                              <Select value={statusDraft} onValueChange={(v) => setStatusDraft(v ?? "")}>
                                <SelectTrigger>
                                  <SelectValue>
                                    {(v: string) =>
                                      STATUS_OVERRIDE_OPTIONS.find((o) => o.value === v)?.label ?? "Automatisch"
                                    }
                                  </SelectValue>
                                </SelectTrigger>
                                <SelectContent>
                                  {STATUS_OVERRIDE_OPTIONS.map((o) => (
                                    <SelectItem key={o.value} value={o.value}>
                                      {o.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <Button onClick={() => saveEdit(e.kunde)} disabled={meta.isPending}>
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
