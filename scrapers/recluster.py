"""
Re-runs K-Means clustering on the full dc_cleaned.csv (203 records)
and writes a new dc_clustered.csv with updated Cluster, PCA1, PCA2 columns.

Run: python scrapers/recluster.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "backend" / "data"

CLEANED_CSV  = DATA_DIR / "dc_cleaned.csv"
CLUSTERED_CSV = DATA_DIR / "dc_clustered.csv"

BOOL_COLS = [
    "FULL_CABINETS","PARTIAL_CABINETS","SHARED_RACKSPACE","CAGES",
    "SUITES","BUILD_TO_SUIT","FOOTPRINTS","REMOTE_HANDS",
]

FEATURE_COLS = [
    "ENERGY", "AREA", "IT EQUIPMENT POWER", "State_Aggregated_PUE",
    *BOOL_COLS,
    "YEAR_OPERATIONAL", "State_Aggregated_IXP_Count",
]

df = pd.read_csv(CLEANED_CSV)
print(f"Loaded {len(df)} records from {CLEANED_CSV}")

# Normalise booleans
for col in BOOL_COLS:
    df[col] = df[col].astype(str).str.lower().map(
        {"true": 1, "false": 0, "yes": 1, "no": 0, "1": 1, "0": 0}
    ).fillna(0).astype(int)

# Drop rows with missing features
df = df.dropna(subset=FEATURE_COLS).reset_index(drop=True)
print(f"After dropping nulls: {len(df)} records")

X = df[FEATURE_COLS].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# K-Means with 3 clusters (same as original)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df["Cluster"] = kmeans.fit_predict(X_scaled)

# PCA for 2D visualisation
pca = PCA(n_components=2, random_state=42)
pca_coords = pca.fit_transform(X_scaled)
df["PCA1"] = pca_coords[:, 0]
df["PCA2"] = pca_coords[:, 1]

df.to_csv(CLUSTERED_CSV, index=False)
print(f"Saved {len(df)} clustered records → {CLUSTERED_CSV}")
print(f"Cluster distribution:\n{df['Cluster'].value_counts().sort_index()}")
print(f"Explained variance: {pca.explained_variance_ratio_.round(3)}")
