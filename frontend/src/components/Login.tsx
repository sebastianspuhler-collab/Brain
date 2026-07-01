import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, useAuth } from "@/context/AuthContext";

export function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Zu viele Versuche, bitte kurz warten.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Zugangsdaten falsch.");
      } else {
        // Netzwerk-/CORS-Fehler (Backend nicht erreichbar, falscher VITE_API_BASE,
        // CORS_ORIGIN-Mismatch) landen sonst hier als ApiError mit status 0 oder
        // als generischer TypeError - nicht mit "Zugangsdaten falsch" verwechseln,
        // sonst sieht ein Verbindungsproblem wie ein falsches Passwort aus.
        setError("Server nicht erreichbar. Läuft das Backend? Stimmt VITE_API_BASE?");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Prozessia Brain</CardTitle>
          <p className="text-sm text-muted-foreground">Bitte anmelden</p>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="username">Benutzername</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Passwort</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" disabled={busy || !username || !password} className="w-full">
              {busy ? "..." : "Einloggen"}
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
