"use client";

import { AVAILABLE_FIELDS } from "./types";

interface FieldSelectorProps {
  value: string;
  onChange: (field: string) => void;
}

export default function FieldSelector({ value, onChange }: FieldSelectorProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        padding: "6px 8px",
        borderRadius: "4px",
        minWidth: "180px",
      }}
    >
      <option value="">Select field...</option>
      {AVAILABLE_FIELDS.map((field) => (
        <option key={field.key} value={field.key}>
          {field.label}
        </option>
      ))}
    </select>
  );
}
