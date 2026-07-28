import logging
import os

from config.settings import ROOT_DIR, SETTINGS
from src.analysis.lastro_stats import (
    analyze_trend_over_time,
)
from src.data.loader import load_and_clean_data
from src.visualization.reporter import generate_descriptive_html

# 1. Configure logging FIRST so it applies to all imported modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# 2. Initialize the logger for this specific file
logger = logging.getLogger(__name__)


def main():

    logger.info("[1/4] Configuration loaded successfully via router.")

    logger.info("[2/4] Loading and cleaning data...")
    df = load_and_clean_data()

    logger.info("[3/4] Running temporal analysis and descriptive stats...")
    trend_df = analyze_trend_over_time(
        df=df,
        date_col=SETTINGS["columns"]["date_col"],
        target_col=SETTINGS["columns"]["target_col"],
        freq=SETTINGS["eda_params"]["time_freq"],
    )

    # Calculate the descriptive statistics
    df_summary = df.describe()

    logger.info("[4/4] Generating and saving reports...")

    # Ensure report directories exist
    reports_fig_dir = ROOT_DIR / "reports/figures"
    reports_sum_dir = ROOT_DIR / "reports/summaries"
    os.makedirs(reports_fig_dir, exist_ok=True)
    os.makedirs(reports_sum_dir, exist_ok=True)

    # Generate the descriptive HTML report, passing the schema (df.schema)
    html_output_path = reports_sum_dir / "descriptive_report.html"

    generate_descriptive_html(
        df_summary=df_summary,
        original_schema=df.schema,
        output_path=str(html_output_path),
    )

    logger.info("EDA Completed! Check the /reports folder to see the results.")


if __name__ == "__main__":
    main()
