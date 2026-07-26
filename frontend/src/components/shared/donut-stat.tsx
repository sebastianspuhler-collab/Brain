import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface DonutSegment {
  label: string;
  value: number;
  /** Optionale feste Farbe (z.B. dieselbe wie eine StatusPill-Variante) - fehlt
   * sie, wird der Reihe nach aus der Chart-Palette (--chart-1…5) gewählt. */
  color?: string;
}

// Port von adrise-ai (packages/ui/src/components/DonutStat.tsx) - Pie/Cell/
// ResponsiveContainer, Summe in der Donut-Mitte, Legende daneben. --ad-*-Tokens
// durch Brains eigene --chart-*-Tokens ersetzt (Umsetzungsplan 2026-07-26).
const PALETTE = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

export function DonutStat({
  title,
  segments,
  totalLabel = "gesamt",
}: {
  title?: string;
  segments: DonutSegment[];
  totalLabel?: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);

  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent className="flex items-center gap-6">
        <div className="relative h-32 w-32 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={segments} dataKey="value" nameKey="label" innerRadius={42} outerRadius={58} paddingAngle={2}>
                {segments.map((segment, index) => (
                  <Cell key={segment.label} fill={segment.color ?? PALETTE[index % PALETTE.length]} stroke="none" />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-xl font-semibold text-foreground">{total}</span>
            <span className="text-[10px] text-muted-foreground">{totalLabel}</span>
          </div>
        </div>
        <ul className="flex-1 space-y-1.5">
          {segments.map((segment, index) => (
            <li key={segment.label} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-2 text-muted-foreground">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ background: segment.color ?? PALETTE[index % PALETTE.length] }}
                />
                <span className="truncate">{segment.label}</span>
              </span>
              <span className="shrink-0 font-mono text-xs tabular-nums text-foreground">
                {segment.value}
                {total > 0 && <span className="text-muted-foreground"> ({Math.round((segment.value / total) * 100)}%)</span>}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
