import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, File, Folder, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError, api } from "@/api/client";
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
// Sebastian, 2026-08-19: default soll alles zu sein, auch die Root-Ebene -
// eine Wand aus offenen Ordnern beim ersten Blick auf /files war ihm zu
// unübersichtlich. Jeder Knoten klappt trotzdem einzeln per Klick auf.
const DEFAULT_OPEN_DEPTH = 0;

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
  uploadingPath,
  onUploadToFolder,
}: {
  node: TreeNode;
  depth: number;
  overridden: Set<string>;
  onToggle: (path: string) => void;
  uploadingPath: string | null;
  onUploadToFolder: (path: string, file: File) => void;
}) {
  if (node.type === "file") {
    return (
      <a
        href={`${API_BASE}${node.url}`}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-muted hover:underline"
        style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        <File className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="flex-1 truncate">{node.name}</span>
        <span className="shrink-0 text-xs text-muted-foreground">{formatSize(node.size ?? 0)}</span>
      </a>
    );
  }

  // Default: alles zu. Ein Klick kehrt genau diesen einen Knoten um (egal ob
  // er per Default offen oder zu war).
  const defaultOpen = depth < DEFAULT_OPEN_DEPTH;
  const isOpen = overridden.has(node.path) ? !defaultOpen : defaultOpen;
  const children = node.children ?? [];
  const isUploadingHere = uploadingPath === node.path;

  return (
    <div>
      <div
        className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium hover:bg-muted"
        style={{ paddingLeft: `${depth * 1.25}rem` }}
      >
        <button type="button" onClick={() => onToggle(node.path)} className="flex flex-1 items-center gap-1.5 text-left">
          {isOpen ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
          )}
          <Folder className="size-3.5 shrink-0 text-amber-500" />
          <span className="truncate">{node.name}</span>
          <span className="text-xs font-normal text-muted-foreground">({children.length})</span>
        </button>
        <label
          title="Datei direkt hier ablegen - ohne KI-Klassifizierung/Umsortierung"
          className="shrink-0 cursor-pointer rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
          onClick={(e) => e.stopPropagation()}
        >
          <Upload className={`size-3.5 ${isUploadingHere ? "animate-pulse" : ""}`} />
          <input
            type="file"
            hidden
            disabled={isUploadingHere}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUploadToFolder(node.path, file);
              e.target.value = "";
            }}
          />
        </label>
      </div>
      {isOpen && (
        <div>
          {children.map((child) => (
            <FolderTree
              key={child.path}
              node={child}
              depth={depth + 1}
              overridden={overridden}
              onToggle={onToggle}
              uploadingPath={uploadingPath}
              onUploadToFolder={onUploadToFolder}
            />
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
  const [uploadingPath, setUploadingPath] = useState<string | null>(null);
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

  // Deterministischer Gegenpart zu handleUpload oben: legt die Datei exakt in
  // den geklickten Ordner, ohne die Inbox-/Klassifizierungs-Pipeline
  // (Sebastian, 2026-08-19: "per Hand Dateien im Brain selber ablegen können,
  // in jedem Ordner").
  async function handleUploadToFolder(folder: string, file: File) {
    setUploadingPath(folder);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("folder", folder);
      await api.postForm("/api/files/upload", form);
      await queryClient.invalidateQueries({ queryKey: ["files"] });
      await queryClient.invalidateQueries({ queryKey: ["files-tree"] });
      toast.success(`${file.name} in ${folder || "Vault-Root"} abgelegt`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.error(err.message);
      } else {
        toast.error("Upload fehlgeschlagen");
      }
    } finally {
      setUploadingPath(null);
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
            title="Wird klassifiziert und automatisch einsortiert"
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
              <FolderTree
                key={child.path}
                node={child}
                depth={0}
                overridden={overridden}
                onToggle={toggle}
                uploadingPath={uploadingPath}
                onUploadToFolder={handleUploadToFolder}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
