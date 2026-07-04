import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface VaultFile {
  path: string;
  name: string;
  size: number;
  url: string;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FilesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["files"],
    queryFn: () => api.get<{ files: VaultFile[] }>("/api/files"),
  });
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");
  const [uploading, setUploading] = useState(false);

  const processInbox = useMutation({
    mutationFn: () => api.post<{ processed?: number; new_indexed?: number }>("/api/inbox_process", {}),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      toast.success(`Inbox verarbeitet: ${data.processed ?? 0} Datei(en), ${data.new_indexed ?? 0} neu indiziert`);
    },
    onError: () => toast.error("Inbox-Verarbeitung fehlgeschlagen"),
  });

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.upload("/api/upload", file);
      await queryClient.invalidateQueries({ queryKey: ["files"] });
      toast.success(`${file.name} hochgeladen und verarbeitet`);
    } catch {
      toast.error("Upload fehlgeschlagen");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  const files = data?.files.filter((f) => f.path.toLowerCase().includes(filter.toLowerCase())) ?? [];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle>Dateien</CardTitle>
        <div className="flex items-center gap-2">
          <Input placeholder="Suchen..." value={filter} onChange={(e) => setFilter(e.target.value)} className="w-56" />
          <Button
            variant="outline"
            onClick={() => processInbox.mutate()}
            disabled={processInbox.isPending}
          >
            {processInbox.isPending ? "..." : "Inbox verarbeiten"}
          </Button>
          <Button
            variant="outline"
            disabled={uploading}
            render={
              <label>
                {uploading ? "..." : "Hochladen"}
                <input type="file" hidden onChange={handleUpload} disabled={uploading} />
              </label>
            }
          />
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pfad</TableHead>
                <TableHead className="w-24">Größe</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {files.slice(0, 300).map((f) => (
                <TableRow key={f.path}>
                  <TableCell>
                    <a href={`${API_BASE}${f.url}`} target="_blank" rel="noreferrer" className="hover:underline">
                      {f.path}
                    </a>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatSize(f.size)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
