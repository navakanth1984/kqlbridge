from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

def parse_time_expr(expr: str, dialect: str = "spark") -> Dict[str, Any]:
    expr = expr.strip()
    if expr.lower() == "now()":
        return {"type": "now"}
    
    ago_match = re.match(r"ago\s*\(\s*([0-9]+)\s*([a-zA-Z]+)\s*\)", expr, re.IGNORECASE)
    if ago_match:
        num = int(ago_match.group(1))
        unit = ago_match.group(2).lower()
        return {"type": "ago", "value": num, "unit": unit}
    
    dt_match = re.match(r"datetime\s*\(\s*['\"]?([^'\")]+)['\"]?\s*\)", expr, re.IGNORECASE)
    if dt_match:
        return {"type": "datetime", "value": dt_match.group(1)}
    
    return {"type": "literal", "value": expr}

def parse_step(step_str: str) -> Dict[str, Any]:
    step_str = step_str.strip()
    match = re.match(r"([0-9]+)\s*([a-zA-Z]+)", step_str)
    if not match:
        raise ValueError(f"Invalid step format: {step_str}")
    num = int(match.group(1))
    unit = match.group(2).lower()
    return {"value": num, "unit": unit}

def get_default_alias(agg_expr: str) -> str:
    agg_expr = agg_expr.strip()
    match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*([a-zA-Z_][a-zA-Z0-9_.]*)?\s*\)", agg_expr)
    if match:
        func = match.group(1).lower()
        col = match.group(2)
        if col:
            return f"{func}_{col}"
        else:
            return f"{func}_"
    return "agg_val"

def format_time_expr(parsed_expr: Dict[str, Any], dialect: str) -> str:
    t_type = parsed_expr["type"]
    if t_type == "now":
        if dialect == "spark":
            return "current_timestamp()"
        elif dialect == "tsql":
            return "GETDATE()"
        elif dialect == "pyspark":
            return "F.current_timestamp()"
        elif dialect == "pandas":
            return "now"
    elif t_type == "ago":
        val = parsed_expr["value"]
        unit = parsed_expr["unit"]
        
        if dialect == "spark":
            unit_map = {"d": "DAYS", "h": "HOURS", "m": "MINUTES", "s": "SECONDS"}
            u = unit_map.get(unit, "DAYS")
            return f"current_timestamp() - INTERVAL {val} {u}"
        elif dialect == "tsql":
            unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
            u = unit_map.get(unit, "day")
            return f"DATEADD({u}, -{val}, GETDATE())"
        elif dialect == "pyspark":
            unit_map = {"d": "DAYS", "h": "HOURS", "m": "MINUTES", "s": "SECONDS"}
            u = unit_map.get(unit, "DAYS")
            return f"F.current_timestamp() - F.expr('INTERVAL {val} {u}')"
        elif dialect == "pandas":
            unit_map = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}
            u = unit_map.get(unit, "days")
            return f"now - pd.Timedelta('{val} {u}')"
    elif t_type == "datetime":
        val = parsed_expr["value"]
        if dialect == "spark":
            return f"CAST('{val}' AS TIMESTAMP)"
        elif dialect == "tsql":
            return f"CAST('{val}' AS DATETIME2)"
        elif dialect == "pyspark":
            return f"F.to_timestamp(F.lit('{val}'))"
        elif dialect == "pandas":
            return f"pd.to_datetime('{val}')"
    else:
        val = parsed_expr["value"]
        if dialect == "spark":
            return f"CAST('{val}' AS TIMESTAMP)"
        elif dialect == "tsql":
            return f"CAST('{val}' AS DATETIME2)"
        elif dialect == "pyspark":
            return f"F.to_timestamp(F.lit('{val}'))"
        elif dialect == "pandas":
            return f"pd.to_datetime('{val}')"
    return "current_timestamp()"

def format_step(parsed_step: Dict[str, Any], dialect: str) -> str:
    val = parsed_step["value"]
    unit = parsed_step["unit"]
    
    if dialect == "spark":
        unit_map = {"d": "DAY", "h": "HOUR", "m": "MINUTE", "s": "SECOND"}
        u = unit_map.get(unit, "DAY")
        return f"INTERVAL {val} {u}"
    elif dialect == "tsql":
        unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        return unit_map.get(unit, "day")
    elif dialect == "pyspark":
        unit_map = {"d": "DAY", "h": "HOUR", "m": "MINUTE", "s": "SECOND"}
        u = unit_map.get(unit, "DAY")
        return f"{val} {u}"
    elif dialect == "pandas":
        unit_map = {"d": "D", "h": "h", "m": "min", "s": "s"}
        u = unit_map.get(unit, "D")
        return f"{val}{u}"
    return f"{val}{unit}"


class TimeSeriesMicroModel:
    """
    KQL Time Series Window and Interpolation Compiler.
    
    Translates 'make-series' pipelines to Spark SQL, T-SQL, PySpark, and Python/Pandas.
    """
    
    def __init__(
        self,
        kql: Optional[str] = None,
        *,
        table: Optional[str] = None,
        aggregation: Optional[str] = None,
        axis_col: Optional[str] = None,
        step: Optional[str] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        by_cols: Optional[List[str]] = None,
        default_value: Any = 0,
        forward_fill_cols: Optional[List[str]] = None,
        linear_fill_cols: Optional[List[str]] = None
    ) -> None:
        self.kql = kql or ""
        self.source_query = table or ""
        self.agg_expr = aggregation or ""
        self.agg_alias = "agg_val"
        self.default_val = default_value if default_value is not None else 0
        self.axis_col = axis_col or ""
        self.start: Dict[str, Any] = {}
        self.end: Dict[str, Any] = {}
        self.step: Dict[str, Any] = {}
        self.groups = by_cols or []
        self.interpolation: Optional[str] = None
        self.forward_fill_cols = forward_fill_cols or []
        self.linear_fill_cols = linear_fill_cols or []
        
        if kql:
            self._parse()
        else:
            if step:
                self.step = parse_step(step)
            if from_time:
                self.start = parse_time_expr(from_time)
            if to_time:
                self.end = parse_time_expr(to_time)
            if forward_fill_cols:
                self.interpolation = "forward"
            if linear_fill_cols:
                self.interpolation = "linear"

        # FIX-04: validate temporal bounds after all paths (kql string OR explicit params).
        # Karpathy P3: only added this call; __init__ is otherwise unchanged.
        self._validate()

    def _validate(self) -> None:
        """FIX-04: Guard against silent runtime bombs.
        Raises ValueError for zero-step and end-before-start configurations.
        Called at the end of __init__ regardless of construction path.
        Karpathy P1: assumptions are explicit and checked here, not at SQL execution time.
        """
        # Guard 1: zero step generates an infinite sequence in Spark
        if self.step:
            step_val = self.step.get("value", 0)
            if step_val == 0:
                raise ValueError(
                    "step value must be > 0, got 0. "
                    "A zero-step generates an infinite sequence at runtime."
                )

        # Guard 2: end before or equal to start produces wrong/empty results silently
        if self.start and self.end:
            # Compare only for literal datetime types — skip ago()/now() comparisons
            # since those are relative and resolved at query time.
            if self.start.get("type") == "datetime" and self.end.get("type") == "datetime":
                try:
                    from datetime import datetime as _dt
                    start_dt = _dt.fromisoformat(self.start["value"])
                    end_dt = _dt.fromisoformat(self.end["value"])
                    if start_dt >= end_dt:
                        raise ValueError(
                            f"from_time must be strictly before to_time. "
                            f"Got from_time={self.start['value']!r} >= to_time={self.end['value']!r}. "
                            f"This would produce an empty or reversed time grid."
                        )
                except (ValueError, KeyError, TypeError) as exc:
                    if "must be strictly before" in str(exc):
                        raise  # re-raise our own validation error
                    # unparseable datetime — let it fail at SQL execution time

        # Guard 3: empty table name
        if self.source_query is not None and self.source_query.strip() == "":
            raise ValueError("table name must not be empty.")

    def _parse(self) -> None:
        match = re.search(r"\|\s*make-series\s", self.kql, re.IGNORECASE)
        if not match:
            raise ValueError("Query does not contain 'make-series' operator.")
        
        self.source_query = self.kql[:match.start()].strip()
        rest = self.kql[match.start() + 1:].strip()
        
        parts = []
        current_part: List[str] = []
        paren_depth = 0
        bracket_depth = 0
        for char in rest:
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            elif char == '|' and paren_depth == 0 and bracket_depth == 0:
                parts.append("".join(current_part).strip())
                current_part = []
                continue
            current_part.append(char)
        if current_part:
            parts.append("".join(current_part).strip())
            
        make_series_clause = parts[0]
        downstream_clauses = parts[1:] if len(parts) > 1 else []
        
        normalized_clause = " ".join(make_series_clause.split())
        clause_pattern = re.compile(
            r"^make-series\s+"
            r"(?P<agg_part>.+?)"
            r"\s+on\s+(?P<axis>[a-zA-Z_][a-zA-Z0-9_.]*)"
            r"\s+from\s+(?P<start>.+?)"
            r"\s+to\s+(?P<end>.+?)"
            r"\s+step\s+(?P<step>[0-9]+[a-zA-Z]+)"
            r"(?:\s+by\s+(?P<by>.+))?$",
            re.IGNORECASE
        )
        
        clause_match = clause_pattern.match(normalized_clause)
        if not clause_match:
            raise ValueError(f"Could not parse make-series clause: {make_series_clause}")
            
        gd = clause_match.groupdict()
        
        agg_part = gd["agg_part"].strip()
        self.axis_col = gd["axis"].strip()
        start_str = gd["start"].strip()
        end_str = gd["end"].strip()
        step_str = gd["step"].strip()
        by_str = gd["by"].strip() if gd["by"] else ""
        
        agg_match = re.match(
            r"(?:(?P<alias>[a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*)?"
            r"(?P<agg>[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\))"
            r"(?:\s+default\s*=\s*(?P<default>[a-zA-Z0-9_.-]+))?",
            agg_part,
            re.IGNORECASE
        )
        if not agg_match:
            raise ValueError(f"Could not parse aggregations in make-series: {agg_part}")
            
        alias = agg_match.group("alias")
        self.agg_expr = agg_match.group("agg").strip()
        default_val_str = agg_match.group("default")
        
        if alias:
            self.agg_alias = alias.strip()
        else:
            self.agg_alias = get_default_alias(self.agg_expr)
            
        if default_val_str is not None:
            try:
                if "." in default_val_str:
                    self.default_val = float(default_val_str)
                else:
                    self.default_val = int(default_val_str)
            except ValueError:
                self.default_val = default_val_str  # type: ignore
        else:
            self.default_val = 0
            
        self.start = parse_time_expr(start_str)
        self.end = parse_time_expr(end_str)
        self.step = parse_step(step_str)
        
        if by_str:
            self.groups = [g.strip() for g in by_str.split(",") if g.strip()]
        else:
            self.groups = []
            
        for clause in downstream_clauses:
            if re.search(r"series_fill_linear\s*\(", clause, re.IGNORECASE):
                self.interpolation = "linear"
                break
            elif re.search(r"series_fill_forward\s*\(", clause, re.IGNORECASE):
                self.interpolation = "forward"
                break

    def to_spark_sql(self, array_format: bool = False) -> str:
        step_val = self.step["value"]
        step_unit = self.step["unit"]
        
        trunc_unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        trunc_unit = trunc_unit_map.get(step_unit, "day")
        
        start_expr = format_time_expr(self.start, "spark")
        end_expr = format_time_expr(self.end, "spark")
        
        step_unit_map = {"d": "DAY", "h": "HOUR", "m": "MINUTE", "s": "SECOND"}
        step_expr = f"INTERVAL {step_val} {step_unit_map.get(step_unit, 'DAY')}"
        
        by_cols_select = "".join([f"{g}, " for g in self.groups])
        by_cols_group = ", ".join(self.groups)
        
        grid_cte = f"""WITH grid AS (
    SELECT explode(sequence(CAST({start_expr} AS TIMESTAMP), CAST({end_expr} AS TIMESTAMP), {step_expr})) AS {self.axis_col}
)"""
        
        if self.groups:
            grid_cte += f""",
keys AS (
    SELECT DISTINCT {by_cols_group} FROM {self.source_query}
),
complete_grid AS (
    SELECT k.*, g.{self.axis_col}
    FROM keys k
    CROSS JOIN grid g
)"""
            grid_select_cols = ", ".join([f"cg.{g}" for g in self.groups] + [f"cg.{self.axis_col}"])
            join_conditions = " AND ".join([f"cg.{g} = a.{g}" for g in self.groups]) + f" AND cg.{self.axis_col} = a.{self.axis_col}_bucket"
            groups_partition = ", ".join(self.groups)
            final_select_prefix = ", ".join([f"cg.{g}" for g in self.groups]) + f", cg.{self.axis_col}"
        else:
            grid_select_cols = f"g.{self.axis_col}"
            join_conditions = f"g.{self.axis_col} = a.{self.axis_col}_bucket"
            groups_partition = ""
            final_select_prefix = f"g.{self.axis_col}"
            
        agg_clause = f"{self.agg_expr} AS agg_val"
        
        if self.forward_fill_cols or self.linear_fill_cols or self.interpolation:
            partition_clause = f"PARTITION BY {groups_partition} " if groups_partition else ""
            
            if self.groups:
                joined_from = f"FROM complete_grid cg\n    LEFT JOIN aggregated a ON {join_conditions}"
            else:
                joined_from = f"FROM grid g\n    LEFT JOIN aggregated a ON {join_conditions}"
                
            agg_expr_to_use = self.agg_expr if self.agg_expr else "count()"
            
            sql = f"""{grid_cte},
aggregated AS (
    SELECT 
        {by_cols_select}date_trunc('{trunc_unit}', {self.axis_col}) AS {self.axis_col}_bucket,
        {agg_expr_to_use} AS agg_val
    FROM {self.source_query}
    GROUP BY {by_cols_group + ', ' if self.groups else ''}date_trunc('{trunc_unit}', {self.axis_col})
),
joined AS (
    SELECT 
        {grid_select_cols},
        a.agg_val AS agg_raw
    {joined_from}
)
SELECT 
    {by_cols_select}{self.axis_col},"""
            
            if self.linear_fill_cols or self.interpolation == "linear":
                sql += f"""
    coalesce(
        agg_raw, 
        last(agg_raw, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) + 
        (cast({self.axis_col} as double) - cast(last(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) as double)) / 
        (cast(first(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING) as double) - cast(last(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) as double)) * 
        (first(agg_raw, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING) - last(agg_raw, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)), 
        {self.default_val}
    ) AS agg_filled
FROM joined"""
            else:
                sql += f"""
    coalesce(
        agg_raw,
        last(agg_raw, true) OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        {self.default_val}
    ) AS agg_filled
FROM joined"""
            return sql
            
        else:
            agg_expr_to_use = self.agg_expr if self.agg_expr else "count()"
            
            if self.groups:
                from_and_joins = f"""FROM complete_grid cg
LEFT JOIN aggregated a
  ON {join_conditions}"""
            else:
                from_and_joins = f"""FROM grid g
LEFT JOIN aggregated a
  ON {join_conditions}"""
                
            return f"""{grid_cte},
complete_grid AS (
    SELECT k.*, g.{self.axis_col}
    FROM keys k
    CROSS JOIN grid g
),
aggregated AS (
    SELECT 
        {by_cols_select}date_trunc('{trunc_unit}', {self.axis_col}) AS {self.axis_col}_bucket,
        {agg_expr_to_use} AS agg_val
    FROM {self.source_query}
    GROUP BY {by_cols_group + ', ' if self.groups else ''}date_trunc('{trunc_unit}', {self.axis_col})
)
SELECT 
    {grid_select_cols},
    coalesce(a.agg_val, {self.default_val}) AS agg_filled
{from_and_joins}"""

    def to_tsql(self) -> str:
        step_val = self.step["value"]
        step_unit = self.step["unit"]
        
        trunc_unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        unit_name = trunc_unit_map.get(step_unit, "day")
        
        start_expr = format_time_expr(self.start, "tsql")
        end_expr = format_time_expr(self.end, "tsql")
        
        by_cols_select = "".join([f"{g}, " for g in self.groups])
        by_cols_group = ", ".join(self.groups)
        
        grid_cte = f"""WITH grid AS (
    SELECT CAST({start_expr} AS DATETIME2) AS {self.axis_col}
    UNION ALL
    SELECT DATEADD({unit_name}, {step_val}, {self.axis_col})
    FROM grid
    WHERE DATEADD({unit_name}, {step_val}, {self.axis_col}) <= CAST({end_expr} AS DATETIME2)
)"""
        
        if self.groups:
            grid_cte += f""",
keys AS (
    SELECT DISTINCT {by_cols_group} FROM {self.source_query}
),
complete_grid AS (
    SELECT k.*, g.{self.axis_col}
    FROM keys k
    CROSS JOIN grid g
)"""
            grid_select_cols = ", ".join([f"cg.{g}" for g in self.groups] + [f"cg.{self.axis_col}"])
            join_conditions = " AND ".join([f"cg.{g} = a.{g}" for g in self.groups]) + f" AND cg.{self.axis_col} = a.{self.axis_col}_bucket"
            groups_partition = ", ".join(self.groups)
            joined_from = f"FROM complete_grid cg\nLEFT JOIN aggregated a ON {join_conditions}"
        else:
            grid_select_cols = f"g.{self.axis_col}"
            join_conditions = f"g.{self.axis_col} = a.{self.axis_col}_bucket"
            groups_partition = ""
            joined_from = f"FROM grid g\nLEFT JOIN aggregated a ON {join_conditions}"
            
        agg_expr_to_use = self.agg_expr if self.agg_expr else "COUNT(*)"
        
        if self.forward_fill_cols or self.linear_fill_cols or self.interpolation:
            partition_clause = f"PARTITION BY {groups_partition} " if groups_partition else ""
            
            sql = f"""{grid_cte},
aggregated AS (
    SELECT 
        {by_cols_select}DATEADD({unit_name}, DATEDIFF({unit_name}, 0, {self.axis_col}), 0) AS {self.axis_col}_bucket,
        {agg_expr_to_use} AS agg_val
    FROM {self.source_query}
    GROUP BY {by_cols_group + ', ' if self.groups else ''}DATEADD({unit_name}, DATEDIFF({unit_name}, 0, {self.axis_col}), 0)
),
joined AS (
    SELECT 
        {grid_select_cols},
        a.agg_val AS agg_raw
    {joined_from}
)
SELECT 
    {by_cols_select}{self.axis_col},"""
            
            if self.linear_fill_cols or self.interpolation == "linear":
                sql += f"""
    COALESCE(
        agg_raw,
        LAST_VALUE(agg_raw) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) + 
        (CAST({self.axis_col} AS FLOAT) - CAST(LAST_VALUE(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS FLOAT)) / 
        (CAST(FIRST_VALUE(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING) AS FLOAT) - CAST(LAST_VALUE(CASE WHEN agg_raw IS NOT NULL THEN {self.axis_col} END) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS FLOAT)) * 
        (FIRST_VALUE(agg_raw) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING) - LAST_VALUE(agg_raw) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)),
        {self.default_val}
    ) AS agg_filled
FROM joined
OPTION (MAXRECURSION 0)"""
            else:
                sql += f"""
    COALESCE(
        agg_raw,
        LAST_VALUE(agg_raw) IGNORE NULLS OVER ({partition_clause}ORDER BY {self.axis_col} ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        {self.default_val}
    ) AS agg_filled
FROM joined
OPTION (MAXRECURSION 0)"""
            return sql
            
        else:
            return f"""{grid_cte},
complete_grid AS (
    SELECT k.*, g.{self.axis_col}
    FROM keys k
    CROSS JOIN grid g
),
aggregated AS (
    SELECT 
        {by_cols_select}DATEADD({unit_name}, DATEDIFF({unit_name}, 0, {self.axis_col}), 0) AS {self.axis_col}_bucket,
        {agg_expr_to_use} AS agg_val
    FROM {self.source_query}
    GROUP BY {by_cols_group + ', ' if self.groups else ''}DATEADD({unit_name}, DATEDIFF({unit_name}, 0, {self.axis_col}), 0)
)
SELECT 
    {grid_select_cols},
    COALESCE(a.agg_val, {self.default_val}) AS agg_filled
{joined_from}
OPTION (MAXRECURSION 0)"""

    def to_pyspark(self) -> str:
        groups_list_repr = repr(self.groups)
        step_val = self.step["value"]
        step_unit = self.step["unit"]
        
        trunc_unit_map = {"d": "day", "h": "hour", "m": "minute", "s": "second"}
        trunc_unit = trunc_unit_map.get(step_unit, "day")
        
        pyspark_start = format_time_expr(self.start, "pyspark")
        pyspark_end = format_time_expr(self.end, "pyspark")
        
        agg_kql = self.agg_expr if self.agg_expr else "count()"
        
        code = f"""from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Filter source by time boundaries
df_filtered = df.filter(F.col('{self.axis_col}').between({pyspark_start}, {pyspark_end}))

# Extract keys
df_keys = df_filtered.select({", ".join([repr(g) for g in self.groups])}).distinct()

# Generate time grid
df_grid = spark.range(1).select(
    F.explode(F.sequence({pyspark_start}, {pyspark_end}, F.expr("INTERVAL {step_val} {trunc_unit.upper()}S"))).alias("{self.axis_col}")
)

# Full complete grid
complete_grid = df_keys.crossJoin(df_grid)

# Aggregate source
df_aggregated = df_filtered.groupBy(
    {", ".join([f"F.col('{g}')" for g in self.groups])},
    F.date_trunc('{trunc_unit}', F.col('{self.axis_col}')).alias('{self.axis_col}_bucket')
).agg(
    F.expr('{agg_kql}').alias('agg_val')
)

# Join complete grid with aggregated
df_joined = complete_grid.join(
    df_aggregated,
    on=[
        {", ".join([f"complete_grid['{g}'] == df_aggregated['{g}']" for g in self.groups])},
        complete_grid['{self.axis_col}'] == df_aggregated['{self.axis_col}_bucket']
    ],
    how="left"
).select(
    {", ".join([f"complete_grid['{g}']" for g in self.groups])},
    complete_grid['{self.axis_col}'],
    df_aggregated['agg_val'].alias('agg_val'),
    df_aggregated['agg_val'].alias('agg_raw')
)

# Zero filling and window functions for interpolation
window_spec = Window.partitionBy({", ".join([repr(g) for g in self.groups])}).orderBy('{self.axis_col}')
"""
        
        code += f"""
# Coalesce to default
df_joined = df_joined.withColumn('agg_filled', F.coalesce(F.col('agg_val'), F.lit({self.default_val})))
"""
        
        if self.forward_fill_cols or self.interpolation == "forward":
            code += f"""
# Forward fill
window_prev = Window.partitionBy({", ".join([repr(g) for g in self.groups])}).orderBy('{self.axis_col}').rowsBetween(Window.unboundedPreceding, -1)
df_final = df_joined.withColumn(
    'agg_filled',
    F.coalesce(F.col('agg_raw'), F.last('agg_raw', ignorenulls=True).over(window_prev), F.lit({self.default_val}))
)
"""
        if self.linear_fill_cols or self.interpolation == "linear":
            code += f"""
# Linear fill
window_prev = Window.partitionBy({", ".join([repr(g) for g in self.groups])}).orderBy('{self.axis_col}').rowsBetween(Window.unboundedPreceding, -1)
window_next = Window.partitionBy({", ".join([repr(g) for g in self.groups])}).orderBy('{self.axis_col}').rowsBetween(1, Window.unboundedFollowing)

df_final = df_joined.withColumn(
    'last_val', F.last('agg_raw', ignorenulls=True).over(window_prev)
).withColumn(
    'last_time', F.last(F.when(F.col('agg_raw').isNotNull(), F.col('{self.axis_col}')), ignorenulls=True).over(window_prev)
).withColumn(
    'next_val', F.first('agg_raw', ignorenulls=True).over(window_next)
).withColumn(
    'next_time', F.first(F.when(F.col('agg_raw').isNotNull(), F.col('{self.axis_col}')), ignorenulls=True).over(window_next)
).withColumn(
    'agg_filled',
    F.coalesce(
        F.col('agg_raw'),
        F.col('last_val') + (F.col('{self.axis_col}').cast('double') - F.col('last_time').cast('double')) / 
        (F.col('next_time').cast('double') - F.col('last_time').cast('double')) * (F.col('next_val') - F.col('last_val')),
        F.lit({self.default_val})
    )
)
"""
        return code

    def to_python(self) -> str:
        groups_list_repr = repr(self.groups)
        pandas_start = format_time_expr(self.start, "pandas")
        pandas_end = format_time_expr(self.end, "pandas")
        pandas_step = format_step(self.step, "pandas")
        
        agg_kql = self.agg_expr if self.agg_expr else "count()"
        
        code = f"""import pandas as pd
import numpy as np

# Define now and time boundaries
now = pd.Timestamp.now()
start_time = {pandas_start}
end_time = {pandas_end}

# Filter and aggregate
df_filtered = df[(df['{self.axis_col}'] >= start_time) & (df['{self.axis_col}'] <= end_time)]
source_aggs = df_filtered.groupby({groups_list_repr} + [pd.Grouper(key='{self.axis_col}', freq='{pandas_step}')])['{self.axis_col}'].count().reset_index()
source_aggs.rename(columns={{'{self.axis_col}': 'agg_val'}}, inplace=True)

# Generate grid
time_range = pd.date_range(start=start_time, end=end_time, freq='{pandas_step}', name='{self.axis_col}')
distinct_groups = df_filtered[{groups_list_repr}].drop_duplicates()

# Prevent group erasure with MultiIndex
multi_idx = pd.MultiIndex.from_product(
    [distinct_groups[g] for g in {groups_list_repr}] + [time_range],
    names={groups_list_repr} + ['{self.axis_col}']
)

df_indexed = source_aggs.set_index({groups_list_repr} + ['{self.axis_col}']).reindex(multi_idx)

# Zero filling and interpolations
df_indexed['agg_filled'] = df_indexed['agg_val'].fillna({self.default_val})
"""
        if self.forward_fill_cols or self.interpolation == "forward":
            code += f"""
# Forward fill
df_indexed['agg_filled'] = df_indexed.groupby({groups_list_repr})['agg_val'].ffill().fillna({self.default_val})
"""
        if self.linear_fill_cols or self.interpolation == "linear":
            code += f"""
# Linear fill
df_indexed['agg_filled'] = df_indexed.groupby({groups_list_repr})['agg_val'].transform(lambda x: x.interpolate(method='linear')).fillna({self.default_val})
"""
        return code

    def to_pandas(self) -> str:
        return self.to_python()
