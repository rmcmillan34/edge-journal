"""
Filter DSL compiler for converting filter expressions to SQLAlchemy queries.

The filter DSL supports nested AND/OR groups with various operators:
- eq, ne: equality/inequality
- contains: string contains (case-insensitive)
- in, not_in: value in/not in list
- gte, lte, gt, lt: numeric/date comparisons
- between: range queries
- is_null, not_null: null checks
"""

from typing import Dict, List, Any, Union
from sqlalchemy.orm import Query
from sqlalchemy import and_, or_, func
from datetime import datetime, date

from .models import Trade, Account, Instrument, PlaybookResponse


class FilterCompiler:
    """Compiles filter DSL to SQLAlchemy query filters"""

    # Map filter field names to SQLAlchemy column objects
    FIELD_MAP = {
        # Trade fields
        "symbol": Instrument.symbol,
        "account": Account.name,
        "net_pnl": Trade.net_pnl,
        "gross_pnl": Trade.gross_pnl,
        "fees": Trade.fees,
        "open_time": Trade.open_time_utc,
        "close_time": Trade.close_time_utc,
        "side": Trade.side,
        "qty_units": Trade.qty_units,
        "entry_price": Trade.entry_price,
        "exit_price": Trade.exit_price,
        "reviewed": Trade.reviewed,

        # Playbook fields (requires join)
        "playbook.grade": PlaybookResponse.computed_grade,
        "playbook.compliance_score": PlaybookResponse.compliance_score,
        "playbook.intended_risk_pct": PlaybookResponse.intended_risk_pct,

        # Account fields
        "account.broker": Account.broker_label,
        "account.status": Account.status,
    }

    def __init__(self, user_id: int):
        """
        Initialize the filter compiler for a specific user.

        Args:
            user_id: The ID of the user to filter trades for
        """
        self.user_id = user_id
        self._needs_account_join = False
        self._needs_instrument_join = False
        self._needs_playbook_join = False

    def compile(self, filter_dsl: Dict[str, Any], base_query: Query) -> Query:
        """
        Apply filter DSL to SQLAlchemy query.

        Args:
            filter_dsl: Filter DSL dictionary with 'operator' and 'conditions'
            base_query: Base SQLAlchemy query to apply filters to

        Returns:
            Modified query with filters applied

        Example filter_dsl:
            {
              "operator": "AND",
              "conditions": [
                {"field": "symbol", "op": "contains", "value": "EUR"},
                {"field": "net_pnl", "op": "gte", "value": 0}
              ]
            }
        """
        if not filter_dsl or "conditions" not in filter_dsl:
            return base_query

        # First pass: check which joins are needed
        self._analyze_required_joins(filter_dsl)

        # Apply joins if needed
        query = self._apply_joins(base_query)

        # Compile the filter conditions
        filter_expr = self._compile_group(filter_dsl)

        if filter_expr is not None:
            query = query.filter(filter_expr)

        return query

    def _analyze_required_joins(self, filter_dsl: Dict[str, Any]) -> None:
        """Analyze filter DSL to determine which joins are needed"""
        conditions = filter_dsl.get("conditions", [])

        for condition in conditions:
            if "operator" in condition:
                # Nested group - recurse
                self._analyze_required_joins(condition)
            elif "field" in condition:
                field = condition["field"]
                if field.startswith("playbook."):
                    self._needs_playbook_join = True
                elif field == "symbol":
                    self._needs_instrument_join = True
                elif field == "account" or field.startswith("account."):
                    self._needs_account_join = True

    def _apply_joins(self, query: Query) -> Query:
        """
        Apply necessary joins to the query.

        Note: The base query from routes_trades.py already has joins for Account and Instrument,
        so we only add playbook join if needed. The existing joins will handle the filter conditions.
        """
        if self._needs_playbook_join:
            # Left join for playbook responses (trades might not have playbooks)
            # Get the latest playbook response for each trade
            query = query.outerjoin(
                PlaybookResponse,
                and_(
                    PlaybookResponse.trade_id == Trade.id,
                    PlaybookResponse.entry_type == "trade_playbook"
                )
            )

        # Note: Account and Instrument joins are already present in the base query,
        # so we don't add them here to avoid duplicate joins
        return query

    def _compile_group(self, group: Dict[str, Any]) -> Any:
        """
        Compile a filter group (AND/OR) to SQLAlchemy expression.

        Args:
            group: Filter group with 'operator' and 'conditions'

        Returns:
            SQLAlchemy expression combining all conditions
        """
        operator = group.get("operator", "AND")
        conditions = group.get("conditions", [])

        if not conditions:
            return None

        compiled_conditions = []
        for condition in conditions:
            if "operator" in condition:
                # Nested group
                compiled = self._compile_group(condition)
            else:
                # Single condition
                compiled = self._compile_condition(condition)

            if compiled is not None:
                compiled_conditions.append(compiled)

        if not compiled_conditions:
            return None

        if len(compiled_conditions) == 1:
            return compiled_conditions[0]

        if operator == "AND":
            return and_(*compiled_conditions)
        else:  # OR
            return or_(*compiled_conditions)

    def _compile_condition(self, condition: Dict[str, Any]) -> Any:
        """
        Compile single condition to SQLAlchemy expression.

        Args:
            condition: Condition dict with 'field', 'op', and 'value'

        Returns:
            SQLAlchemy filter expression
        """
        field_name = condition.get("field")
        op = condition.get("op")
        value = condition.get("value")

        if field_name not in self.FIELD_MAP:
            raise ValueError(f"Unknown filter field: {field_name}")

        column = self.FIELD_MAP[field_name]

        # Compile based on operator
        if op == "eq":
            return column == value

        elif op == "ne":
            return column != value

        elif op == "contains":
            # Case-insensitive string contains
            if value is None:
                return None
            return func.lower(column).contains(str(value).lower())

        elif op == "in":
            if not isinstance(value, list) or not value:
                return None
            return column.in_(value)

        elif op == "not_in":
            if not isinstance(value, list) or not value:
                return None
            return column.notin_(value)

        elif op == "gte":
            return column >= self._parse_value(value, column)

        elif op == "lte":
            return column <= self._parse_value(value, column)

        elif op == "gt":
            return column > self._parse_value(value, column)

        elif op == "lt":
            return column < self._parse_value(value, column)

        elif op == "between":
            if not isinstance(value, list) or len(value) != 2:
                return None
            min_val = self._parse_value(value[0], column, is_upper_bound=False)
            # For upper bound with date-only strings, we need to include the entire day
            # So we parse it with is_upper_bound=True which adds 1 day, then use < instead of <=
            max_val_raw = self._parse_value(value[1], column, is_upper_bound=False)

            # Check if value[1] is a date-only string (YYYY-MM-DD format)
            is_date_only = isinstance(value[1], str) and len(value[1]) == 10
            column_type = str(column.type)
            is_datetime_col = "DATETIME" in column_type or "TIMESTAMP" in column_type

            if is_date_only and is_datetime_col:
                # Add one day and use < for inclusive end-of-day
                from datetime import timedelta
                max_val_exclusive = max_val_raw + timedelta(days=1)
                return and_(column >= min_val, column < max_val_exclusive)
            else:
                # Use <= for non-date values or explicit timestamps
                return and_(column >= min_val, column <= max_val_raw)

        elif op == "is_null":
            return column.is_(None)

        elif op == "not_null":
            return column.isnot(None)

        else:
            raise ValueError(f"Unknown operator: {op}")

    def _parse_value(self, value: Any, column: Any, is_upper_bound: bool = False) -> Any:
        """
        Parse and convert value to appropriate type for column.

        Args:
            value: Raw value from filter DSL
            column: SQLAlchemy column to match type
            is_upper_bound: Deprecated, kept for compatibility

        Returns:
            Converted value
        """
        # If value is already the right type, return it
        if value is None:
            return None

        # Handle datetime columns
        column_type = str(column.type)
        if "DATETIME" in column_type or "TIMESTAMP" in column_type:
            if isinstance(value, str):
                # Try to parse ISO format datetime
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    # Try date-only format (parses as midnight)
                    try:
                        return datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        return value

        # Handle date columns
        if "DATE" in column_type:
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    return value

        return value


def legacy_params_to_filter_dsl(
    symbol: str = None,
    account: str = None,
    start: str = None,
    end: str = None
) -> Dict[str, Any]:
    """
    Convert legacy query parameters to filter DSL for backward compatibility.

    Args:
        symbol: Symbol filter (contains)
        account: Account name filter (contains)
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)

    Returns:
        Filter DSL dictionary
    """
    conditions = []

    if symbol:
        conditions.append({
            "field": "symbol",
            "op": "contains",
            "value": symbol
        })

    if account:
        conditions.append({
            "field": "account",
            "op": "contains",
            "value": account
        })

    if start:
        conditions.append({
            "field": "open_time",
            "op": "gte",
            "value": start
        })

    if end:
        # End date should be inclusive (end of day)
        # Add one day and use 'lt' to include all of end date
        try:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            from datetime import timedelta
            next_day = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            conditions.append({
                "field": "open_time",
                "op": "lt",
                "value": next_day
            })
        except ValueError:
            # If not a valid date, use as-is
            conditions.append({
                "field": "open_time",
                "op": "lte",
                "value": end
            })

    if not conditions:
        return {}

    return {
        "operator": "AND",
        "conditions": conditions
    }
