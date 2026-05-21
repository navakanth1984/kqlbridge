import pytest
from kqlbridge.micro_model import TimeSeriesMicroModel

class TestTimeSeriesMicroModelSparkSQL:
    def test_spark_sql_basic_make_series(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="1d",
            from_time="ago(7d)",
            to_time="ago(1d)",
            by_cols=["ServiceName", "Region"],
            default_value=0
        )
        sql = model.to_spark_sql()
        
        # Verify sequence generation
        assert "sequence(CAST(current_timestamp() - INTERVAL 7 DAYS AS TIMESTAMP)" in sql
        assert "INTERVAL 1 DAY" in sql
        assert "explode(" in sql
        
        # Verify keys and complete grid
        assert "keys AS" in sql
        assert "SELECT DISTINCT ServiceName, Region FROM AppLogs" in sql
        assert "complete_grid AS" in sql
        assert "CROSS JOIN grid g" in sql
        
        # Verify aggregation with date_trunc
        assert "aggregated AS" in sql
        assert "date_trunc('day', TimeGenerated)" in sql
        assert "count() AS agg_val" in sql
        
        # Verify zero filling
        assert "coalesce(a.agg_val, 0) AS agg_filled" in sql
        assert "LEFT JOIN aggregated a" in sql
        assert "cg.ServiceName = a.ServiceName AND cg.Region = a.Region" in sql

    def test_spark_sql_interpolations(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="1h",
            from_time="ago(12h)",
            to_time="now()",
            by_cols=["ServiceName"],
            default_value=0,
            forward_fill_cols=["count"],
            linear_fill_cols=["count"]
        )
        sql = model.to_spark_sql()
        
        # Verify time boundaries and step
        assert "current_timestamp() - INTERVAL 12 HOURS" in sql
        assert "current_timestamp()" in sql
        assert "INTERVAL 1 HOUR" in sql
        
        # Verify forward fill window expression
        assert "last(agg_raw, true) OVER (PARTITION BY ServiceName ORDER BY TimeGenerated ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)" in sql
        
        # Verify linear fill window expression and formula
        assert "first(agg_raw, true) OVER (PARTITION BY ServiceName ORDER BY TimeGenerated ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING)" in sql
        assert "cast(TimeGenerated as double)" in sql


class TestTimeSeriesMicroModelTSQL:
    def test_tsql_basic_make_series(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="COUNT(*)",
            axis_col="TimeGenerated",
            step="1d",
            from_time="ago(7d)",
            to_time="ago(1d)",
            by_cols=["ServiceName", "Region"],
            default_value=0
        )
        sql = model.to_tsql()
        
        # Verify recursive CTE grid generation
        assert "WITH grid AS (" in sql
        assert "DATEADD(day, -7, GETDATE())" in sql
        assert "UNION ALL" in sql
        assert "DATEADD(day, 1, TimeGenerated)" in sql
        
        # Verify cross join and key extraction
        assert "keys AS (" in sql
        assert "CROSS JOIN grid g" in sql
        
        # Verify aggregation and date truncation/binning in T-SQL
        assert "DATEADD(day, DATEDIFF(day, 0, TimeGenerated), 0)" in sql
        assert "COALESCE(a.agg_val, 0) AS agg_filled" in sql

    def test_tsql_interpolations(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="COUNT(*)",
            axis_col="TimeGenerated",
            step="5m",
            from_time="ago(1h)",
            to_time="now()",
            by_cols=["ServiceName"],
            default_value=0,
            forward_fill_cols=["count"],
            linear_fill_cols=["count"]
        )
        sql = model.to_tsql()
        
        # Verify minute step and boundaries
        assert "DATEADD(minute, -1, GETDATE())" or "DATEADD(hour, -1, GETDATE())" in sql
        assert "DATEADD(minute, 5, TimeGenerated)" in sql
        
        # Verify T-SQL IGNORE NULLS analytical functions
        assert "LAST_VALUE(agg_raw) IGNORE NULLS OVER" in sql
        assert "FIRST_VALUE(agg_raw) IGNORE NULLS OVER" in sql
        assert "CAST(TimeGenerated AS FLOAT)" in sql


class TestTimeSeriesMicroModelPySpark:
    def test_pyspark_make_series(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="1d",
            from_time="ago(7d)",
            to_time="ago(1d)",
            by_cols=["ServiceName", "Region"],
            default_value=0,
            forward_fill_cols=["count"],
            linear_fill_cols=["count"]
        )
        code = model.to_pyspark()
        
        # Verify pyspark imports
        assert "from pyspark.sql import functions as F" in code
        assert "from pyspark.sql.window import Window" in code
        
        # Verify filtering, grid generation, and cross joining
        assert "F.current_timestamp() - F.expr('INTERVAL 7 DAYS')" in code
        assert "df_filtered.select('ServiceName', 'Region').distinct()" in code
        assert "df_keys.crossJoin(df_grid)" in code
        
        # Verify aggregation with date_trunc
        assert "F.date_trunc('day', F.col('TimeGenerated'))" in code
        assert "F.expr('count()').alias('agg_val')" in code
        
        # Verify coalesce and windows
        assert "F.coalesce(F.col('agg_val'), F.lit(0))" in code
        assert "Window.partitionBy('ServiceName', 'Region').orderBy('TimeGenerated')" in code
        assert "F.last('agg_raw', ignorenulls=True)" in code
        assert "Window.unboundedPreceding" in code


class TestTimeSeriesMicroModelPandas:
    def test_pandas_make_series(self):
        model = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="1d",
            from_time="ago(7d)",
            to_time="ago(1d)",
            by_cols=["ServiceName", "Region"],
            default_value=0,
            forward_fill_cols=["count"],
            linear_fill_cols=["count"]
        )
        code = model.to_pandas()
        
        # Verify pandas imports
        assert "import pandas as pd" in code
        assert "import numpy as np" in code
        
        # Verify time boundaries
        assert "now - pd.Timedelta('7 days')" in code
        assert "now - pd.Timedelta('1 days')" in code
        
        # Verify multi index and date range grid
        assert "pd.date_range(" in code
        assert "freq='1D'" in code
        assert "pd.MultiIndex.from_product(" in code
        
        # Verify resampling, reindexing and fills
        assert "reindex(multi_idx)" in code
        assert "fillna(0)" in code
        assert "ffill()" in code
        assert "interpolate(method='linear')" in code


class TestTimeSeriesMicroModelEdgeCases:
    def test_invalid_step(self):
        with pytest.raises(ValueError, match="Invalid step format"):
            TimeSeriesMicroModel(
                table="AppLogs",
                aggregation="count()",
                axis_col="TimeGenerated",
                step="invalid",
                from_time="ago(7d)",
                to_time="now()",
                by_cols=["ServiceName"],
                default_value=0
            ).to_spark_sql()

    def test_custom_step_units(self):
        # Minute step
        model_m = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="30m",
            from_time="ago(1h)",
            to_time="now()",
            by_cols=["ServiceName"],
            default_value=0
        )
        sql_m = model_m.to_spark_sql()
        assert "INTERVAL 30 MINUTE" in sql_m
        assert "date_trunc('minute', TimeGenerated)" in sql_m

        # Hour step
        model_h = TimeSeriesMicroModel(
            table="AppLogs",
            aggregation="count()",
            axis_col="TimeGenerated",
            step="12h",
            from_time="ago(1d)",
            to_time="now()",
            by_cols=["ServiceName"],
            default_value=0
        )
        sql_h = model_h.to_spark_sql()
        assert "INTERVAL 12 HOUR" in sql_h
        assert "date_trunc('hour', TimeGenerated)" in sql_h
