/**
 * Type definitions for Filter DSL
 */

export type FilterOperator =
  | "eq"
  | "ne"
  | "contains"
  | "in"
  | "not_in"
  | "gte"
  | "lte"
  | "gt"
  | "lt"
  | "between"
  | "is_null"
  | "not_null";

export interface Condition {
  field: string;
  op: FilterOperator;
  value: string | number | string[] | number[] | null;
}

export interface FilterDSL {
  operator: "AND" | "OR";
  conditions: Condition[];
}

export type FieldType = "string" | "number" | "date";

export interface FieldDefinition {
  key: string;
  label: string;
  type: FieldType;
}

// Available fields for filtering
export const AVAILABLE_FIELDS: FieldDefinition[] = [
  { key: "symbol", label: "Symbol", type: "string" },
  { key: "account", label: "Account", type: "string" },
  { key: "net_pnl", label: "P&L", type: "number" },
  { key: "fees", label: "Fees", type: "number" },
  { key: "open_time", label: "Open Time", type: "date" },
  { key: "close_time", label: "Close Time", type: "date" },
  { key: "side", label: "Side (Buy/Sell)", type: "string" },
  { key: "playbook.grade", label: "Playbook Grade", type: "string" },
  { key: "playbook.compliance_score", label: "Compliance Score", type: "number" },
  { key: "playbook.intended_risk_pct", label: "Intended Risk %", type: "number" },
];

// Operator labels for display
export const OPERATOR_LABELS: Record<FilterOperator, string> = {
  eq: "equals",
  ne: "not equals",
  contains: "contains",
  in: "in list",
  not_in: "not in list",
  gte: "≥",
  lte: "≤",
  gt: ">",
  lt: "<",
  between: "between",
  is_null: "is empty",
  not_null: "is not empty",
};

/**
 * Get available operators for a field type
 */
export function getOperatorsForFieldType(fieldType: FieldType): FilterOperator[] {
  switch (fieldType) {
    case "string":
      return ["eq", "ne", "contains", "in", "is_null", "not_null"];
    case "number":
      return ["eq", "ne", "gte", "lte", "gt", "lt", "between", "is_null", "not_null"];
    case "date":
      return ["eq", "gte", "lte", "between", "is_null", "not_null"];
    default:
      return ["eq", "ne", "is_null", "not_null"];
  }
}

/**
 * Get field type from field key
 */
export function getFieldType(fieldKey: string): FieldType {
  const field = AVAILABLE_FIELDS.find((f) => f.key === fieldKey);
  return field?.type || "string";
}

/**
 * Get field label from field key
 */
export function getFieldLabel(fieldKey: string): string {
  const field = AVAILABLE_FIELDS.find((f) => f.key === fieldKey);
  return field?.label || fieldKey;
}
