import os
import pandas as pd
from scipy.stats import pearsonr
from sklearn.model_selection import LeaveOneOut
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset.csv")


def run_analysis():
    if not os.path.exists(DATASET_PATH):
        print("Dataset CSV not found. Please run extract_features.py first.")
        return

    df = pd.read_csv(DATASET_PATH)

    if len(df) < 3:
        print("Not enough data points to run correlation analysis.")
        return

    feature_cols = [col for col in df.columns if col not in ["participant_id", "phq9_score"]]
    target_col = "phq9_score"

    print("=== Pearson Correlation Analysis with PHQ-9 ===")
    correlations = []
    for col in feature_cols:
        r, p_val = pearsonr(df[col], df[target_col])
        correlations.append({"feature": col, "pearson_r": r, "p_value": p_val})

    df_corr = pd.DataFrame(correlations).sort_values(by="p_value")
    print(df_corr.to_string(index=False))

    print("\n=== Machine Learning Evaluation (Leave-One-Out CV) ===")
    X = df[feature_cols].values
    y = df[target_col].values

    loo = LeaveOneOut()
    y_true, y_pred = [], []

    model = Ridge(alpha=1.0)

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        y_true.append(y_test[0])
        y_pred.append(pred[0])

    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    print(f"Model: Ridge Regression")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"R2 Score: {r2:.4f}")


if __name__ == "__main__":
    run_analysis()