import logging
from pathlib import Path

import pandas as pd
import polars as pl

from config.settings import SETTINGS

logger = logging.getLogger(__name__)


def transform_base_data(df: pl.DataFrame, dim_file: Path) -> pl.DataFrame:
    """
    Pure transformation step.
    Receives an ALREADY LOADED & VALIDATED Polars DataFrame and the dimension file path.

    - Splits '_KEY_ACCOUNT' into 'COD KEY ACCOUNT' (numeric ID) and 'Key account' (name description)
    - Merges with the dimension table using 'COD KEY ACCOUNT' to fetch 'Canal'
    - Derives 'Nome do Mês' and 'Ano' from 'DATA_ENTREGA'
    - Leaves specified target metrics and validation columns blank (None)
    - Enforces strict target schema order fetched strictly from config (SETTINGS)
    """
    logger.info("Starting base data transformation in memory...")

    # 1. Load dimension table for channel mapping robustly using the passed dim_file path
    try:
        df_dim_pd = pd.read_csv(dim_file, sep=";", encoding="latin1")
        if len(df_dim_pd.columns) == 1:
            df_dim_pd = pd.read_csv(dim_file, sep=",", encoding="latin1")
    except Exception:
        df_dim_pd = pd.read_csv(dim_file, sep=",", encoding="latin1")

    df_dim = (
        pl.from_pandas(df_dim_pd)
        .select(["COD KEY ACCOUNT", "Canal"])
        .with_columns(pl.col("COD KEY ACCOUNT").cast(pl.Int64))
        .unique(subset=["COD KEY ACCOUNT"])
    )

    # Fetch months mapping dictionary from settings (ensuring integer keys)
    months_mapping = {int(k): v for k, v in SETTINGS.get("months", {}).items()}

    # 2. Extract keys, split _KEY_ACCOUNT, derive date fields, and set requested columns to None (blank)
    df_transformed = (
        df.with_columns(
            [
                # Split _KEY_ACCOUNT: Extract numeric ID as Int64 to match dimension table
                pl.col("_KEY_ACCOUNT")
                .cast(pl.Utf8)
                .str.extract(r"^(\d+)")
                .cast(pl.Int64)
                .alias("COD KEY ACCOUNT"),
                # Split _KEY_ACCOUNT: Extract account name description
                pl.col("_KEY_ACCOUNT")
                .cast(pl.Utf8)
                .str.extract(r" - (.*)$")
                .alias("Key account"),
                pl.col("CATEGORIA_1").alias("Categoria"),
                # Derive 'Nome do Mês' and 'Ano' from DATA_ENTREGA
                pl.col("DATA_ENTREGA")
                .dt.month()
                .replace_strict(months_mapping, return_dtype=pl.Utf8)
                .alias("Nome do Mês"),
                pl.col("DATA_ENTREGA").dt.year().alias("Ano"),
                # Requested columns to be left blank (None)
                pl.lit(None).alias("Dupli. Matricula"),
                pl.lit(None).alias("*Vol Misto"),
                pl.lit(None).alias("*Datas Entrega"),
                pl.lit(None).alias("*Soma Lastro"),
                pl.lit(None).alias("* Paletização"),
                pl.lit(None).alias("Camada"),
                pl.lit(None).alias("*Valida Paletização"),
                pl.lit(None).alias("*Valida Lastro"),
                pl.lit(None).alias("Oportunidade"),
                pl.lit(None).alias("Menor 1 lastro"),
                pl.lit(None).alias("% Lastro"),
                pl.lit(None).alias("% Palete"),
                pl.lit(None).alias("Valida oport. Palete"),
            ]
        )
        # Join with dimension table using the matching Int64 ID type
        .join(df_dim, on="COD KEY ACCOUNT", how="left")
    )

    # 3. Enforce strict target schema order fetched from settings
    target_schema = SETTINGS["target_schema"]

    df_final = df_transformed.select(target_schema)
    logger.info(
        f"Transformation complete. Processed {df_final.height} rows successfully."
    )

    return df_final
