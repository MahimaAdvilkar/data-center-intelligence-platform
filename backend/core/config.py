from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

DC_CLUSTERED_CSV = DATA_DIR / "dc_clustered.csv"
DC_CLEANED_CSV = DATA_DIR / "dc_cleaned.csv"
DC_FINAL_CSV = DATA_DIR / "data_final.csv"
GRAVITY_CSV = DATA_DIR / "gravity_city_scores.csv"

RF_MODEL_PATH = MODELS_DIR / "rf_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
