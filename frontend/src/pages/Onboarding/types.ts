export type ProjectType = "beschaffungsagent" | "stuecklistenagent" | "neues_projekt";

export interface CustomerData {
  kundenname: string;
  kunde_adresse: string;
  ansprechpartner_name: string;
  ansprechpartner_email: string;
  ansprechpartner_telefon: string;
  erp_system: string;
  it_kontakt_name: string;
  it_kontakt_email: string;
  bestellnummer: string;
  bestelldatum: string;
  angebotsnummer: string;
  angebotsdatum: string;
  setup_preis: string;
  monatliche_rate: string;
  projektstart_datum: string;
}

export const EMPTY_CUSTOMER_DATA: CustomerData = {
  kundenname: "",
  kunde_adresse: "",
  ansprechpartner_name: "",
  ansprechpartner_email: "",
  ansprechpartner_telefon: "",
  erp_system: "",
  it_kontakt_name: "",
  it_kontakt_email: "",
  bestellnummer: "",
  bestelldatum: "",
  angebotsnummer: "",
  angebotsdatum: "",
  setup_preis: "",
  monatliche_rate: "",
  projektstart_datum: "",
};

export const BESCHAFFUNGSAGENT_FEATURES = [
  "AB-Abgleich",
  "Mahnwesen",
  "3-Way-Match Rechnungsprüfung",
  "Versanddokumente",
  "Angebotsvergleich / RFQ",
  "Tagesbriefing",
  "Lieferantenscore",
  "Eskalationsmechanismus",
  "Performance-Tracking",
  "Vessel Tracking",
];

export const STUECKLISTENAGENT_FEATURES = [
  "Triple-Lock Extraktion",
  "GREEN/YELLOW/RED Confidence-System",
  "Split-View PDF + Excel UI",
  "Bulk-Accept für GREEN Cells",
  "Stammdaten-Matching",
];

export interface ImplementationPhase {
  phase: string;
  title: string;
  duration: string;
  tasks: string[];
}

export interface TicketPlanItem {
  title: string;
  type: "feature" | "setup";
  priority: "high" | "medium" | "low";
  description: string;
}

export interface AiAnalysis {
  repo_name: string;
  project_title: string;
  produkt_name: string;
  produkt_beschreibung: string;
  tech_stack: string[];
  features: string[];
  ki_dienst_beschreibung: string;
  unterauftragnehmer_ki_firma: string;
  unterauftragnehmer_ki_land: string;
  unterauftragnehmer_ki_region: string;
  unterauftragnehmer_ki_leistung: string;
  implementation_plan: ImplementationPhase[];
  ticket_plan: TicketPlanItem[];
  contract_description: string;
}

export interface ProjectTypeData {
  projekttyp: ProjectType | null;
  features: string[];
  neue_funktion: string;
  projektbeschreibung: string;
  aiAnalysis: AiAnalysis | null;
  uploadedFiles: File[];
}

export const EMPTY_PROJECT_TYPE_DATA: ProjectTypeData = {
  projekttyp: null,
  features: [],
  neue_funktion: "",
  projektbeschreibung: "",
  aiAnalysis: null,
  uploadedFiles: [],
};

export interface AutomationToggles {
  drive_folders: boolean;
  file_upload: boolean;
  contract: boolean;
  avv: boolean;
  github: boolean;
  notification: boolean;
}

export const DEFAULT_TOGGLES: AutomationToggles = {
  drive_folders: true,
  file_upload: true,
  contract: true,
  avv: true,
  github: true,
  notification: true,
};

export const STEP_LABELS: Record<keyof AutomationToggles, string> = {
  drive_folders: "Drive Ordnerstruktur erstellen",
  file_upload: "Dateien in Drive hochladen",
  contract: "Dienstleistungsvertrag generieren",
  avv: "AVV generieren",
  github: "GitHub Repository erstellen/forken",
  notification: "Email-Notification senden",
};

export const STEP_DESCRIPTIONS: Record<keyof AutomationToggles, string> = {
  drive_folders: "Legt die komplette Kundenordner-Struktur in Google Drive an.",
  file_upload: "Lädt die hochgeladenen Dokumente nach 01_Onboarding/Kundendokumente hoch.",
  contract: "Erstellt den Dienstleistungsvertrag als Markdown in 00_Verträge.",
  avv: "Befüllt die AVV-Vorlage und legt sie als .docx in 00_Verträge ab.",
  github: "Forkt das passende Produkt-Repo oder legt ein neues Projekt-Repo an.",
  notification: "Informiert das Team per E-Mail über das neue Onboarding.",
};
