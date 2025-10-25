"use client";

import { Condition, getFieldType, FilterOperator } from "./types";
import FieldSelector from "./FieldSelector";
import OperatorSelector from "./OperatorSelector";
import ValueInput from "./ValueInput";

interface FilterConditionProps {
  condition: Condition;
  onChange: (updated: Condition) => void;
  onRemove: () => void;
}

export default function FilterCondition({ condition, onChange, onRemove }: FilterConditionProps) {
  const fieldType = condition.field ? getFieldType(condition.field) : "string";

  const handleFieldChange = (field: string) => {
    // When field changes, reset operator and value
    onChange({
      field,
      op: "" as FilterOperator,
      value: null,
    });
  };

  const handleOperatorChange = (op: FilterOperator) => {
    // When operator changes, reset value
    let newValue: any = null;

    // Initialize appropriate default values
    if (op === "in" || op === "not_in") {
      newValue = [];
    } else if (op === "between") {
      newValue = ["", ""];
    } else if (op === "is_null" || op === "not_null") {
      newValue = null;
    }

    onChange({
      ...condition,
      op,
      value: newValue,
    });
  };

  const handleValueChange = (value: any) => {
    onChange({
      ...condition,
      value,
    });
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "8px",
        alignItems: "center",
        padding: "8px",
        border: "1px solid var(--ctp-surface2)",
        borderRadius: "6px",
        background: "var(--ctp-surface0)",
        flexWrap: "wrap",
      }}
    >
      <FieldSelector value={condition.field} onChange={handleFieldChange} />

      {condition.field && (
        <OperatorSelector
          value={condition.op}
          fieldType={fieldType}
          onChange={handleOperatorChange}
        />
      )}

      {condition.field && condition.op && (
        <ValueInput
          fieldKey={condition.field}
          fieldType={fieldType}
          operator={condition.op}
          value={condition.value}
          onChange={handleValueChange}
        />
      )}

      <button
        type="button"
        onClick={onRemove}
        title="Remove condition"
        style={{
          padding: "6px 10px",
          borderRadius: "4px",
          background: "var(--ctp-red)",
          color: "var(--ctp-crust)",
          border: "none",
          cursor: "pointer",
          fontWeight: "bold",
          marginLeft: "auto",
        }}
      >
        ×
      </button>
    </div>
  );
}
