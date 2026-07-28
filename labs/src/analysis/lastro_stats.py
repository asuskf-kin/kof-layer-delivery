# src/analysis/lastro_stats.py
import polars as pl


def analyze_trend_over_time(
    df: pl.DataFrame, date_col: str, target_col: str, freq: str
) -> pl.DataFrame:
    """Calculates the % of fractional vs. closed pallets/layers over time."""
    trend = (
        df.group_by([pl.col(date_col).dt.truncate(freq).alias("period"), target_col])
        .agg(pl.len().alias("order_count"))
        .with_columns(
            (
                pl.col("order_count") / pl.col("order_count").sum().over("period") * 100
            ).alias("percentage")
        )
        .sort("period")
    )
    return trend


def identify_fractional_offenders(
    df: pl.DataFrame, target_col: str, fractional_val: str, dim_col: str
) -> pl.DataFrame:
    """Identifies which clients (RAZAO_SOCIAL) or SKUs generate the most fractional orders."""
    offenders = (
        df.filter(pl.col(target_col).str.contains(fractional_val))
        .group_by(dim_col)
        .agg(pl.len().alias("total_fractional"))
        .sort("total_fractional", descending=True)
        .head(10)  # Top 10 offenders
    )
    return offenders
