import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { StatusPill } from "@/components/shared/status-pill";
import { cn } from "@/lib/utils";

interface CalendarEvent {
  title: string;
  start: string;
  end?: string;
  location?: string;
  allDay?: boolean;
  type: "meeting" | "deadline";
}

const WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const MONTHS = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

function toKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function eventTime(iso: string): string | null {
  const time = iso.slice(11, 16);
  return time && time !== "00:00" ? time : null;
}

function formatDate(iso: string): string {
  const [date, time] = iso.split("T");
  const [y, m, d] = date.split("-");
  return time && time !== "00:00" ? `${d}.${m}.${y} ${time}` : `${d}.${m}.${y}`;
}

/** Montag-first Rasterkalender: volle Wochen, inkl. Rand-Tage aus Vor-/Folgemonat. */
function buildMonthGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const gridStart = new Date(year, month, 1 - startOffset);
  const days: Date[] = [];
  for (let i = 0; i < 42; i++) {
    days.push(new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i));
  }
  return days;
}

export function CalendarPage() {
  const [view, setView] = useState<"calendar" | "list">("calendar");
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.get<CalendarEvent[]>("/api/calendar"),
    refetchInterval: 5 * 60 * 1000,
  });

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of data ?? []) {
      const key = e.start.slice(0, 10);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(e);
    }
    return map;
  }, [data]);

  const grid = useMemo(() => buildMonthGrid(cursor.getFullYear(), cursor.getMonth()), [cursor]);
  const todayKey = toKey(new Date());

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>
          {view === "calendar" ? `${MONTHS[cursor.getMonth()]} ${cursor.getFullYear()}` : "Kalender"}
        </CardTitle>
        <div className="flex items-center gap-2">
          <Tabs value={view} onValueChange={(v) => v && setView(v as "calendar" | "list")}>
            <TabsList>
              <TabsTrigger value="calendar">Kalender</TabsTrigger>
              <TabsTrigger value="list">Liste</TabsTrigger>
            </TabsList>
          </Tabs>
          {view === "calendar" && (
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCursor(() => {
                  const now = new Date();
                  return new Date(now.getFullYear(), now.getMonth(), 1);
                })}
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
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
        ) : view === "list" ? (
          !data?.length ? (
            <p className="text-sm text-muted-foreground">Keine anstehenden Termine.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-40">Termin</TableHead>
                  <TableHead>Titel</TableHead>
                  <TableHead>Ort</TableHead>
                  <TableHead className="w-28">Typ</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((e, i) => (
                  <TableRow key={i}>
                    <TableCell className="whitespace-nowrap">{formatDate(e.start)}</TableCell>
                    <TableCell>{e.title}</TableCell>
                    <TableCell className="text-muted-foreground">{e.location ?? "-"}</TableCell>
                    <TableCell>
                      <StatusPill variant={e.type === "deadline" ? "danger" : "info"}>
                        {e.type === "deadline" ? "Deadline" : "Termin"}
                      </StatusPill>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )
        ) : (
          <div className="overflow-hidden rounded-2xl border border-border">
            <div className="grid grid-cols-7 border-b border-border bg-muted/40">
              {WEEKDAYS.map((d) => (
                <div key={d} className="px-2 py-2 text-center text-xs font-medium text-muted-foreground">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7">
              {grid.map((date, i) => {
                const key = toKey(date);
                const dayEvents = eventsByDay.get(key) ?? [];
                const isCurrentMonth = date.getMonth() === cursor.getMonth();
                const isToday = key === todayKey;
                const isLastRow = i >= grid.length - 7;
                const visible = dayEvents.slice(0, 3);
                const overflow = dayEvents.length - visible.length;

                return (
                  <div
                    key={key}
                    className={cn(
                      "min-h-24 border-r border-border p-1.5 [&:nth-child(7n)]:border-r-0",
                      !isLastRow && "border-b",
                      !isCurrentMonth && "bg-muted/20"
                    )}
                  >
                    <div
                      className={cn(
                        "mb-1 flex size-6 items-center justify-center rounded-full text-xs",
                        isToday
                          ? "bg-primary font-medium text-primary-foreground"
                          : isCurrentMonth
                            ? "text-foreground"
                            : "text-muted-foreground/50"
                      )}
                    >
                      {date.getDate()}
                    </div>
                    <div className="flex flex-col gap-1">
                      {visible.map((e, idx) => {
                        const time = eventTime(e.start);
                        return (
                          <Tooltip key={idx}>
                            <TooltipTrigger
                              render={
                                <div
                                  className={cn(
                                    "cursor-default truncate rounded-md px-1.5 py-0.5 text-[11px] leading-tight",
                                    e.type === "deadline"
                                      ? "bg-destructive/15 text-destructive"
                                      : "bg-primary/15 text-primary"
                                  )}
                                >
                                  {time ? `${time} ` : ""}
                                  {e.title}
                                </div>
                              }
                            />
                            <TooltipContent>
                              {e.title}
                              {time ? ` · ${time} Uhr` : ""}
                              {e.location ? ` · ${e.location}` : ""}
                            </TooltipContent>
                          </Tooltip>
                        );
                      })}
                      {overflow > 0 && (
                        <div className="px-1.5 text-[10px] text-muted-foreground">+{overflow} weitere</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
