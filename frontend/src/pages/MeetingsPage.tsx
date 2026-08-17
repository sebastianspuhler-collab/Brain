import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Download, List, Maximize2 } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DayEventsPopoverContent } from "@/components/shared/day-events-popover";
import { MonthGrid } from "@/components/shared/month-grid";
import { SegmentedControl } from "@/components/shared/segmented-control";
import { StatusPill } from "@/components/shared/status-pill";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

type View = "list" | "calendar";

interface Meeting {
  path: string;
  name: string;
  kunde: string | null;
  datum: string;
  zusammenfassung: string;
  url: string;
  /** Serverseitig aus der .md gerenderter PDF-Download (2026-07-28) - Sebastian
   * will lesbare Transkripte, keine rohe Markdown-Datei im Download. */
  pdf_url: string;
  /** Original-Quelldokument (z.B. .docx), falls im Meeting-Ordner gefunden. */
  original_url: string | null;
}

const MONTHS = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

function formatDatum(datum: string): string {
  if (!datum || datum.length < 10) return datum || "–";
  const [y, m, d] = datum.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

/** Rohe Markdown-Notiz ohne YAML-Frontmatter - für die groß lesbare
 * Volltext-Ansicht zählt der Inhalt, nicht die Metadaten obendrüber. */
function stripFrontmatter(text: string): string {
  return text.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
}

function useMeetingFulltext(path: string | null) {
  return useQuery({
    queryKey: ["meeting-fulltext", path],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/files/download/${encodePath(path as string)}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Transkript konnte nicht geladen werden");
      return stripFrontmatter(await res.text());
    },
    enabled: path !== null,
  });
}

export function MeetingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => api.get<{ meetings: Meeting[] }>("/api/meetings"),
  });
  const [filter, setFilter] = useState("");
  const [kunde, setKunde] = useState("alle");
  const [view, setView] = useState<View>("list");
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [openMeeting, setOpenMeeting] = useState<Meeting | null>(null);
  const { data: fulltext, isLoading: fulltextLoading } = useMeetingFulltext(openMeeting?.path ?? null);

  function expand(e: React.MouseEvent, m: Meeting) {
    e.preventDefault();
    e.stopPropagation();
    setOpenMeeting(m);
  }

  const kunden = useMemo(() => {
    const set = new Set((data?.meetings ?? []).map((m) => m.kunde).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [data]);

  const meetings = (data?.meetings ?? []).filter((m) => {
    if (kunde !== "alle" && m.kunde !== kunde) return false;
    if (!filter) return true;
    const q = filter.toLowerCase();
    return m.name.toLowerCase().includes(q) || m.zusammenfassung.toLowerCase().includes(q);
  });

  const meetingsByDay = useMemo(() => {
    const map = new Map<string, Meeting[]>();
    for (const m of meetings) {
      if (!m.datum) continue;
      const key = m.datum.slice(0, 10);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    return map;
  }, [meetings]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Transkripte</CardTitle>
        <div className="flex items-center gap-2">
          <SegmentedControl
            options={[
              { value: "list", label: "Liste", icon: <List className="size-3.5" /> },
              { value: "calendar", label: "Kalender", icon: <CalendarIcon className="size-3.5" /> },
            ]}
            value={view}
            onChange={setView}
          />
          <Select value={kunde} onValueChange={(v) => v && setKunde(v)}>
            <SelectTrigger size="sm" className="w-40">
              <SelectValue>{(v: string) => (v === "alle" ? "Alle Kunden" : v)}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="alle">Alle Kunden</SelectItem>
              {kunden.map((k) => (
                <SelectItem key={k} value={k}>
                  {k}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input placeholder="Suchen..." value={filter} onChange={(e) => setFilter(e.target.value)} className="w-56" />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : view === "calendar" ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-foreground">
                {MONTHS[cursor.getMonth()]} {cursor.getFullYear()}
              </span>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const now = new Date();
                    setCursor(new Date(now.getFullYear(), now.getMonth(), 1));
                  }}
                >
                  Heute
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Vorheriger Monat"
                  onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() - 1, 1))}
                >
                  <ChevronLeft className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Nächster Monat"
                  onClick={() => setCursor((c) => new Date(c.getFullYear(), c.getMonth() + 1, 1))}
                >
                  <ChevronRight className="size-4" />
                </Button>
              </div>
            </div>
            <MonthGrid
              cursor={cursor}
              itemsByDay={meetingsByDay}
              renderPill={(m, idx) => (
                <div key={idx} className="truncate rounded-md bg-primary/15 px-1.5 py-0.5 text-[11px] leading-tight text-primary">
                  {m.kunde ? `${m.kunde} · ` : ""}
                  {m.name}
                </div>
              )}
              renderPopoverContent={(date, dayMeetings) => (
                <DayEventsPopoverContent
                  date={date}
                  items={dayMeetings}
                  emptyLabel="Keine Transkripte an diesem Tag."
                  renderItem={(m) => (
                    <a
                      href={`${API_BASE}${m.pdf_url}`}
                      target="_blank"
                      rel="noreferrer"
                      className="group flex flex-col gap-0.5 rounded-lg px-2 py-1.5 hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-1.5">
                        {m.kunde && <StatusPill variant="info">{m.kunde}</StatusPill>}
                        <span className="truncate text-sm font-medium text-foreground">{m.name}</span>
                        {m.original_url && (
                          <a
                            href={`${API_BASE}${m.original_url}`}
                            target="_blank"
                            rel="noreferrer"
                            title="Original-Dokument herunterladen"
                            className="ml-auto flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 hover:bg-muted group-hover:opacity-100"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Download className="size-3.5" />
                          </a>
                        )}
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className={m.original_url ? "size-6 shrink-0 opacity-0 group-hover:opacity-100" : "ml-auto size-6 shrink-0 opacity-0 group-hover:opacity-100"}
                          title="Volltext groß anzeigen"
                          onClick={(e) => expand(e, m)}
                        >
                          <Maximize2 className="size-3.5" />
                        </Button>
                      </div>
                      {m.zusammenfassung && (
                        <p className="line-clamp-2 text-xs text-muted-foreground">{m.zusammenfassung}</p>
                      )}
                    </a>
                  )}
                />
              )}
            />
          </div>
        ) : meetings.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Transkripte gefunden.</p>
        ) : (
          <div className="flex flex-col divide-y divide-border">
            {meetings.map((m) => (
              <a
                key={m.path}
                href={`${API_BASE}${m.pdf_url}`}
                target="_blank"
                rel="noreferrer"
                className="group flex flex-col gap-1 py-3 first:pt-0 last:pb-0 hover:bg-muted/40"
              >
                <div className="flex items-center gap-2">
                  <span className="whitespace-nowrap text-xs font-medium text-muted-foreground">
                    {formatDatum(m.datum)}
                  </span>
                  {m.kunde && <StatusPill variant="info">{m.kunde}</StatusPill>}
                  <span className="truncate text-sm font-medium text-foreground">{m.name}</span>
                  {m.original_url && (
                    <a
                      href={`${API_BASE}${m.original_url}`}
                      target="_blank"
                      rel="noreferrer"
                      title="Original-Dokument herunterladen"
                      className="ml-auto flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 hover:bg-muted group-hover:opacity-100"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Download className="size-4" />
                    </a>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className={m.original_url ? "size-7 shrink-0 opacity-0 group-hover:opacity-100" : "ml-auto size-7 shrink-0 opacity-0 group-hover:opacity-100"}
                    title="Volltext groß anzeigen"
                    onClick={(e) => expand(e, m)}
                  >
                    <Maximize2 className="size-4" />
                  </Button>
                </div>
                {m.zusammenfassung && (
                  <p className="line-clamp-2 text-xs text-muted-foreground">{m.zusammenfassung}</p>
                )}
              </a>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={openMeeting !== null} onOpenChange={(open) => !open && setOpenMeeting(null)}>
        <DialogContent className="max-w-3xl">
          {openMeeting && (
            <>
              <DialogHeader>
                <DialogTitle className="text-lg">{openMeeting.name}</DialogTitle>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {formatDatum(openMeeting.datum)}
                  {openMeeting.kunde && <StatusPill variant="info">{openMeeting.kunde}</StatusPill>}
                </div>
              </DialogHeader>
              <DialogBody>
                {fulltextLoading ? (
                  <Skeleton className="h-40 w-full" />
                ) : (
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-foreground">
                    {fulltext || "Kein Inhalt gefunden."}
                  </p>
                )}
              </DialogBody>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
