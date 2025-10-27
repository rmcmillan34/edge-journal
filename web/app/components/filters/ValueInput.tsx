"use client";

import { useState } from "react";
import { FieldType, FilterOperator } from "./types";

interface ValueInputProps {
  fieldKey: string;
  fieldType: FieldType;
  operator: FilterOperator | "";
  value: any;
  onChange: (value: any) => void;
}

export default function ValueInput({ fieldKey, fieldType, operator, value, onChange }: ValueInputProps) {
  const [tempValue, setTempValue] = useState<string>("");

  // No input needed for null checks
  if (operator === "is_null" || operator === "not_null") {
    return (
      <div style={{ padding: "6px 8px", color: "var(--ctp-overlay1)", fontStyle: "italic" }}>
        (no value needed)
      </div>
    );
  }

  // Handle "in" operator - comma-separated list
  if (operator === "in" || operator === "not_in") {
    const displayValue = Array.isArray(value) ? value.join(", ") : (value || "");

    return (
      <input
        type="text"
        placeholder="Enter values separated by commas"
        value={displayValue}
        onChange={(e) => {
          const inputVal = e.target.value;
          // Split by comma and trim whitespace
          const items = inputVal.split(",").map((s) => s.trim()).filter(Boolean);

          // Convert to numbers if numeric field
          if (fieldType === "number") {
            const numbers = items.map((s) => parseFloat(s)).filter((n) => !isNaN(n));
            onChange(numbers);
          } else {
            onChange(items);
          }
        }}
        style={{
          padding: "6px 8px",
          borderRadius: "4px",
          minWidth: "200px",
          flex: 1,
        }}
      />
    );
  }

  // Handle "between" operator - two inputs
  if (operator === "between") {
    const [min, max] = Array.isArray(value) && value.length === 2 ? value : ["", ""];

    return (
      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
        {fieldType === "date" ? (
          <>
            <input
              type="date"
              value={min || ""}
              onChange={(e) => onChange([e.target.value, max])}
              style={{ padding: "6px 8px", borderRadius: "4px" }}
            />
            <span style={{ color: "var(--ctp-overlay1)" }}>to</span>
            <input
              type="date"
              value={max || ""}
              onChange={(e) => onChange([min, e.target.value])}
              style={{ padding: "6px 8px", borderRadius: "4px" }}
            />
          </>
        ) : (
          <>
            <input
              type={fieldType === "number" ? "number" : "text"}
              placeholder="Min"
              value={min || ""}
              onChange={(e) => {
                const val = fieldType === "number" ? parseFloat(e.target.value) : e.target.value;
                onChange([val, max]);
              }}
              style={{ padding: "6px 8px", borderRadius: "4px", width: "100px" }}
            />
            <span style={{ color: "var(--ctp-overlay1)" }}>to</span>
            <input
              type={fieldType === "number" ? "number" : "text"}
              placeholder="Max"
              value={max || ""}
              onChange={(e) => {
                const val = fieldType === "number" ? parseFloat(e.target.value) : e.target.value;
                onChange([min, val]);
              }}
              style={{ padding: "6px 8px", borderRadius: "4px", width: "100px" }}
            />
          </>
        )}
      </div>
    );
  }

  // Special handling for specific fields with known values
  if (fieldKey === "side" && operator === "eq") {
    return (
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "6px 8px", borderRadius: "4px", minWidth: "120px" }}
      >
        <option value="">Select side...</option>
        <option value="Buy">Buy</option>
        <option value="Sell">Sell</option>
      </select>
    );
  }

  if (fieldKey === "playbook.grade" && operator === "eq") {
    return (
      <select
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "6px 8px", borderRadius: "4px", minWidth: "120px" }}
      >
        <option value="">Select grade...</option>
        <option value="A">A</option>
        <option value="B">B</option>
        <option value="C">C</option>
        <option value="D">D</option>
      </select>
    );
  }

  // Default input based on field type
  if (fieldType === "date") {
    return (
      <input
        type="date"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "6px 8px",
          borderRadius: "4px",
          minWidth: "150px",
        }}
      />
    );
  }

  if (fieldType === "number") {
    return (
      <input
        type="number"
        step="any"
        placeholder="Enter number"
        value={value ?? ""}
        onChange={(e) => {
          const val = e.target.value;
          onChange(val === "" ? null : parseFloat(val));
        }}
        style={{
          padding: "6px 8px",
          borderRadius: "4px",
          minWidth: "150px",
        }}
      />
    );
  }

  // Default: text input
  return (
    <input
      type="text"
      placeholder="Enter value"
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      style={{
        padding: "6px 8px",
        borderRadius: "4px",
        minWidth: "150px",
        flex: 1,
      }}
    />
  );
}
