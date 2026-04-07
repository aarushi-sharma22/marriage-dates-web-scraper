"""
Add columns E-J to the combined marriage muhurats CSV using chaumasa dates.

Columns computed:
  E - last_chaumasa_end_date: the most recent Prabodhini Ekadashi before this date
  F - muhurats_in_month: count of auspicious dates in same month+year for this district
  G - muhurats_in_year: count of auspicious dates in same year for this district
  H - muhurats_between_chaumasa: total muhurats from last chaumasa end to next chaumasa start
  I - muhurat_number_since_chaumasa: running count since last chaumasa ended (1, 2, 3...)
  J - muhurats_till_next_chaumasa: countdown to next chaumasa (H - I)

Usage:
    python compute_columns.py

Expects:
    - combined_marriage_muhurats.csv (from combine_muhurats.py)
    - data/chaumasa_dates.csv (from scrape_chaumasa.py)

Output: combined_marriage_muhurats_full.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime

# --- Load data ---
print("Loading data...")
df = pd.read_csv("combined_marriage_muhurats.csv")

# Convert month names to numbers for date creation
month_map = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}
df["month_num"] = df["month"].map(month_map)
df["date"] = pd.to_datetime(df[["year", "month_num", "day"]].rename(
    columns={"month_num": "month", "day": "day"}
))

# Load chaumasa dates
chaumasa = pd.read_csv("data/chaumasa_dates.csv")
chaumasa["chaumasa_start"] = pd.to_datetime(chaumasa["chaumasa_start"])
chaumasa["chaumasa_end"] = pd.to_datetime(chaumasa["chaumasa_end"])

# Build sorted arrays of chaumasa start and end dates
chaumasa_starts = chaumasa["chaumasa_start"].dropna().sort_values().values
chaumasa_ends = chaumasa["chaumasa_end"].dropna().sort_values().values

print(f"Loaded {len(df):,} rows, {len(chaumasa)} chaumasa years")

# --- Column F: muhurats in month ---
print("Computing F (muhurats per month)...")
month_counts = df.groupby(["state", "district", "year", "month_num"]).size().reset_index(name="muhurats_in_month")
df = df.merge(month_counts, on=["state", "district", "year", "month_num"], how="left")

# --- Column G: muhurats in year ---
print("Computing G (muhurats per year)...")
year_counts = df.groupby(["state", "district", "year"]).size().reset_index(name="muhurats_in_year")
df = df.merge(year_counts, on=["state", "district", "year"], how="left")

# --- Column E: last chaumasa end date ---
print("Computing E (last chaumasa end date)...")
# For each muhurat date, find the most recent chaumasa_end that is <= this date
dates_np = df["date"].values
idx = np.searchsorted(chaumasa_ends, dates_np, side="right") - 1
df["last_chaumasa_end_date"] = pd.NaT
valid = idx >= 0
df.loc[valid, "last_chaumasa_end_date"] = chaumasa_ends[idx[valid]]

# --- Columns H, I, J: inter-chaumasa window ---
print("Computing H, I, J (inter-chaumasa columns)...")

# For each muhurat, determine if it falls in an inter-chaumasa window:
# i.e., after a chaumasa_end and before the next chaumasa_start
# Find next chaumasa_start after each date
idx_next_start = np.searchsorted(chaumasa_starts, dates_np, side="right")
next_chaumasa_start = pd.Series(pd.NaT, index=df.index)
valid_start = idx_next_start < len(chaumasa_starts)
next_chaumasa_start[valid_start] = chaumasa_starts[idx_next_start[valid_start]]

# A muhurat is in inter-chaumasa if: last_chaumasa_end <= date < next_chaumasa_start
in_window = valid & valid_start & (df["date"].values >= df["last_chaumasa_end_date"].values)
# Also ensure it's before next chaumasa start
in_window = in_window & (df["date"].values < next_chaumasa_start.values)

df["next_chaumasa_start"] = next_chaumasa_start
df["in_inter_chaumasa"] = in_window

# H: total muhurats in each inter-chaumasa window per district
# Group by district + last_chaumasa_end_date, count rows where in_window
print("  Computing H (total muhurats in window)...")
window_df = df[df["in_inter_chaumasa"]].copy()
window_counts = window_df.groupby(
    ["state", "district", "last_chaumasa_end_date"]
).size().reset_index(name="muhurats_between_chaumasa")
df = df.merge(window_counts, on=["state", "district", "last_chaumasa_end_date"], how="left")

# I: running count within each window per district
print("  Computing I (running count)...")
df["muhurat_number_since_chaumasa"] = np.nan
if len(window_df) > 0:
    window_df = window_df.sort_values(["state", "district", "last_chaumasa_end_date", "date"])
    window_df["muhurat_number_since_chaumasa"] = window_df.groupby(
        ["state", "district", "last_chaumasa_end_date"]
    ).cumcount() + 1
    df.loc[window_df.index, "muhurat_number_since_chaumasa"] = window_df["muhurat_number_since_chaumasa"]

# J: countdown
print("  Computing J (countdown)...")
df["muhurats_till_next_chaumasa"] = df["muhurats_between_chaumasa"] - df["muhurat_number_since_chaumasa"]

# --- Clean up and save ---
df["last_chaumasa_end_date"] = df["last_chaumasa_end_date"].dt.strftime("%Y-%m-%d")

output_cols = [
    "state", "district", "year", "month", "day",
    "last_chaumasa_end_date",
    "muhurats_in_month",
    "muhurats_in_year",
    "muhurats_between_chaumasa",
    "muhurat_number_since_chaumasa",
    "muhurats_till_next_chaumasa",
]
df_out = df[output_cols]
df_out.to_csv("combined_marriage_muhurats_full.csv", index=False)

print(f"\nSaved {len(df_out):,} rows to combined_marriage_muhurats_full.csv")
print(f"Columns: {list(df_out.columns)}")
print(f"\nSample (Anantnag, 1900):")
sample = df_out[(df_out["district"] == "Anantnag") & (df_out["year"] == 1900)].tail(10)
print(sample.to_string(index=False))