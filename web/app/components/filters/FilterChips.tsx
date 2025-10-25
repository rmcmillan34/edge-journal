"use client";

import { FilterDSL, getFieldLabel, OPERATOR_LABELS } from "./types";

interface FilterChipsProps {
  filters: FilterDSL | null;
  onRemoveCondition: (index: number) => void;
  onClearAll: () => void;
}

export default function FilterChips({ filters, onRemoveCondition, onClearAll }: FilterChipsProps) {
  if (!filters || !filters.conditions || filters.conditions.length === 0) {
    return null;
  }

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "";
    }
    if (Array.isArray(value)) {
      if (value.length === 2 && value.every((v) => v !== null && v !== "")) {
        // between operator
        return `${value[0]} - ${value[1]}`;
      }
      // in/not_in operator
      return value.join(", ");
    }
    return String(value);
  };

  return (
    <div
      style={{
        display: "flex",
        gap: "8px",
        flexWrap: "wrap",
        alignItems: "center",
        padding: "8px 12px",
        background: "var(--ctp-surface0)",
        borderRadius: "6px",
        marginBottom: "16px",
      }}
    >
      <span style={{ fontSize: "14px", color: "var(--ctp-overlay1)", fontWeight: 600 }}>
        Active filters:
      </span>

      {filters.conditions.map((condition, index) => {
        const fieldLabel = getFieldLabel(condition.field);
        const operatorLabel = OPERATOR_LABELS[condition.op];
        const valueStr = formatValue(condition.value);

        return (
          <div
            key={index}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 8px",
              background: "var(--ctp-surface1)",
              borderRadius: "4px",
              fontSize: "13px",
              border: "1px solid var(--ctp-surface2)",
            }}
          >
            <span style={{ color: "var(--ctp-blue)", fontWeight: 600 }}>{fieldLabel}</span>
            <span style={{ color: "var(--ctp-overlay1)" }}>{operatorLabel}</span>
            {condition.op !== "is_null" && condition.op !== "not_null" && valueStr && (
              <span style={{ color: "var(--ctp-text)", fontWeight: 500 }}>{valueStr}</span>
            )}
            <button
              type="button"
              onClick={() => onRemoveCondition(index)}
              title="Remove this filter"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--ctp-red)",
                cursor: "pointer",
                padding: "0 4px",
                fontSize: "16px",
                fontWeight: "bold",
                lineHeight: "1",
              }}
            >
              ×
            </button>
          </div>
        );
      })}

      <button
        type="button"
        onClick={onClearAll}
        style={{
          padding: "4px 8px",
          fontSize: "13px",
          background: "transparent",
          color: "var(--ctp-red)",
          border: "1px solid var(--ctp-surface2)",
          borderRadius: "4px",
          cursor: "pointer",
          fontWeight: 500,
        }}
      >
        Clear all
      </button>
    </div>
  );
}
