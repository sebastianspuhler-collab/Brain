import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusPill } from "@/components/shared/status-pill";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

interface Meeting {
  path: string;
  name: string;
  kunde: string | null;
  datum: string;
  zusammenfassung: string;
  url: string;
}

function formatDatum(datum: string): string {
  if (!datum || datum.length < 10) return datum || "–";
  const [y, m, d] = datum.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

export function MeetingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => api.get<{ meetings: Meeting[] }>("/api/meetings"),
  });
  const [filter, setFilter] = useState("");
  const [kunde, setKunde] = useState("alle");

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

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Meeting Cockpit</CardTitle>
        <div className="flex items-center gap-2">
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
        ) : meetings.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Meeting-Notizen gefunden.</p>
        ) : (
          <div className="flex flex-col divide-y divide-border">
            {meetings.map((m) => (
              <a
                key={m.path}
                href={`${API_BASE}${m.url}`}
                target="_blank"
                rel="noreferrer"
                className="flex flex-col gap-1 py-3 first:pt-0 last:pb-0 hover:bg-muted/40"
              >
                <div className="flex items-center gap-2">
                  <span className="whitespace-nowrap text-xs font-medium text-muted-foreground">
                    {formatDatum(m.datum)}
                  </span>
                  {m.kunde && <StatusPill variant="info">{m.kunde}</StatusPill>}
                  <span className="truncate text-sm font-medium text-foreground">{m.name}</span>
                </div>
                {m.zusammenfassung && (
                  <p className="line-clamp-2 text-xs text-muted-foreground">{m.zusammenfassung}</p>
                )}
              </a>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
