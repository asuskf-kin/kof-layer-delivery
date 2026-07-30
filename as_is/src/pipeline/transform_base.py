import logging
from pathlib import Path

import pandas as pd
import polars as pl

from config.settings import SETTINGS

logger = logging.getLogger(__name__)


def transform_base_data(df: pl.DataFrame, dim_file: Path) -> pl.DataFrame:
    """
    Transformation step with GroupBy Aggregation.

    - Splits '_KEY_ACCOUNT' into 'COD KEY ACCOUNT' and 'Key account'
    - Derives date and month fields
    - Creates a unique 'Clave' (Key) based on Mes_Ano_MATRICULA_SKU
    - Groups by the Key and aggregates (SUM) LASTRO, PALETIZACAO, VOL_CF and counts unique dates
    - Performs sequential math calculations (ratios, validations, opportunities) on the grouped data
    - Merges with the dimension table to fetch 'Canal'
    - Enforces strict target schema order
    """
    logger.info("Starting base data transformation and aggregation in memory...")

    # 1. Load dimension table for channel mapping robustly
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

    months_mapping = {int(k): v for k, v in SETTINGS.get("months", {}).items()}

    # 2. Extract base features and CREATE THE KEY (Clave)
    df_base = df.with_columns(
        [
            # Split _KEY_ACCOUNT
            pl.col("_KEY_ACCOUNT")
            .cast(pl.Utf8)
            .str.extract(r"^(\d+)")
            .cast(pl.Int64)
            .alias("COD KEY ACCOUNT"),
            pl.col("_KEY_ACCOUNT")
            .cast(pl.Utf8)
            .str.extract(r" - (.*)$")
            .alias("Key account"),
            pl.col("CATEGORIA_1").alias("Categoria"),
            # Derive Dates
            pl.col("DATA_ENTREGA")
            .dt.month()
            .replace_strict(months_mapping, return_dtype=pl.Utf8)
            .alias("Nome do Mês"),
            pl.col("DATA_ENTREGA").dt.year().alias("Ano"),
            pl.col("DATA_ENTREGA").dt.month().alias("Mes"),
        ]
    ).with_columns(
        # Create the specific Key: Mes_Ano_MATRICULA_SKU_ECC
        pl.concat_str(
            [
                pl.col("Mes").cast(pl.Utf8).str.pad_start(2, "0"),
                pl.lit("_"),
                pl.col("Ano").cast(pl.Utf8),
                pl.lit("_"),
                pl.col("MATRICULA").cast(pl.Utf8),
                pl.lit("_"),
                pl.col("SKU_ECC").cast(pl.Utf8),
            ]
        ).alias("clave")
    )

    # 3. GROUP BY the Key and calculate the SUMS (Σ) and unique dates
    df_grouped = df_base.group_by(
        [
            "clave",
            "Mes",
            "Ano",
            "Nome do Mês",
            "MATRICULA",
            "SKU_ECC_DESC",
            "SKU_ECC",
            "COD KEY ACCOUNT",
            "Key account",
            "Categoria",
        ]
    ).agg(
        [
            pl.col("LASTRO").sum().alias("LASTRO"),
            pl.col("PALETIZACAO").sum().alias("PALETIZACAO"),
            pl.col("VOL_CF").sum().alias("VOL_CF"),
            pl.col("VOL_CF").sum().alias("*Vol Misto"),
            # AQUI ESTA LA CORRECCIÓN: Cuenta las fechas únicas en lugar de sumar FlagFecha
            pl.col("DATA_ENTREGA").n_unique().alias("*Datas Entrega"),
        ]
    )

    # 4. MATH CALCULATIONS (Executing over the grouped dataframe)
    df_math = (
        df_grouped.with_columns(
            [
                # Block 1: Base division metrics
                (pl.col("LASTRO") / pl.col("*Datas Entrega")).alias("*Soma Lastro"),
                (pl.col("PALETIZACAO") / pl.col("*Datas Entrega")).alias(
                    "* Paletização"
                ),
                (pl.col("*Vol Misto") / pl.col("PALETIZACAO")).alias(
                    "*Valida Paletização"
                ),
                (pl.col("*Vol Misto") / pl.col("LASTRO")).alias("*Valida Lastro"),
            ]
        )
        .with_columns(
            [
                # Block 2: Logic and percentages
                (pl.col("* Paletização") / pl.col("*Soma Lastro"))
                .round(0)
                .alias("Camada"),
                pl.when(
                    (pl.col("*Datas Entrega") >= 3)
                    & (pl.col("*Valida Paletização") >= 0.99)
                )
                .then(pl.lit("Oportunidade Palete"))
                .when(
                    (pl.col("*Datas Entrega") >= 3)
                    & (pl.col("*Valida Paletização") < 0.99)
                    & (pl.col("*Valida Lastro") >= 1)
                )
                .then(pl.lit("Oportunidade Lastro"))
                .otherwise(pl.lit("Sem Oportunidade"))
                .alias("Oportunidade"),
                (pl.col("*Vol Misto") < pl.col("*Soma Lastro")).alias("Menor 1 lastro"),
                (pl.col("*Vol Misto") / pl.col("*Soma Lastro")).alias("% Lastro"),
                (pl.col("*Vol Misto") / pl.col("* Paletização")).alias("% Palete"),
                pl.lit(1).alias("Dupli. Matricula"),
            ]
        )
        .with_columns(
            [
                # Block 3: Final validation opportunity
                pl.when(pl.col("% Palete") >= 0.79)
                .then(pl.lit("Oportunidade Palete"))
                .when(pl.col("% Lastro") >= 0.59)
                .then(pl.lit("Oportunidade Lastro"))
                .otherwise(pl.lit("Avaliar"))
                .alias("Valida oport. Palete"),
            ]
        )
    )

    # 5. Join with dimension table
    df_transformed = df_math.join(df_dim, on="COD KEY ACCOUNT", how="left")

    # 6. Enforce strict target schema order fetched from settings
    target_schema = SETTINGS["target_schema"]
    target_schema_limpio = list(dict.fromkeys(target_schema))
    df_final = df_transformed.select(target_schema)

    logger.info(
        f"Transformation complete. Grouped into {df_final.height} summary rows successfully."
    )

    return df_final
