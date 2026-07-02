import { CheckCircle2, ExternalLink } from "lucide-react";
import type { OnboardingEvent } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { AutomationToggles } from "../components/AutomationToggles";
import { StatusChecklist } from "../components/StatusChecklist";
import type { AutomationToggles as TogglesType, CustomerData, ProjectTypeData } from "../types";

interface ReviewStepProps {
  customer: CustomerData;
  project: ProjectTypeData;
  toggles: TogglesType;
  onToggleChange: (toggles: TogglesType) => void;
  confirmed: boolean;
  onConfirmChange: (confirmed: boolean) => void;
  running: boolean;
  events: Record<string, OnboardingEvent>;
  result: { drive_link?: string; github_link?: string } | null;
  runError: string;
  onStart: () => void;
}

const PROJECT_TYPE_LABEL: Record<string, string> = {
  beschaffungsagent: "Beschaffungsagent",
  stuecklistenagent: "Stücklistenagent",
  neues_projekt: "Neues Projekt",
};

export function ReviewStep({
  customer,
  project,
  toggles,
  onToggleChange,
  confirmed,
  onConfirmChange,
  running,
  events,
  result,
  runError,
  onStart,
}: ReviewStepProps) {
  if (running || result) {
    return (
      <div className="flex flex-col gap-4">
        <StatusChecklist toggles={toggles} events={events} />
        {runError && <p className="text-sm text-destructive">{runError}</p>}
        {result && !runError && (
          <Card className="border-emerald-500/30 bg-emerald-500/5">
            <CardContent className="flex flex-col gap-2 pt-6">
              <div className="flex items-center gap-2 text-sm font-medium text-emerald-600">
                <CheckCircle2 className="size-4" />
                Onboarding abgeschlossen
              </div>
              <div className="flex flex-wrap gap-2">
                {result.drive_link && (
                  <Button
                    variant="outline"
                    size="sm"
                    render={
                      <a href={result.drive_link} target="_blank" rel="noreferrer">
                        Drive öffnen <ExternalLink className="size-3.5" />
                      </a>
                    }
                  />
                )}
                {result.github_link && (
                  <Button
                    variant="outline"
                    size="sm"
                    render={
                      <a href={result.github_link} target="_blank" rel="noreferrer">
                        Repo öffnen <ExternalLink className="size-3.5" />
                      </a>
                    }
                  />
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Zusammenfassung</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
          <SummaryRow label="Kunde" value={customer.kundenname} />
          <SummaryRow label="Ansprechpartner" value={`${customer.ansprechpartner_name} (${customer.ansprechpartner_email})`} />
          <SummaryRow label="Projekttyp" value={project.projekttyp ? PROJECT_TYPE_LABEL[project.projekttyp] : "-"} />
          <SummaryRow label="Setup / Monatlich" value={`${customer.setup_preis}€ / ${customer.monatliche_rate}€`} />
          <SummaryRow label="Projektstart" value={customer.projektstart_datum} />
          <SummaryRow label="Dateien" value={`${project.uploadedFiles.length} hochgeladen`} />
          {project.projekttyp !== "neues_projekt" && (
            <SummaryRow label="Features" value={project.features.join(", ") || "-"} />
          )}
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-medium">Automatisierungen</h3>
        <AutomationToggles toggles={toggles} onChange={onToggleChange} hasFiles={project.uploadedFiles.length > 0} />
      </div>

      <div className="flex flex-col gap-3">
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={confirmed} onCheckedChange={(checked) => onConfirmChange(checked === true)} />
          Ich bestätige dass alle Daten korrekt sind
        </label>
        <Button onClick={onStart} disabled={!confirmed} className="self-start">
          Onboarding starten
        </Button>
      </div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border/50 py-1">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
