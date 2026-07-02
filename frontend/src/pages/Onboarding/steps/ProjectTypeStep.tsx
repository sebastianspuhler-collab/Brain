import { Loader2, Package, PackageCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { FeatureCard } from "../components/FeatureCard";
import { FileUploadZone } from "../components/FileUploadZone";
import {
  BESCHAFFUNGSAGENT_FEATURES,
  STUECKLISTENAGENT_FEATURES,
  type AiAnalysis,
  type ProjectType,
  type ProjectTypeData,
} from "../types";

const PROJECT_TYPES: { value: ProjectType; label: string; description: string; icon: typeof Package }[] = [
  { value: "beschaffungsagent", label: "Beschaffungsagent", description: "Fork des Standard-Produkts inkl. Feature-Auswahl", icon: Package },
  { value: "stuecklistenagent", label: "Stücklistenagent", description: "Fork des Standard-Produkts inkl. Feature-Auswahl", icon: PackageCheck },
  { value: "neues_projekt", label: "Neues Projekt", description: "Individuallösung, KI analysiert Dokumente + Beschreibung", icon: Sparkles },
];

interface ProjectTypeStepProps {
  data: ProjectTypeData;
  onChange: (patch: Partial<ProjectTypeData>) => void;
  onUpdateAnalysis: (patch: Partial<AiAnalysis>) => void;
  analyzing: boolean;
  analyzeError: string;
  onAnalyze: () => void;
}

export function ProjectTypeStep({ data, onChange, onUpdateAnalysis, analyzing, analyzeError, onAnalyze }: ProjectTypeStepProps) {
  const featureList = data.projekttyp === "beschaffungsagent" ? BESCHAFFUNGSAGENT_FEATURES : STUECKLISTENAGENT_FEATURES;

  function toggleFeature(feature: string) {
    const active = data.features.includes(feature);
    onChange({ features: active ? data.features.filter((f) => f !== feature) : [...data.features, feature] });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-3">
        {PROJECT_TYPES.map((type) => {
          const active = data.projekttyp === type.value;
          const Icon = type.icon;
          return (
            <button
              key={type.value}
              type="button"
              onClick={() =>
                onChange({
                  projekttyp: type.value,
                  // Feature-Toggles starten alle AN (siehe Spec), nur bei "Neues Projekt"
                  // gibt es keine feste Feature-Liste - die kommt erst aus der KI-Analyse.
                  features:
                    type.value === "beschaffungsagent"
                      ? [...BESCHAFFUNGSAGENT_FEATURES]
                      : type.value === "stuecklistenagent"
                        ? [...STUECKLISTENAGENT_FEATURES]
                        : [],
                })
              }
              className={cn(
                "flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition",
                active ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"
              )}
            >
              <Icon className={cn("size-5", active ? "text-primary" : "text-muted-foreground")} />
              <div className="text-sm font-medium">{type.label}</div>
              <div className="text-xs text-muted-foreground">{type.description}</div>
            </button>
          );
        })}
      </div>

      {(data.projekttyp === "beschaffungsagent" || data.projekttyp === "stuecklistenagent") && (
        <div className="flex flex-col gap-3">
          <Label>Features</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            {featureList.map((feature) => (
              <FeatureCard key={feature} label={feature} active={data.features.includes(feature)} onToggle={() => toggleFeature(feature)} />
            ))}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="neue_funktion">Neue Funktion beschreiben (optional)</Label>
            <Textarea
              id="neue_funktion"
              value={data.neue_funktion}
              onChange={(e) => onChange({ neue_funktion: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      )}

      {data.projekttyp === "neues_projekt" && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="projektbeschreibung">
              Projektbeschreibung <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="projektbeschreibung"
              value={data.projektbeschreibung}
              onChange={(e) => onChange({ projektbeschreibung: e.target.value })}
              rows={4}
            />
          </div>

          <FileUploadZone
            files={data.uploadedFiles}
            onChange={(files) => onChange({ uploadedFiles: files })}
            label="Angebote, Meeting-Notes, Spezifikationen hierher ziehen"
          />

          <Button
            type="button"
            onClick={onAnalyze}
            disabled={analyzing || !data.projektbeschreibung.trim()}
            className="self-start"
          >
            {analyzing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            {analyzing ? "Analysiere..." : "Mit KI analysieren"}
          </Button>
          {analyzeError && <p className="text-sm text-destructive">{analyzeError}</p>}

          {data.aiAnalysis && <AiAnalysisReview analysis={data.aiAnalysis} onChange={onUpdateAnalysis} />}
        </div>
      )}

      {(data.projekttyp === "beschaffungsagent" || data.projekttyp === "stuecklistenagent") && (
        <FileUploadZone files={data.uploadedFiles} onChange={(files) => onChange({ uploadedFiles: files })} />
      )}
    </div>
  );
}

function AiAnalysisReview({ analysis, onChange }: { analysis: AiAnalysis; onChange: (patch: Partial<AiAnalysis>) => void }) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Sparkles className="size-4 text-primary" />
        KI-Analyse (alle Felder editierbar)
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Projekttitel" value={analysis.project_title} onChange={(v) => onChange({ project_title: v })} />
        <Field label="GitHub-Repo-Name" value={analysis.repo_name} onChange={(v) => onChange({ repo_name: v })} />
        <Field label="Produktname (Vertrag/AVV)" value={analysis.produkt_name} onChange={(v) => onChange({ produkt_name: v })} />
        <Field label="Tech-Stack (Komma-getrennt)" value={analysis.tech_stack.join(", ")} onChange={(v) => onChange({ tech_stack: splitList(v) })} />
      </div>

      <TextField
        label="Produktbeschreibung (AVV)"
        value={analysis.produkt_beschreibung}
        onChange={(v) => onChange({ produkt_beschreibung: v })}
      />
      <TextField
        label="Vertragsbeschreibung"
        value={analysis.contract_description}
        onChange={(v) => onChange({ contract_description: v })}
      />
      <Field label="Features (Komma-getrennt)" value={analysis.features.join(", ")} onChange={(v) => onChange({ features: splitList(v) })} />

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="KI-Dienst-Beschreibung" value={analysis.ki_dienst_beschreibung} onChange={(v) => onChange({ ki_dienst_beschreibung: v })} />
        <Field label="Unterauftragnehmer (KI-Firma)" value={analysis.unterauftragnehmer_ki_firma} onChange={(v) => onChange({ unterauftragnehmer_ki_firma: v })} />
        <Field label="Unterauftragnehmer-Land" value={analysis.unterauftragnehmer_ki_land} onChange={(v) => onChange({ unterauftragnehmer_ki_land: v })} />
        <Field label="Unterauftragnehmer-Region" value={analysis.unterauftragnehmer_ki_region} onChange={(v) => onChange({ unterauftragnehmer_ki_region: v })} />
      </div>
      <TextField
        label="Unterauftragnehmer-Leistung"
        value={analysis.unterauftragnehmer_ki_leistung}
        onChange={(v) => onChange({ unterauftragnehmer_ki_leistung: v })}
      />

      {analysis.implementation_plan.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Label>Implementierungsplan</Label>
          <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
            {analysis.implementation_plan.map((phase, i) => (
              <li key={i} className="rounded-md border border-border px-3 py-2">
                <span className="font-medium text-foreground">
                  {phase.phase}: {phase.title} ({phase.duration})
                </span>
                <ul className="mt-1 list-inside list-disc">
                  {phase.tasks.map((task, j) => (
                    <li key={j}>{task}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}

      {analysis.ticket_plan.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Label>Ticket-Plan ({analysis.ticket_plan.length} Tickets werden als GitHub-Issues angelegt)</Label>
          <ul className="flex flex-col gap-1.5 text-sm text-muted-foreground">
            {analysis.ticket_plan.map((ticket, i) => (
              <li key={i} className="rounded-md border border-border px-3 py-1.5">
                <span className="font-medium text-foreground">{ticket.title}</span> — {ticket.type} / {ticket.priority}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function splitList(value: string): string[] {
  return value.split(",").map((v) => v.trim()).filter(Boolean);
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Textarea value={value} onChange={(e) => onChange(e.target.value)} rows={2} />
    </div>
  );
}

export function isProjectTypeValid(data: ProjectTypeData): boolean {
  if (!data.projekttyp) return false;
  if (data.projekttyp === "neues_projekt") return data.projektbeschreibung.trim() !== "" && data.aiAnalysis !== null;
  return true;
}
