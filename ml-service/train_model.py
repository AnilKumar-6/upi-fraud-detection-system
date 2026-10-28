
"""Train and compare fraud-detection models using an authorized labeled CSV.

Required CSV columns:
amount,hourOfDay,locationMismatch,failedAttempts,deviceChanged,transactionType,is_fraud

is_fraud must contain both classes: 0 (legitimate) and 1 (fraud).
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC


FEATURES = [
    "amount",
    "hourOfDay",
    "locationMismatch",
    "failedAttempts",
    "deviceChanged",
    "transactionType",
]

NUMERIC = ["amount", "hourOfDay", "failedAttempts"]

CATEGORICAL = [
    "locationMismatch",
    "deviceChanged",
    "transactionType",
]


def main():
    parser = argparse.ArgumentParser(
        description="Train and evaluate UPI fraud-detection models."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to an authorized labeled CSV dataset.",
    )
    args = parser.parse_args()

    # Load and validate the dataset.
    csv_path = Path(args.csv)
    if not csv_path.is_file():
        raise SystemExit(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = FEATURES + ["is_fraud"]
    missing = set(required_columns) - set(df.columns)

    if missing:
        raise SystemExit(f"CSV is missing columns: {sorted(missing)}")

    df = df[required_columns].copy()

    df["is_fraud"] = pd.to_numeric(df["is_fraud"], errors="coerce")

    if df["is_fraud"].isna().any():
        raise SystemExit("is_fraud contains missing or non-numeric values.")

    if not df["is_fraud"].isin([0, 1]).all():
        raise SystemExit("is_fraud must contain only 0 and 1.")

    y = df["is_fraud"].astype(int)
    X = df[FEATURES]

    if y.nunique() != 2:
        raise SystemExit(
            "The dataset must contain both legitimate (0) and fraud (1) rows."
        )

    if y.value_counts().min() < 2:
        raise SystemExit(
            "At least two rows per class are required for a stratified split."
        )

    # Prepare numeric and categorical features.
    prep = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUMERIC,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        (
                            "imputer",
                            SimpleImputer(strategy="most_frequent"),
                        ),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore"),
                        ),
                    ]
                ),
                CATEGORICAL,
            ),
        ]
    )

    # Candidate models.
    models = {
        "Decision Tree": DecisionTreeClassifier(
            class_weight="balanced",
            random_state=42,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            random_state=42,
        ),
        "SVM": SVC(
            probability=True,
            class_weight="balanced",
            random_state=42,
        ),
    }

    # Keep a held-out test set for evaluation and permutation importance.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    best_model = None
    best_model_name = None
    best_f1 = -1.0

    print("\nModel evaluation on held-out test data")
    print("-" * 75)

    for name, classifier in models.items():
        pipeline = Pipeline(
            steps=[
                ("prep", prep),
                ("model", classifier),
            ]
        )

        pipeline.fit(X_train, y_train)

        predictions = pipeline.predict(X_test)
        probabilities = pipeline.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, predictions)
        precision = precision_score(
            y_test, predictions, zero_division=0
        )
        recall = recall_score(
            y_test, predictions, zero_division=0
        )
        f1 = f1_score(
            y_test, predictions, zero_division=0
        )
        auc = roc_auc_score(y_test, probabilities)

        print(
            f"{name}: "
            f"accuracy={accuracy:.4f} "
            f"precision={precision:.4f} "
            f"recall={recall:.4f} "
            f"f1={f1:.4f} "
            f"roc_auc={auc:.4f}"
        )

        # Select the model with the highest held-out F1 score.
        if f1 > best_f1:
            best_model = pipeline
            best_model_name = name
            best_f1 = f1

    if best_model is None:
        raise SystemExit("Training failed: no model was selected.")

    # Measure global feature importance by shuffling one original input
    # feature at a time and measuring the change in held-out F1.
    print("\nCalculating permutation importance...")

    importance_result = permutation_importance(
        best_model,
        X_test,
        y_test,
        scoring="f1",
        n_repeats=10,
        random_state=42,
        n_jobs=1,
    )

    feature_importance = {
        feature: round(float(score), 6)
        for feature, score in zip(
            FEATURES,
            importance_result.importances_mean,
        )
    }

    importance_std = {
        feature: round(float(score), 6)
        for feature, score in zip(
            FEATURES,
            importance_result.importances_std,
        )
    }

    # IMPORTANT:
    # This artifact is now a dictionary, not a bare sklearn Pipeline.
    # Update the FastAPI loader to support this format before replacing
    # the model file used by your running application.
    output_path = Path(__file__).parent / "fraud_model.joblib"

    artifact = {
        "pipeline": best_model,
        "model_name": best_model_name,
        "feature_importance": feature_importance,
        "feature_importance_std": importance_std,
        "importance_method": "permutation importance (held-out F1)",
        "features": FEATURES,
    }

    joblib.dump(artifact, output_path)

    print(f"\nSelected model: {best_model_name}")
    print(f"Best held-out F1: {best_f1:.4f}")
    print(f"Saved model artifact to: {output_path}")

    print("\nPermutation importance (held-out F1):")
    for feature, score in sorted(
        feature_importance.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(
            f"  {feature}: {score:.6f} "
            f"(std={importance_std[feature]:.6f})"
        )


if __name__ == "__main__":
    main()
