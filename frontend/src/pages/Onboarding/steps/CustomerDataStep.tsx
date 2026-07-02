import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CustomerData } from "../types";

interface FieldConfig {
  key: keyof CustomerData;
  label: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
}

const FIELDS: FieldConfig[] = [
  { key: "kundenname", label: "Kundenname", required: true },
  { key: "kunde_adresse", label: "Kundenadresse" },
  { key: "ansprechpartner_name", label: "Ansprechpartner Name", required: true },
  { key: "ansprechpartner_email", label: "Ansprechpartner E-Mail", type: "email", required: true },
  { key: "ansprechpartner_telefon", label: "Ansprechpartner Telefon" },
  { key: "erp_system", label: "ERP-System", placeholder: "z.B. ProAlpha, SAP, Buhl" },
  { key: "it_kontakt_name", label: "IT-Kontakt Name" },
  { key: "it_kontakt_email", label: "IT-Kontakt E-Mail", type: "email" },
  { key: "bestellnummer", label: "Bestellnummer", placeholder: "z.B. BEST-PROZESSIA-127412" },
  { key: "bestelldatum", label: "Bestelldatum", type: "date" },
  { key: "angebotsnummer", label: "Angebotsnummer", placeholder: "z.B. AG0024" },
  { key: "angebotsdatum", label: "Angebotsdatum", type: "date" },
  { key: "setup_preis", label: "Setup-Preis (€)", type: "number", required: true },
  { key: "monatliche_rate", label: "Monatliche Rate (€)", type: "number", required: true },
  { key: "projektstart_datum", label: "Projektstart-Datum", type: "date", required: true },
];

interface CustomerDataStepProps {
  data: CustomerData;
  onChange: (patch: Partial<CustomerData>) => void;
}

export function CustomerDataStep({ data, onChange }: CustomerDataStepProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {FIELDS.map((field) => (
        <div key={field.key} className="flex flex-col gap-1.5">
          <Label htmlFor={field.key}>
            {field.label}
            {field.required && <span className="text-destructive"> *</span>}
          </Label>
          <Input
            id={field.key}
            type={field.type ?? "text"}
            placeholder={field.placeholder}
            value={data[field.key]}
            onChange={(e) => onChange({ [field.key]: e.target.value })}
          />
        </div>
      ))}
    </div>
  );
}

export function isCustomerDataValid(data: CustomerData): boolean {
  return (
    data.kundenname.trim() !== "" &&
    data.ansprechpartner_name.trim() !== "" &&
    data.ansprechpartner_email.trim() !== "" &&
    data.setup_preis.trim() !== "" &&
    data.monatliche_rate.trim() !== "" &&
    data.projektstart_datum.trim() !== ""
  );
}
