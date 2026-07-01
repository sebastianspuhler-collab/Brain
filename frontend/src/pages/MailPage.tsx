import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface Mail {
  id: string;
  from: string;
  email: string;
  subject: string;
  snippet: string;
  time: string;
  unread: boolean;
}

export function MailPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["gmail"],
    queryFn: () => api.get<Mail[]>("/api/gmail"),
    refetchInterval: 60 * 1000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mail</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : !data?.length ? (
          <p className="text-sm text-muted-foreground">Keine E-Mails oder Gmail nicht verbunden.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8"></TableHead>
                <TableHead className="w-44">Von</TableHead>
                <TableHead>Betreff</TableHead>
                <TableHead className="w-20">Zeit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((m) => (
                <TableRow key={m.id} className={m.unread ? "font-medium" : "text-muted-foreground"}>
                  <TableCell>{m.unread && <span className="block h-2 w-2 rounded-full bg-primary" />}</TableCell>
                  <TableCell className="truncate max-w-44">{m.from}</TableCell>
                  <TableCell>
                    <div className="truncate">{m.subject}</div>
                    {m.snippet && <div className="text-xs text-muted-foreground truncate">{m.snippet}</div>}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">{m.time}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
