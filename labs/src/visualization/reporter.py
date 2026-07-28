# src/visualization/reporter.py
import logging
import os

import pandas as pd
import polars as pl

logger = logging.getLogger(__name__)


def generate_descriptive_html(
    df_summary: pl.DataFrame, original_schema: dict, output_path: str
):
    """
    Generates a static HTML report with row-by-row descriptive statistics.
    Inserts a row at the top displaying the original data types.
    The first column is frozen for easy horizontal scrolling.
    """
    # 1. Convert to Pandas
    df_pd = df_summary.to_pandas()
    stat_col = df_pd.columns[
        0
    ]  # Gets the name of the first column (usually 'statistic')

    # 2. Build a new row containing the data types
    dtype_row = {stat_col: "data_type"}
    for col in df_pd.columns[1:]:
        # Get the string representation of the Polars data type
        dtype_row[col] = str(original_schema.get(col, "unknown"))

    # 3. Insert the data_type row at the very top of the DataFrame
    df_pd = pd.concat([pd.DataFrame([dtype_row]), df_pd], ignore_index=True)

    # 4. Generate the HTML table
    html_table = df_pd.to_html(
        index=False,
        classes="descriptive-table",
        justify="left",
        float_format=lambda x: f"{x:.2f}",
    )

    # 5. Build the final HTML string
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Descriptive EDA Report</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #333; background-color: #f4f7f6; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .container {{ max-width: 1400px; margin: auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .table-container {{ overflow-x: auto; margin-top: 20px; max-height: 80vh; }}
            
            .descriptive-table {{ border-collapse: collapse; width: 100%; }}
            .descriptive-table th, .descriptive-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; font-size: 13px; white-space: nowrap; }}
            
            /* Sticky Header */
            .descriptive-table th {{ background-color: #2c3e50; color: white; position: sticky; top: 0; text-transform: uppercase; z-index: 2; }}
            
            /* Alternating row colors */
            .descriptive-table tr:nth-child(even) td {{ background-color: #f9f9f9; }}
            .descriptive-table tr:hover td {{ background-color: #f1f1f1; }}
            
            /* Freeze the first column */
            .descriptive-table th:first-child,
            .descriptive-table td:first-child {{
                position: sticky;
                left: 0;
                background-color: #fff;
                z-index: 1;
                border-right: 2px solid #bdc3c7;
                font-weight: bold;
                text-transform: uppercase;
            }}
            
            /* Highlight the data_type row specifically */
            .descriptive-table tr:first-child td {{
                background-color: #e8f4f8 !important;
                font-weight: bold;
                color: #2980b9;
            }}
            
            /* Hover/Z-index fixes for frozen column */
            .descriptive-table tr:nth-child(even) td:first-child {{ background-color: #f9f9f9; }}
            .descriptive-table tr:hover td:first-child {{ background-color: #f1f1f1; }}
            .descriptive-table th:first-child {{ background-color: #2c3e50; z-index: 3; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Variable Descriptive Analysis</h1>
            <p>Row-by-row statistics. The first row indicates the <strong>Data Type</strong> for each feature. Scroll horizontally to view all columns.</p>
            <div class="table-container">
                {html_table}
            </div>
        </div>
    </body>
    </html>
    """

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Descriptive HTML report generated at: {output_path}")
