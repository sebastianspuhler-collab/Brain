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
import { DayEventsPopoverContent } from "@/components/shared/day-events-popover";
import { MonthGrid } from "@/components/shared/month-grid";
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

const MONTHS = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

function eventTime(iso: string): string | null {
  const time = iso.slice(11, 16);
  return time && time !== "00:00" ? time : null;
}

function formatDate(iso: string): string {
  const [date, time] = iso.split("T");
  const [y, m, d] = date.split("-");
  return time && time !== "00:00" ? `${d}.${m}.${y} ${time}` : `${d}.${m}.${y}`;
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
          <MonthGrid
            cursor={cursor}
            itemsByDay={eventsByDay}
            renderPill={(e, idx) => {
              const time = eventTime(e.start);
              return (
                <Tooltip key={idx}>
                  <TooltipTrigger
                    render={
                      <div
                        className={cn(
                          "cursor-default truncate rounded-md px-1.5 py-0.5 text-[11px] leading-tight",
                          e.type === "deadline" ? "bg-destructive/15 text-destructive" : "bg-primary/15 text-primary"
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
            }}
            renderPopoverContent={(date, dayEvents) => (
              <DayEventsPopoverContent
                date={date}
                items={dayEvents}
                emptyLabel="Keine Termine an diesem Tag."
                renderItem={(e) => {
                  const time = eventTime(e.start);
                  return (
                    <div className="flex items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/50">
                      <span
                        className={cn(
                          "mt-1 size-1.5 shrink-0 rounded-full",
                          e.type === "deadline" ? "bg-destructive" : "bg-primary"
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm text-foreground">{e.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {time ? `${time} Uhr` : "Ganztägig"}
                          {e.location ? ` · ${e.location}` : ""}
                        </div>
                      </div>
                    </div>
                  );
                }}
              />
            )}
          />
        )}
      </CardContent>
    </Card>
  );
}
