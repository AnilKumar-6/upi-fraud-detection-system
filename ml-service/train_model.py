import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()

    df = pd.read_csv(
        args.csv,
        usecols=["amount", "type", "isFraud"]
    )
    df = df.dropna(subset=["amount", "type", "isFraud"])

    # Limit training size while preserving both classes.
    if len(df) > 100000:
        df = df.sample(n=100000, random_state=42)

    # Ensure the sample still contains both legitimate and fraud examples.
    if df["isFraud"].nunique() < 2:
        raise SystemExit(
            "Sample contains only one class. Increase the sample size or "
            "use a stratified sampling approach."
        )

    X = df[["amount", "type"]].copy()
    X["amount"] = pd.to_numeric(X["amount"], errors="coerce")
    X = X.dropna(subset=["amount"])
    y = df.loc[X.index, "isFraud"].astype(int)

    prep = ColumnTransformer([
        ("amount", SimpleImputer(strategy="median"), ["amount"]),
        ("type", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), ["type"])
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = Pipeline([
        ("prep", prep),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        ))
    ])

    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]

    print(f"Accuracy:  {accuracy_score(y_test, pred):.4f}")
    print(f"Precision: {precision_score(y_test, pred, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(y_test, pred, zero_division=0):.4f}")
    print(f"F1 score:  {f1_score(y_test, pred, zero_division=0):.4f}")
    print(f"ROC AUC:   {roc_auc_score(y_test, prob):.4f}")

    out = Path(__file__).parent / "fraud_model.joblib"
    joblib.dump(model, out)
    print(f"Model saved to: {out}")

if __name__ == "__main__":
    main()
