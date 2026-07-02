import { useCallback, useState } from "react";
import { api } from "@/api/client";
import { streamOnboarding, type OnboardingEvent } from "@/api/client";
import {
  DEFAULT_TOGGLES,
  EMPTY_CUSTOMER_DATA,
  EMPTY_PROJECT_TYPE_DATA,
  type AiAnalysis,
  type AutomationToggles,
  type CustomerData,
  type ProjectTypeData,
} from "../types";

export type StepStatus = "pending" | "running" | "done" | "error" | "warning";

export function useOnboarding() {
  const [step, setStep] = useState(1);
  const [customer, setCustomer] = useState<CustomerData>(EMPTY_CUSTOMER_DATA);
  const [project, setProject] = useState<ProjectTypeData>(EMPTY_PROJECT_TYPE_DATA);
  const [toggles, setToggles] = useState<AutomationToggles>(DEFAULT_TOGGLES);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<Record<string, OnboardingEvent>>({});
  const [result, setResult] = useState<{ drive_link?: string; github_link?: string } | null>(null);
  const [runError, setRunError] = useState("");

  const updateCustomer = useCallback((patch: Partial<CustomerData>) => {
    setCustomer((prev) => ({ ...prev, ...patch }));
  }, []);

  const updateProject = useCallback((patch: Partial<ProjectTypeData>) => {
    setProject((prev) => ({ ...prev, ...patch }));
  }, []);

  const updateAnalysis = useCallback((patch: Partial<AiAnalysis>) => {
    setProject((prev) => (prev.aiAnalysis ? { ...prev, aiAnalysis: { ...prev.aiAnalysis, ...patch } } : prev));
  }, []);

  const analyzeNewProject = useCallback(async () => {
    setAnalyzing(true);
    setAnalyzeError("");
    try {
      const form = new FormData();
      form.append("beschreibung", project.projektbeschreibung);
      for (const file of project.uploadedFiles) form.append("files", file);
      const analysis = await api.postForm<AiAnalysis>("/api/onboarding/analyze", form);
      updateProject({ aiAnalysis: analysis, features: analysis.features });
    } catch {
      setAnalyzeError("KI-Analyse fehlgeschlagen. Bitte Dateien/Beschreibung prüfen und erneut versuchen.");
    } finally {
      setAnalyzing(false);
    }
  }, [project.projektbeschreibung, project.uploadedFiles, updateProject]);

  const buildSubmitData = useCallback((): Record<string, unknown> => {
    const base: Record<string, unknown> = { ...customer, projekttyp: project.projekttyp };
    if (project.projekttyp === "neues_projekt") {
      return { ...base, projektbeschreibung: project.projektbeschreibung, ...(project.aiAnalysis ?? {}) };
    }
    return { ...base, features: project.features, neue_funktion: project.neue_funktion };
  }, [customer, project]);

  const startOnboarding = useCallback(async () => {
    setRunning(true);
    setRunError("");
    setEvents({});
    setResult(null);

    const form = new FormData();
    form.append("data", JSON.stringify(buildSubmitData()));
    form.append("toggles", JSON.stringify(toggles));
    for (const file of project.uploadedFiles) form.append("files", file);

    try {
      await streamOnboarding(form, (event) => {
        if (event.step === "complete") {
          setResult({ drive_link: event.drive_link, github_link: event.github_link });
          if (event.status === "error") setRunError("Onboarding wurde wegen eines Fehlers abgebrochen.");
          return;
        }
        setEvents((prev) => ({ ...prev, [event.step]: event }));
      });
    } catch {
      setRunError("Verbindung zum Server unterbrochen. Bitte prüfen, ob bereits Schritte gelaufen sind, bevor du es erneut versuchst.");
    } finally {
      setRunning(false);
    }
  }, [buildSubmitData, toggles, project.uploadedFiles]);

  return {
    step,
    setStep,
    customer,
    updateCustomer,
    project,
    updateProject,
    updateAnalysis,
    toggles,
    setToggles,
    analyzing,
    analyzeError,
    analyzeNewProject,
    running,
    events,
    result,
    runError,
    startOnboarding,
  };
}
