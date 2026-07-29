import logging
from pathlib import Path

from config.settings import SETTINGS
from src.pipeline.extract import load_and_clean_data
from src.pipeline.transform_base import transform_base_data

# Global logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Starting Paletização ETL Pipeline ===")

    raw_dir = Path(SETTINGS["paths"]["raw_dir"])
    palet_file = raw_dir / SETTINGS["paths"]["paletizacao_file"]
    dim_file = raw_dir / SETTINGS["paths"]["dim_key_account_file"]
    logger.info(f"Processing second source: {palet_file.name}")
    df_base_raw = load_and_clean_data(palet_file)

    # 2. TRANSFORM: Transform Base 1 using the in-memory DataFrame
    df_base_final = transform_base_data(df_base_raw, dim_file)
    df_base_final.write_csv("test.csv")
    logger.info("=== ETL Pipeline Completed Successfully ===")


if __name__ == "__main__":
    main()
