"use client";

import { FilterOperator, FieldType, OPERATOR_LABELS, getOperatorsForFieldType } from "./types";

interface OperatorSelectorProps {
  value: FilterOperator | "";
  fieldType: FieldType;
  onChange: (op: FilterOperator) => void;
}

export default function OperatorSelector({ value, fieldType, onChange }: OperatorSelectorProps) {
  const availableOperators = getOperatorsForFieldType(fieldType);

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as FilterOperator)}
      style={{
        padding: "6px 8px",
        borderRadius: "4px",
        minWidth: "120px",
      }}
    >
      <option value="">Select operator...</option>
      {availableOperators.map((op) => (
        <option key={op} value={op}>
          {OPERATOR_LABELS[op]}
        </option>
      ))}
    </select>
  );
}
