import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedControl } from "@/components/shared/segmented-control";

const THEME_OPTIONS = [
  { value: "light" as const, label: "Hell" },
  { value: "dark" as const, label: "Dunkel" },
];

export function SettingsPage() {
  const { theme, setTheme } = useTheme();
  // next-themes liest den gespeicherten Wert erst nach dem ersten Render aus
  // localStorage - vor dem Mount zeigen wir den Default (hell) statt kurz
  // "undefined" an die SegmentedControl durchzureichen.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Darstellung</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-3 text-sm text-muted-foreground">
            Hell ist der Standard. Dunkel entspricht dem bisherigen Prozessia-Look.
          </p>
          <SegmentedControl
            options={THEME_OPTIONS}
            value={mounted ? (theme === "dark" ? "dark" : "light") : "light"}
            onChange={setTheme}
          />
        </CardContent>
      </Card>
    </div>
  );
}
