// API-Basis: in Produktion läuft alles hinter einem Reverse-Proxy unter derselben
// Origin (kein CORS nötig), im lokalen Dev zeigt VITE_API_BASE auf das FastAPI-Backend.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // FormData bekommt bewusst KEIN Content-Type - der Browser setzt
  // "multipart/form-data; boundary=..." selbst, ein manueller "application/json"-
  // Header hier würde den Multipart-Body für den Server unlesbar machen.
  const isFormData = options.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? body.error ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>(path, { method: "POST", body: form as unknown as BodyInit });
  },
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form as unknown as BodyInit }),
};

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  updated_at: string;
  model: string;
}

export interface ChatSessionData {
  id: string;
  title: string;
  model: string;
  messages: ChatMessage[];
}

/** Chat-Verlauf: Sessions bleiben nach Reload/Neustart erhalten (Ergänzung, kein
 * Ersatz für /api/chat - ohne session_id verhält sich der Chat wie zuvor). */
export const chatSessions = {
  list: () => api.get<ChatSessionSummary[]>("/api/chat/sessions"),
  get: (id: string) => api.get<ChatSessionData>(`/api/chat/sessions/${id}`),
  remove: (id: string) => request<{ ok: boolean }>(`/api/chat/sessions/${id}`, { method: "DELETE" }),
};

export interface Agent {
  id: string;
  name: string;
  system_prompt_zusatz: string;
  ordner_filter: string[];
  model: string | null;
}

/** Eigene benannte Chat-Agenten (Umsetzungsplan-Memo 2026-07-16, Punkt D2) -
 * Ergänzung zum Hauptchat, der ohne agent_id unverändert bleibt. */
export const agents = {
  list: () => api.get<Agent[]>("/api/agents"),
  create: (data: Omit<Agent, "id">) => api.post<Agent>("/api/agents", data),
  update: (id: string, data: Omit<Agent, "id">) => api.put<Agent>(`/api/agents/${id}`, data),
  remove: (id: string) => api.del<{ ok: boolean }>(`/api/agents/${id}`),
};

export interface ChatSource {
  path: string;
  score: number;
}

/** Streamt Chat-Antworten per SSE. onChunk wird für jedes Text-Fragment aufgerufen,
 * onSources (optional) einmalig, sobald die RAG-Suche für diese Antwort feststeht. */
export async function streamChat(
  messages: ChatMessage[],
  model: string,
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  sessionId?: string,
  onSources?: (sources: ChatSource[]) => void,
  agentId?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, model, session_id: sessionId, agent_id: agentId }),
    signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Chat-Anfrage fehlgeschlagen");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      let data: { chunk?: string; error?: string; sources?: ChatSource[] };
      try {
        data = JSON.parse(payload);
      } catch {
        continue; // unvollständiges JSON-Fragment, wird im nächsten Chunk komplettiert
      }
      if (data.error) throw new Error(data.error);
      if (data.sources) onSources?.(data.sources);
      if (data.chunk) onChunk(data.chunk);
    }
  }
}

export interface LinkedInChatEvent {
  chunk?: string;
  state_changed?: boolean;
  error?: string;
}

/** Streamt eine Chat-Antwort für die gesamte LinkedIn-Sektion (Ideen, Posts,
 * Karusselle, Richtung - alles über Tool Use steuerbar). state_changed zeigt
 * an, dass sich Ideen/Posts/Karusselle geändert haben und neu geladen werden sollten. */
export async function streamLinkedInChat(
  messages: ChatMessage[],
  onEvent: (event: LinkedInChatEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/linkedin/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "LinkedIn-Chat-Anfrage fehlgeschlagen");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      try {
        onEvent(JSON.parse(payload));
      } catch {
        continue;
      }
    }
  }
}

export interface OnboardingEvent {
  step: string;
  status: "running" | "done" | "error" | "warning";
  message?: string;
  link?: string;
  drive_link?: string;
  github_link?: string;
}

/** Streamt den Onboarding-Automatisierungslauf per SSE. onEvent wird für jeden Schritt-Status aufgerufen. */
export async function streamOnboarding(form: FormData, onEvent: (event: OnboardingEvent) => void): Promise<void> {
  const res = await fetch(`${API_BASE}/api/onboarding`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? "Onboarding-Anfrage fehlgeschlagen");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        onEvent(JSON.parse(line.slice(6)));
      } catch {
        continue;
      }
    }
  }
}
