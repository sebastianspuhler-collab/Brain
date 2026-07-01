import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Task {
  text: string;
  urgency: "urgent" | "soon" | "normal" | "done";
  done?: boolean;
}

const URGENCY_LABEL: Record<Task["urgency"], string> = {
  urgent: "Dringend",
  soon: "Bald",
  normal: "Normal",
  done: "Erledigt",
};

const URGENCY_VARIANT: Record<Task["urgency"], "destructive" | "secondary" | "outline"> = {
  urgent: "destructive",
  soon: "secondary",
  normal: "outline",
  done: "outline",
};

export function TasksPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.get<Task[]>("/api/tasks"),
    refetchInterval: 5 * 60 * 1000,
  });

  const open = data?.filter((t) => !t.done) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Aufgaben</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : open.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine offenen Aufgaben.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Aufgabe</TableHead>
                <TableHead className="w-32">Priorität</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {open.map((t, i) => (
                <TableRow key={i}>
                  <TableCell>{t.text}</TableCell>
                  <TableCell>
                    <Badge variant={URGENCY_VARIANT[t.urgency]}>{URGENCY_LABEL[t.urgency]}</Badge>
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
