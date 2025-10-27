"use client";

import { useState, useEffect } from "react";
import { FilterDSL, Condition, FilterOperator } from "./types";
import FilterCondition from "./FilterCondition";

interface FilterBuilderProps {
  onApply: (filterDsl: FilterDSL | null) => void;
  initialFilters?: FilterDSL;
}

export default function FilterBuilder({ onApply, initialFilters }: FilterBuilderProps) {
  const [conditions, setConditions] = useState<Condition[]>([]);

  // Initialize from props if provided
  useEffect(() => {
    if (initialFilters && initialFilters.conditions) {
      setConditions(initialFilters.conditions);
    }
  }, [initialFilters]);

  const addCondition = () => {
    const newCondition: Condition = {
      field: "",
      op: "" as FilterOperator,
      value: null,
    };
    setConditions([...conditions, newCondition]);
  };

  const updateCondition = (index: number, updated: Condition) => {
    const newConditions = [...conditions];
    newConditions[index] = updated;
    setConditions(newConditions);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const handleApply = () => {
    // Filter out incomplete conditions (missing field or operator)
    const validConditions = conditions.filter(
      (c) => c.field && c.op
    );

    if (validConditions.length === 0) {
      onApply(null);
      return;
    }

    const filterDsl: FilterDSL = {
      operator: "AND", // MVP: single AND group only
      conditions: validConditions,
    };

    onApply(filterDsl);
  };

  const handleClearAll = () => {
    setConditions([]);
    onApply(null);
  };

  return (
    <div
      style={{
        border: "1px solid var(--ctp-surface1)",
        borderRadius: "8px",
        padding: "16px",
        background: "var(--ctp-mantle)",
        marginBottom: "16px",
      }}
    >
      <div style={{ marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>Filters</h3>
        {conditions.length > 0 && (
          <span
            style={{
              background: "var(--ctp-surface2)",
              color: "var(--ctp-text)",
              padding: "2px 8px",
              borderRadius: "12px",
              fontSize: "12px",
            }}
          >
            {conditions.length}
          </span>
        )}
      </div>

      {conditions.length === 0 && (
        <div
          style={{
            padding: "16px",
            textAlign: "center",
            color: "var(--ctp-overlay1)",
            fontStyle: "italic",
          }}
        >
          No filters applied. Click &quot;Add Condition&quot; to start filtering.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
        {conditions.map((condition, index) => (
          <div key={index}>
            {index > 0 && (
              <div
                style={{
                  padding: "4px 0",
                  fontSize: "12px",
                  fontWeight: "bold",
                  color: "var(--ctp-mauve)",
                  textAlign: "center",
                }}
              >
                AND
              </div>
            )}
            <FilterCondition
              condition={condition}
              onChange={(updated) => updateCondition(index, updated)}
              onRemove={() => removeCondition(index)}
            />
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={addCondition}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            background: "var(--ctp-blue)",
            color: "var(--ctp-crust)",
            border: "none",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          + Add Condition
        </button>

        <button
          type="button"
          onClick={handleApply}
          disabled={conditions.length === 0}
          style={{
            padding: "8px 16px",
            borderRadius: "6px",
            background: conditions.length > 0 ? "var(--ctp-green)" : "var(--ctp-surface1)",
            color: conditions.length > 0 ? "var(--ctp-crust)" : "var(--ctp-overlay1)",
            border: "none",
            cursor: conditions.length > 0 ? "pointer" : "not-allowed",
            fontWeight: 600,
          }}
        >
          Apply Filters
        </button>

        {conditions.length > 0 && (
          <button
            type="button"
            onClick={handleClearAll}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "var(--ctp-surface1)",
              color: "var(--ctp-text)",
              border: "1px solid var(--ctp-surface2)",
              cursor: "pointer",
            }}
          >
            Clear All
          </button>
        )}
      </div>
    </div>
  );
}
