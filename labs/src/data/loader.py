import logging
import time

import pandas as pd
import polars as pl

from config.settings import SETTINGS

# Initialize the logger for this module
logger = logging.getLogger(__name__)


def load_and_clean_data() -> pl.DataFrame:
    """
    Loads the raw data dynamically based on the file extension using Pandas,
    converts it to Polars, formats the delivery date column, and logs execution time.
    """
    start_time = time.perf_counter()

    raw_file_path = SETTINGS["data"]["raw_path"]
    date_col = SETTINGS["columns"]["date_col"]

    logger.info("--- Starting Data Pipeline ---")
    logger.info(f"Target file: {raw_file_path}")

    ext = raw_file_path.suffix.lower()

    # STEP 1: Reading the file
    logger.info(f"[1/3] Reading {ext.upper()} file into memory...")

    if ext == ".csv":
        try:
            df_pd = pd.read_csv(
                raw_file_path, na_values=["NULL"], decimal=",", engine="pyarrow"
            )
            logger.info("      -> Successfully read CSV using PyArrow engine.")
        except Exception as e:
            logger.warning(
                f"      -> PyArrow read failed ({e}). Falling back to C engine (latin1)..."
            )
            df_pd = pd.read_csv(
                raw_file_path,
                encoding="latin1",
                na_values=["NULL"],
                decimal=",",
                engine="c",
                low_memory=False,
            )
            logger.info("      -> Successfully read CSV using C engine.")

    elif ext == ".parquet":
        df_pd = pd.read_parquet(raw_file_path, engine="pyarrow")
        logger.info("      -> Successfully read Parquet.")

    elif ext in [".xls", ".xlsx", ".xlsb"]:
        df_pd = pd.read_excel(raw_file_path, engine="calamine")
        logger.info("      -> Successfully read Excel using Calamine engine.")

    else:
        logger.error(f"Unsupported file format: {ext}")
        raise ValueError(f"Unsupported file format: {ext}")

    # STEP 2: Converting to Polars
    logger.info("[2/3] Converting Pandas DataFrame to Polars...")
    df_sample = df_pd.sample(n=50, random_state=42)
    df_sample.to_excel("Muestra_semilla_42.xlsx")
    df = pl.from_pandas(df_pd)
    del df_pd  # Free up memory

    # STEP 3: Cleaning Data
    logger.info("[3/3] Cleaning and formatting dates...")
    if df.schema[date_col] == pl.String:
        df = df.with_columns(
            pl.col(date_col)
            .str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S.%f", strict=False)
            .cast(pl.Date)
            .alias(date_col)
        )
    else:
        df = df.with_columns(pl.col(date_col).cast(pl.Date))

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    logger.info("--- Pipeline Complete ---")
    logger.info(
        f"Successfully loaded and cleaned {df.height} rows in {elapsed_time:.2f} seconds."
    )

    return df
