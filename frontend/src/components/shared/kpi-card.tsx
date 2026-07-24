import { TrendingDown, TrendingUp } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export interface KpiCardProps {
  label: string
  value: string
  /** z.B. "+12,5%" — nur setzen, wenn ein echter Vorzeitraum-Vergleich vorliegt. */
  trendLabel?: string
  trend?: "up" | "down"
  /** Fette Zeile im Footer, z.B. "9% mehr als im Vorzeitraum". */
  headline?: string
  /** Gedämpfte Zeile unter der Headline, z.B. "Letzte 30 Tage". */
  description?: string
  className?: string
}

export function KpiCard({
  label,
  value,
  trendLabel,
  trend = "up",
  headline,
  description,
  className,
}: KpiCardProps) {
  const TrendIcon = trend === "down" ? TrendingDown : TrendingUp

  return (
    <Card className={cn("relative", className)}>
      <CardContent>
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-foreground sm:text-3xl">
          {value}
        </div>
        {trendLabel && (
          <span
            className={cn(
              "absolute right-4 top-4 flex items-center gap-1 rounded-lg border px-2 py-0.5 text-xs font-medium",
              trend === "down"
                ? "border-destructive/30 text-destructive"
                : "border-emerald-500/30 text-emerald-400"
            )}
          >
            <TrendIcon className="h-3 w-3" />
            {trendLabel}
          </span>
        )}
        {(headline || description) && (
          <div className="mt-3 space-y-0.5 text-sm">
            {headline && (
              <div className="flex items-center gap-1.5 font-medium text-foreground">
                {headline}
                <TrendIcon className="h-4 w-4 text-muted-foreground" />
              </div>
            )}
            {description && <div className="text-muted-foreground">{description}</div>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
