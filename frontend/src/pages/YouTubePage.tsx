import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Video {
  filename: string;
  original_name: string;
  size: number;
  uploaded_at: string;
  title: string;
  description: string;
  category_id: string;
  privacy: string;
  topic: string;
  pushed: boolean;
  post_id: string | null;
  scheduled_at: string | null;
  error: string | null;
}

function formatSize(bytes: number) {
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

function VideoCard({ video }: { video: Video }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(video.title);
  const [description, setDescription] = useState(video.description);
  const [topic, setTopic] = useState(video.topic);
  const [categoryId, setCategoryId] = useState(video.category_id);
  const [privacy, setPrivacy] = useState(video.privacy);
  const [scheduledAt, setScheduledAt] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["yt-videos"] });

  const generateMeta = useMutation({
    mutationFn: () =>
      api.post<{ ok?: boolean; title?: string; description?: string; error?: string }>(
        "/api/youtube/generate-metadata",
        { filename: video.filename, topic }
      ),
    onSuccess: (data) => {
      if (data.ok) {
        setTitle(data.title ?? "");
        setDescription(data.description ?? "");
        toast.success("Titel + Beschreibung generiert");
      } else {
        toast.error(data.error ?? "Generierung fehlgeschlagen");
      }
    },
    onError: () => toast.error("Generierung fehlgeschlagen"),
  });

  const saveMeta = useMutation({
    mutationFn: () =>
      api.post("/api/youtube/metadata", {
        filename: video.filename, title, description, category_id: categoryId, privacy, topic,
      }),
    onSuccess: () => {
      invalidate();
      toast.success("Gespeichert");
    },
    onError: () => toast.error("Speichern fehlgeschlagen"),
  });

  const pushBuffer = useMutation({
    mutationFn: () =>
      api.post<{ ok?: boolean; error?: unknown }>("/api/youtube/push-buffer", {
        filename: video.filename, scheduled_at: scheduledAt || null,
      }),
    onSuccess: (data) => {
      if (data.ok) {
        toast.success("Video in Buffer eingeplant");
        invalidate();
      } else {
        toast.error("Buffer-Fehler: " + JSON.stringify(data.error));
      }
    },
    onError: () => toast.error("Push fehlgeschlagen"),
  });

  const deleteVideo = async () => {
    try {
      await fetch(`${(import.meta.env.VITE_API_BASE ?? "")}/api/youtube/videos/${video.filename}`, {
        method: "DELETE",
        credentials: "include",
      });
      invalidate();
      toast.success("Video gelöscht");
    } catch {
      toast.error("Löschen fehlgeschlagen");
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 space-y-0">
        <div className="min-w-0">
          <CardTitle className="truncate text-sm">{video.original_name}</CardTitle>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={video.pushed ? "default" : "outline"} className="text-xs">
              {video.pushed ? "in Buffer" : "offen"}
            </Badge>
            <span className="text-xs text-muted-foreground">{formatSize(video.size)}</span>
          </div>
        </div>
        <Button size="sm" variant="ghost" onClick={deleteVideo}>Löschen</Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {video.error && (
          <p className="text-xs text-destructive">Letzter Fehler: {video.error}</p>
        )}
        <div className="flex items-center gap-2">
          <Input
            placeholder="Stichpunkte zum Videoinhalt (für Claude)"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="text-sm"
          />
          <Button size="sm" variant="outline" onClick={() => generateMeta.mutate()} disabled={generateMeta.isPending || !topic.trim()}>
            {generateMeta.isPending ? "..." : "Titel schreiben"}
          </Button>
        </div>
        <Input
          placeholder="Titel (max. 100 Zeichen)"
          value={title}
          maxLength={100}
          onChange={(e) => setTitle(e.target.value)}
          className="text-sm font-medium"
        />
        <Textarea
          placeholder="Beschreibung…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="min-h-24 text-sm"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Select value={categoryId} onValueChange={(v) => v && setCategoryId(v as string)}>
            <SelectTrigger className="w-44" size="sm">
              <SelectValue>{(v: string) => v}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="28">Wissenschaft & Technik</SelectItem>
              <SelectItem value="27">Bildung</SelectItem>
              <SelectItem value="22">Blogs & Menschen</SelectItem>
              <SelectItem value="26">How-to & Style</SelectItem>
              <SelectItem value="24">Unterhaltung</SelectItem>
            </SelectContent>
          </Select>
          <Select value={privacy} onValueChange={(v) => v && setPrivacy(v as string)}>
            <SelectTrigger className="w-32" size="sm">
              <SelectValue>{(v: string) => v}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="public">Öffentlich</SelectItem>
              <SelectItem value="unlisted">Nicht gelistet</SelectItem>
              <SelectItem value="private">Privat</SelectItem>
            </SelectContent>
          </Select>
          <Input
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="w-48 text-xs"
            title="Zeitpunkt (leer = nächster freier Slot)"
          />
          <Button size="sm" variant="outline" onClick={() => saveMeta.mutate()} disabled={saveMeta.isPending}>
            Speichern
          </Button>
          <Button
            size="sm"
            onClick={() => pushBuffer.mutate()}
            disabled={pushBuffer.isPending || !title.trim() || video.pushed}
          >
            {pushBuffer.isPending ? "Pushe…" : video.pushed ? "Bereits gepusht" : "In Buffer pushen"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function YouTubePage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const videosQuery = useQuery({
    queryKey: ["yt-videos"],
    queryFn: () => api.get<{ videos: Video[] }>("/api/youtube/videos"),
  });

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await api.upload("/api/youtube/upload", file);
      }
      queryClient.invalidateQueries({ queryKey: ["yt-videos"] });
      toast.success("Video hochgeladen");
    } catch {
      toast.error("Upload fehlgeschlagen");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFileSelect(e.dataTransfer.files);
        }}
      >
        <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <p className="text-sm text-muted-foreground">
            NotebookLM-Video hierher ziehen oder auswählen
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/x-m4v"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
          <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? "Lädt hoch…" : "Video auswählen"}
          </Button>
        </CardContent>
      </Card>

      {!videosQuery.data?.videos.length ? (
        <p className="text-sm text-muted-foreground">Noch keine Videos hochgeladen.</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {videosQuery.data.videos.map((v) => (
            <VideoCard key={v.filename} video={v} />
          ))}
        </div>
      )}
    </div>
  );
}
