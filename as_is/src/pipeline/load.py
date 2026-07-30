import logging
from pathlib import Path

import polars as pl

from config.settings import SETTINGS

logger = logging.getLogger(__name__)


def export_to_excel(df_base: pl.DataFrame, df_palet: pl.DataFrame) -> None:
    """
    Exports the final Polars DataFrames to Excel, guaranteeing
    the exact same format without injecting pandas indexes.
    """
    out_dir = Path(SETTINGS["paths"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / SETTINGS["paths"]["output_file"]

    logger.info(f"Exporting results natively with Polars to {out_path}...")

    # Polars native Excel writer requires 'xlsxwriter'
    # We pass both DataFrames as a dictionary to write them as separate sheets
    sheets = {"Base_Processed": df_base, "Paletizacao_CSV": df_palet}

    # Writing multiple sheets directly from Polars
    # This ensures 100% schema fidelity and zero index artifacts
    # You will need to add xlsxwriter via uv: `uv add xlsxwriter`
    from xlsxwriter import Workbook

    with Workbook(out_path) as wb:
        for sheet_name, df in sheets.items():
            df.write_excel(
                workbook=wb,
                worksheet=sheet_name,
                header_format={"bold": True},  # Keeps headers clean
                autofit=True,  # Automatically fits column widths
            )

    logger.info("Export completed with exact formatting preserved.")
