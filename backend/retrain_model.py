"""
Retrains the Random Forest cluster classifier on the current sklearn version
and saves fresh rf_model.pkl and scaler.pkl to backend/models/.
Run once: python backend/retrain_model.py
"""
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from backend.core.config import DC_CLUSTERED_CSV, RF_MODEL_PATH, SCALER_PATH

FEATURE_COLS = [
    "ENERGY", "AREA", "IT EQUIPMENT POWER", "State_Aggregated_PUE",
    "FULL_CABINETS", "PARTIAL_CABINETS", "SHARED_RACKSPACE", "CAGES",
    "SUITES", "BUILD_TO_SUIT", "FOOTPRINTS", "REMOTE_HANDS",
    "YEAR_OPERATIONAL", "State_Aggregated_IXP_Count",
]

df = pd.read_csv(DC_CLUSTERED_CSV)

# Boolean columns stored as strings — convert to int
bool_cols = ["FULL_CABINETS","PARTIAL_CABINETS","SHARED_RACKSPACE","CAGES",
             "SUITES","BUILD_TO_SUIT","FOOTPRINTS","REMOTE_HANDS"]
for col in bool_cols:
    df[col] = df[col].astype(str).str.lower().map({"true": 1, "false": 0, "1": 1, "0": 0}).fillna(0).astype(int)

X = df[FEATURE_COLS]
y = df["Cluster"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

print("Classification Report:")
print(classification_report(y_test, rf.predict(X_test)))

joblib.dump(rf, RF_MODEL_PATH)
joblib.dump(scaler, SCALER_PATH)
print(f"Saved rf_model.pkl to {RF_MODEL_PATH}")
print(f"Saved scaler.pkl to {SCALER_PATH}")
