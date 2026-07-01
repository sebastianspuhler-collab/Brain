import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface CalendarEvent {
  title: string;
  start: string;
  end?: string;
  location?: string;
  allDay?: boolean;
  type: "meeting" | "deadline";
}

function formatDate(iso: string): string {
  const [date, time] = iso.split("T");
  const [y, m, d] = date.split("-");
  return time && time !== "00:00" ? `${d}.${m}.${y} ${time}` : `${d}.${m}.${y}`;
}

export function CalendarPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.get<CalendarEvent[]>("/api/calendar"),
    refetchInterval: 5 * 60 * 1000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Kalender</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : !data?.length ? (
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
                    <Badge variant={e.type === "deadline" ? "destructive" : "secondary"}>
                      {e.type === "deadline" ? "Deadline" : "Termin"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
