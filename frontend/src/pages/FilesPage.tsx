import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, File, Folder } from "lucide-react";
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

interface TreeNode {
  name: string;
  path: string;
  type: "folder" | "file";
  size?: number;
  url?: string;
  children?: TreeNode[];
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
// Root-Ebene (Kunden, Finanzen, Leads, ...) direkt aufgeklappt zeigen, wie auf
// dem Mac - alles darunter erst auf Klick, sonst ist der erste Eindruck wieder
// eine unübersichtliche Wand aus Ordnern.
const DEFAULT_OPEN_DEPTH = 1;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FolderTree({
  node,
  depth,
  overridden,
  onToggle,
}: {
  node: TreeNode;
  depth: number;
  overridden: Set<string>;
  onToggle: (path: string) => void;
}) {
  if (node.type === "file") {
    return (
      <a
        href={`${API_BASE}${node.url}`}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-muted hover:underline"
        style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        <File className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="flex-1 truncate">{node.name}</span>
        <span className="shrink-0 text-xs text-muted-foreground">{formatSize(node.size ?? 0)}</span>
      </a>
    );
  }

  // Default: Root-Ebene offen, Rest zu. Ein Klick kehrt genau diesen einen
  // Knoten um (egal ob er per Default offen oder zu war).
  const defaultOpen = depth < DEFAULT_OPEN_DEPTH;
  const isOpen = overridden.has(node.path) ? !defaultOpen : defaultOpen;
  const children = node.children ?? [];

  return (
    <div>
      <button
        type="button"
        onClick={() => onToggle(node.path)}
        className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-sm font-medium hover:bg-muted"
        style={{ paddingLeft: `${depth * 1.25}rem` }}
      >
        {isOpen ? (
          <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
        )}
        <Folder className="size-3.5 shrink-0 text-amber-500" />
        <span className="truncate">{node.name}</span>
        <span className="text-xs font-normal text-muted-foreground">({children.length})</span>
      </button>
      {isOpen && (
        <div>
          {children.map((child) => (
            <FolderTree key={child.path} node={child} depth={depth + 1} overridden={overridden} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  );
}

export function FilesPage() {
  const treeQuery = useQuery({
    queryKey: ["files-tree"],
    queryFn: () => api.get<TreeNode>("/api/files/tree"),
  });
  const flatQuery = useQuery({
    queryKey: ["files"],
    queryFn: () => api.get<{ files: VaultFile[] }>("/api/files"),
  });
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("");
  const [uploading, setUploading] = useState(false);
  const [overridden, setOverridden] = useState<Set<string>>(new Set());

  const processInbox = useMutation({
    mutationFn: () => api.post<{ processed?: number; new_indexed?: number }>("/api/inbox_process", {}),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.invalidateQueries({ queryKey: ["files-tree"] });
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
      await queryClient.invalidateQueries({ queryKey: ["files-tree"] });
      toast.success(`${file.name} hochgeladen und verarbeitet`);
    } catch {
      toast.error("Upload fehlgeschlagen");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  function toggle(path: string) {
    setOverridden((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }

  const isSearching = filter.trim().length > 0;
  const filteredFlat = flatQuery.data?.files.filter((f) => f.path.toLowerCase().includes(filter.toLowerCase())) ?? [];

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
        {isSearching ? (
          flatQuery.isLoading ? (
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
                {filteredFlat.slice(0, 300).map((f) => (
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
          )
        ) : treeQuery.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : (
          <div className="space-y-0.5">
            {(treeQuery.data?.children ?? []).map((child) => (
              <FolderTree key={child.path} node={child} depth={0} overridden={overridden} onToggle={toggle} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
