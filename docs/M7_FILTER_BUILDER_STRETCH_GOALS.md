# M7: Filter Builder - Stretch Goals & Future Enhancements

**Status**: Planning
**Version**: 0.6.1
**Last Updated**: 2025-10-25

## Overview

Phase 1 of the Filter Builder is complete with AND-only filtering. This document outlines future enhancements to unlock the full power of the filter DSL, which the backend already supports.

---

## Current State

### ✅ Implemented (Phase 1)
- Single AND group with multiple conditions
- 10 filterable fields (symbol, account, P&L, fees, dates, side, playbook fields)
- 12 operators (eq, ne, contains, in, not_in, gte, lte, gt, lt, between, is_null, not_null)
- Smart value inputs (text, number, date, multi-select, range)
- Active filter chips with individual remove
- URL addressability
- Backward compatibility with legacy query params

### ⚠️ Backend Ready, Frontend Pending
- OR operator support
- Nested AND/OR groups
- Complex filter logic

---

## Stretch Goal 1: Top-Level OR Toggle

**Effort**: Small (2-3 hours)
**Value**: Medium

### Description
Add ability to switch the top-level operator between AND and OR.

### UI Changes
```
┌─────────────────────────────────────────┐
│ Filters                             [2] │
├─────────────────────────────────────────┤
│ Match: [AND ▾] [OR]  ← New toggle      │
│                                         │
│ [Symbol] [contains] [EUR]          [×] │
│             AND                         │
│ [P&L] [≥] [0]                      [×] │
│                                         │
│ [+ Add Condition] [Apply] [Clear All]  │
└─────────────────────────────────────────┘
```

### Implementation
1. Add state in `FilterBuilder.tsx`: `const [operator, setOperator] = useState<"AND" | "OR">("AND")`
2. Add dropdown/toggle above conditions
3. Update filter DSL in `handleApply()`: `operator: operator` instead of hardcoded "AND"
4. Update "AND" label between conditions to use state: `{operator}`

### Example Use Case
"Show me trades where Symbol contains EUR **OR** Account contains Live"

---

## Stretch Goal 2: Nested Groups (Full Power)

**Effort**: Large (1-2 days)
**Value**: High

### Description
Support complex nested AND/OR logic like:
```
(Symbol contains EUR AND P&L ≥ 0)
  OR
(Playbook Grade = A AND Account = Live)
```

### UI Concept
```
┌──────────────────────────────────────────────────────┐
│ Filters                                          [5] │
├──────────────────────────────────────────────────────┤
│ ┌─ AND Group ────────────────────────────────┐  [×] │
│ │ [Symbol] [contains] [EUR]              [×] │      │
│ │            AND                             │      │
│ │ [P&L] [≥] [0]                          [×] │      │
│ └────────────────────────────────────────────┘      │
│                    OR                                │
│ ┌─ AND Group ────────────────────────────────┐  [×] │
│ │ [Playbook Grade] [equals] [A]          [×] │      │
│ │            AND                             │      │
│ │ [Account] [contains] [Live]            [×] │      │
│ └────────────────────────────────────────────┘      │
│                                                      │
│ [+ Add Condition] [+ Add Group]                     │
│ [Apply Filters] [Clear All]                         │
└──────────────────────────────────────────────────────┘
```

### Implementation Approach

**1. Update Data Model**
Change `FilterBuilder` state from flat conditions to recursive:
```typescript
type FilterNode = Condition | FilterGroup;

interface FilterGroup {
  operator: "AND" | "OR";
  conditions: FilterNode[];
}
```

**2. New Components**
- `FilterGroup.tsx` - Wrapper for grouped conditions with operator toggle
- Update `FilterBuilder.tsx` to support recursive rendering

**3. UI Interactions**
- "+ Add Condition" adds to current group
- "+ Add Group" creates nested AND/OR group
- Each group has its own operator toggle
- Remove button on groups (with confirmation if contains conditions)
- Visual nesting with borders/indentation

**4. Filter DSL Compilation**
Recursively build nested filter JSON matching backend schema

### Example Use Cases
1. **Complex Trade Queries**:
   - "(EURUSD or GBPUSD) AND (Winning trades OR A-grade playbooks)"
2. **Advanced Filtering**:
   - "Show high-risk trades (Risk% > 2) that were either profitable OR had A-grade execution"
3. **Multi-Account Logic**:
   - "(Account A AND profitable) OR (Account B AND breakeven)"

---

## Stretch Goal 3: Filter Presets/Templates

**Effort**: Small (2-3 hours)
**Value**: Medium

### Description
Quick-apply common filter patterns without building from scratch.

### UI
```
┌─────────────────────────────────────────┐
│ Filters                                 │
├─────────────────────────────────────────┤
│ Quick filters:                          │
│ [Winning Trades] [Losing Trades]        │
│ [A-Grade Only] [This Week] [This Month] │
│                                         │
│ Or build custom:                        │
│ [+ Add Condition]                       │
└─────────────────────────────────────────┘
```

### Preset Examples
- **Winning Trades**: P&L > 0
- **Losing Trades**: P&L < 0
- **A-Grade Only**: Playbook Grade = A
- **This Week**: Open Time between [start of week] and [end of week]
- **High Risk**: Intended Risk % > 2
- **Recent**: Open Time ≥ 7 days ago

### Implementation
1. Define preset configurations in `types.ts`
2. Add preset buttons above FilterBuilder
3. Click preset → populate filter conditions
4. User can further customize after applying preset

---

## Stretch Goal 4: Date Range Presets

**Effort**: Small (1-2 hours)
**Value**: High

### Description
Quick-select common date ranges (already exists for legacy filters, add to new Filter Builder).

### UI Enhancement
When selecting date field + between operator, show preset buttons:
```
[Open Time] [between] [2025-01-01] to [2025-01-31]

Quick ranges:
[Today] [Yesterday] [Last 7 Days] [This Week]
[Last Week] [This Month] [Last Month] [YTD]
```

### Implementation
Add `DateRangePresets.tsx` component that:
- Calculates date ranges dynamically based on current date
- Inserts into "between" value on click
- Shows inside ValueInput when operator is "between" and field is date type

---

## Stretch Goal 5: Filter Validation & Feedback

**Effort**: Small (2-3 hours)
**Value**: Medium

### Description
Provide real-time feedback on filter validity and improve UX.

### Features
1. **Incomplete Filter Warning**
   - Show warning if field selected but no operator
   - Disable "Apply" if any incomplete conditions

2. **Value Validation**
   - Number fields: validate numeric input
   - Date fields: validate date format
   - "In" operator: require at least 1 value
   - "Between": require both min and max

3. **Result Count Preview**
   - Show "(~23 trades match)" next to Apply button
   - Debounced API call to count matches without fetching all data

4. **Empty Result Warning**
   - If filter will return 0 results, show warning before applying
   - Suggest loosening filters

### Example UI
```
┌─────────────────────────────────────────┐
│ [Symbol] [contains] [XYZ]          [×] │
│            AND                          │
│ [P&L] [ ] [____]  ⚠️ Select operator  │
├─────────────────────────────────────────┤
│ [Apply Filters (~0 trades)]             │
│ ⚠️ No trades match these filters        │
└─────────────────────────────────────────┘
```

---

## Stretch Goal 6: Filter History & Undo

**Effort**: Medium (4-5 hours)
**Value**: Low-Medium

### Description
Remember previously applied filters and allow quick reapplication.

### Features
1. **Filter History** (stored in localStorage)
   - Last 10 filter combinations
   - Dropdown showing recent filters with descriptions
   - Click to reapply

2. **Undo/Redo**
   - Undo last filter change
   - Redo undone change
   - Keyboard shortcuts (Ctrl+Z, Ctrl+Y)

### UI
```
┌─────────────────────────────────────────┐
│ Filters                    [History ▾]  │
│                                         │
│ History:                                │
│ • Symbol:EUR AND P&L>0 (5 min ago)     │
│ • Account:Live (1 hour ago)            │
│ • Playbook Grade:A (Today 2:15pm)      │
└─────────────────────────────────────────┘
```

---

## Stretch Goal 7: Natural Language Filter Input

**Effort**: Large (3-5 days)
**Value**: Low (Cool Factor: High)

### Description
Allow users to type filters in natural language and parse into filter DSL.

### Example
```
Input: "symbol contains EUR and pnl > 100"
↓
Parsed to:
{
  "operator": "AND",
  "conditions": [
    {"field": "symbol", "op": "contains", "value": "EUR"},
    {"field": "net_pnl", "op": "gt", "value": 100}
  ]
}
```

### Implementation
1. Build simple parser for common patterns
2. Field name aliases (pnl = net_pnl, profit = net_pnl)
3. Operator aliases (>, >=, contains, includes, is)
4. Show parsed filter for confirmation before applying

---

## Stretch Goal 8: Export/Import Filters

**Effort**: Small (1-2 hours)
**Value**: Low-Medium

### Description
Allow users to share filter configurations.

### Features
1. **Copy Filter JSON**
   - Button to copy current filter DSL to clipboard
   - Can paste into Slack, docs, etc.

2. **Import from JSON**
   - Text area to paste filter JSON
   - Validates and applies

3. **Share via URL**
   - Already implemented! Filters encoded in URL params
   - Add "Copy link" button for easy sharing

---

## Priority Ranking

### High Priority (Do Next)
1. **Top-Level OR Toggle** - Simple, high value, unlocks common use cases
2. **Date Range Presets** - Huge time-saver for common operation
3. **Filter Validation & Feedback** - Better UX, prevents errors

### Medium Priority (Phase 2+)
4. **Nested Groups** - Power users, complex queries
5. **Filter Presets/Templates** - Convenience for common patterns
6. **Filter History & Undo** - Nice-to-have, improves workflow

### Low Priority (Nice-to-Have)
7. **Export/Import Filters** - Edge case, low demand
8. **Natural Language Input** - Cool but not essential

---

## Implementation Notes

- All stretch goals are **frontend-only** changes
- Backend already supports full filter DSL
- Maintain backward compatibility with Phase 1 implementation
- Consider combining multiple small stretch goals into single PR
- Test thoroughly with existing saved views (Phase 2)

---

## Success Metrics

When implementing stretch goals, measure:
- **Adoption**: % of users using advanced features (OR, nesting)
- **Complexity**: Average filter depth and condition count
- **Performance**: Filter application time with nested groups
- **Usability**: User feedback on complex filter builder UX

---

## Related Documents

- `/docs/M7_REPORTS_FILTERS_TECH_DESIGN.md` - Full M7 technical design
- `/docs/ROADMAP.md` - Overall project roadmap
