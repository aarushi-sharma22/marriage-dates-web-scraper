"""
Combine all marriage muhurat CSVs into one file with state/district names.

Usage:
    python combine_muhurats.py

Run from the repo root (religion-india/).
Output: combined_marriage_muhurats.csv
"""

import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path("data/marriage_muhurats")
CODEBOOK = Path("data/state-district-codes.csv")
OUTPUT = Path("combined_marriage_muhurats.csv")

# --- Load codebook ---
codes = pd.read_csv(CODEBOOK)
codes = codes.dropna(subset=["state_code", "district_code"])
codes["state_code"] = codes["state_code"].astype(int)
codes["district_code"] = codes["district_code"].astype(int)
codes["state_name"] = codes["state_name"].str.strip()
codes["district_name"] = codes["district_name"].str.strip()

state_map = dict(zip(codes["state_code"], codes["state_name"]))
district_map = {
    (row.state_code, row.district_code): row.district_name
    for _, row in codes.iterrows()
}

# 6 states present in marriage_muhurats/ folders but missing from state-district-codes.csv.
# Their folders all use named CSVs so district names come from filenames.
MISSING_STATES = {
    1: "Jammu & Kashmir",
    7: "Delhi",
    24: "Gujarat",
    26: "Dadra & Nagar Haveli and Daman & Diu",
    31: "Lakshadweep",
    37: "Ladakh",
}
state_map.update(MISSING_STATES)

# --- Combine CSVs ---
all_rows = []

for state_dir in sorted(BASE_DIR.iterdir()):
    if not state_dir.is_dir():
        continue

    state_code = int(state_dir.name)
    state_name = state_map.get(state_code, f"UNMAPPED_STATE_{state_code}")

    for csv_file in sorted(state_dir.glob("*.csv")):
        fname = csv_file.stem

        if fname.isdigit():
            district_code = int(fname)
            district_name = district_map.get(
                (state_code, district_code), f"UNMAPPED_DISTRICT_{district_code}"
            )
        else:
            district_name = fname

        try:
            df = pd.read_csv(csv_file)
            df["state"] = state_name
            df["district"] = district_name
            all_rows.append(df)
        except Exception as e:
            print(f"ERROR reading {csv_file}: {e}", file=sys.stderr)

combined = pd.concat(all_rows, ignore_index=True)
combined = combined[["state", "district", "year", "month", "day"]]
combined.to_csv(OUTPUT, index=False)

print(f"Rows:      {len(combined):,}")
print(f"States:    {combined['state'].nunique()}")
print(f"Districts: {combined['district'].nunique()}")
print(f"Years:     {combined['year'].min()}-{combined['year'].max()}")
print(f"Saved to:  {OUTPUT}")