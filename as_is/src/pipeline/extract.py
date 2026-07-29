import logging
import time
from pathlib import Path

import pandas as pd
import polars as pl

from config.settings import SETTINGS

logger = logging.getLogger(__name__)


def load_and_clean_data(file_path: Path) -> pl.DataFrame:
    """
    Loads raw data using Pandas, converts to Polars,
    and cleans percentage string columns if they exist.
    """
    start_time = time.perf_counter()
    required_cols = SETTINGS.get("required_columns", [])
    pct_cols = SETTINGS["columns"]["pct_cols"]

    logger.info(f"Reading file into memory: {file_path.name}")
    ext = file_path.suffix.lower()

    if ext == ".csv":
        try:
            df_pd = pd.read_csv(
                file_path,
                sep=",",
                decimal=",",
                na_values=["NULL"],
                engine="pyarrow",
            )
        except Exception as e:
            logger.warning(f"PyArrow failed ({e}). Falling back to C engine...")
            df_pd = pd.read_csv(
                file_path,
                sep=",",
                encoding="latin1",
                decimal=",",
                na_values=["NULL"],
                engine="c",
                low_memory=False,
            )
    elif ext in [".xls", ".xlsx", ".xlsb"]:
        df_pd = pd.read_excel(
            file_path, engine="pyxlsb" if ext == ".xlsb" else "calamine"
        )
    else:
        raise ValueError(f"Unsupported format: {ext}")
    file_columns = df_pd.columns.tolist()
    missing_cols = [col for col in required_cols if col not in file_columns]

    if missing_cols:
        logger.error(
            f"Validation failed. Missing columns in {file_path.name}: {missing_cols}"
        )
        raise ValueError(f"Missing mandatory columns in source file -> {missing_cols}")

    logger.info(f"Column validation passed successfully for {file_path.name}.")

    logger.info("Converting to Polars...")
    df = pl.from_pandas(df_pd)
    del df_pd

    for col in pct_cols:
        if col in df.columns and df.schema[col] == pl.String:
            df = df.with_columns(
                pl.col(col).str.replace("%", "").cast(pl.Float64) / 100.0
            )

    logger.info(f"Loaded {df.height} rows in {time.perf_counter() - start_time:.2f}s")
    return df
