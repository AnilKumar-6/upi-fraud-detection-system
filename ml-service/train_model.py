"""Train and compare models from an authorized labeled CSV dataset.

Expected columns:
amount,hourOfDay,locationMismatch,failedAttempts,deviceChanged,transactionType,is_fraud
is_fraud must be 0/1. This script cannot create trustworthy results without real labeled data.
"""
import argparse
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC

FEATURES = ["amount", "hourOfDay", "locationMismatch", "failedAttempts", "deviceChanged", "transactionType"]
NUMERIC = ["amount", "hourOfDay", "failedAttempts"]
CATEGORICAL = ["locationMismatch", "deviceChanged", "transactionType"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to authorized labeled CSV")
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    missing = set(FEATURES + ["is_fraud"]) - set(df.columns)
    if missing: raise SystemExit(f"CSV is missing columns: {sorted(missing)}")
    X, y = df[FEATURES], df["is_fraud"].astype(int)
    if y.nunique() < 2: raise SystemExit("is_fraud must contain both classes 0 and 1")
    prep = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL)
    ])
    models = {
        "Decision Tree": DecisionTreeClassifier(class_weight="balanced", random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "SVM": SVC(probability=True, class_weight="balanced", random_state=42)
    }
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.2, random_state=42, stratify=y)
    best, best_f1 = None, -1
    for name, clf in models.items():
        pipe = Pipeline([("prep", prep), ("model", clf)])
        pipe.fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        try: auc = roc_auc_score(yte, pipe.predict_proba(Xte)[:, 1])
        except Exception: auc = float("nan")
        p, r, f = precision_score(yte, pred, zero_division=0), recall_score(yte, pred, zero_division=0), f1_score(yte, pred, zero_division=0)
        print(f"{name}: accuracy={accuracy_score(yte,pred):.4f} precision={p:.4f} recall={r:.4f} f1={f:.4f} roc_auc={auc:.4f}")
        if f > best_f1: best, best_f1 = pipe, f
    out = Path(__file__).parent / "fraud_model.joblib"
    joblib.dump(best, out)
    print(f"Saved best model (by held-out F1) to {out}")
if __name__ == "__main__": main()
