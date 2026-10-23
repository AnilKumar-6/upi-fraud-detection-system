
"""Explainable UPI fraud scoring API.

Explanations are diagnostic sensitivity estimates, not causal proof.
"""
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sklearn.inspection import permutation_importance

app = FastAPI(
    title="UPI Fraud Scoring + Explainable AI",
    version="2.2.0",
    description=(
        "Returns transaction-level sensitivity contributions, global "
        "permutation importance, and rules-versus-ML comparison."
    ),
)

MODEL_PATH = Path(__file__).parent / "fraud_model.joblib"
DATA_PATH = Path(__file__).parent / "demo_transactions.csv"

model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

FEATURES = [
    "amount",
    "hourOfDay",
    "locationMismatch",
    "failedAttempts",
    "deviceChanged",
    "transactionType",
]

DISPLAY = {
    "amount": "Transaction amount",
    "hourOfDay": "Transaction hour",
    "locationMismatch": "Location mismatch",
    "failedAttempts": "Failed attempts",
    "deviceChanged": "Device changed",
    "transactionType": "Transaction type",
}


class TransactionInput(BaseModel):
    senderUpi: str
    receiverUpi: str
    amount: float = Field(gt=0)
    transactionType: Literal[
        "P2P", "P2M", "BILL_PAYMENT", "OTHER"
    ]
    hourOfDay: int = Field(ge=0, le=23)
    locationMismatch: bool
    failedAttempts: int = Field(ge=0, le=100)
    deviceChanged: bool


def row(tx):
    """Convert a request or feature mapping into model input fields."""
    if isinstance(tx, dict):
        return {feature: tx[feature] for feature in FEATURES}

    return {
        "amount": tx.amount,
        "hourOfDay": tx.hourOfDay,
        "locationMismatch": tx.locationMismatch,
        "failedAttempts": tx.failedAttempts,
        "deviceChanged": tx.deviceChanged,
        "transactionType": tx.transactionType,
    }


def rules_score(tx):
    """Calculate the transparent demo rules score and active triggers."""
    factors = []
    score = 0.0

    checks = [
        (tx.amount >= 50000, 0.35,
         "Large transaction amount", "amount"),
        (20000 <= tx.amount < 50000, 0.20,
         "Elevated transaction amount", "amount"),
        (tx.hourOfDay <= 5 or tx.hourOfDay >= 23, 0.15,
         "Unusual transaction hour", "hourOfDay"),
        (tx.locationMismatch, 0.25,
         "Location mismatch", "locationMismatch"),
        (tx.failedAttempts >= 3, 0.20,
         "Multiple failed attempts", "failedAttempts"),
        (tx.deviceChanged, 0.15,
         "Device changed recently", "deviceChanged"),
    ]

    for active, weight, reason, feature in checks:
        if active:
            score += weight
            factors.append({
                "feature": feature,
                "label": reason,
                "contribution": weight,
                "relativeImportance": 0.0,
            })

    score = min(score, 1.0)
    total = sum(item["contribution"] for item in factors)

    for item in factors:
        item["relativeImportance"] = (
            round(item["contribution"] / total, 4)
            if total else 0.0
        )

    return score, factors


def model_score(data):
    """Return the model's estimated positive-class probability."""
    if model is None:
        return None

    frame = pd.DataFrame([data], columns=FEATURES)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(frame)[0]
        classes = list(getattr(model, "classes_", []))

        if 1 in classes:
            score = float(probabilities[classes.index(1)])
        else:
            score = float(probabilities[-1])

    elif hasattr(model, "decision_function"):
        # A decision margin is not a calibrated probability.
        # This sigmoid is a bounded compatibility fallback only.
        margin = float(np.ravel(model.decision_function(frame))[0])
        score = 1.0 / (
            1.0 + np.exp(-np.clip(margin, -30, 30))
        )
    else:
        score = float(np.ravel(model.predict(frame))[0])

    return float(np.clip(score, 0.0, 1.0))


def model_importance():
    """Estimate global permutation importance on labeled demo data.

    Each original input feature is shuffled independently and the
    resulting change in ROC AUC is measured. This estimates global
    model reliance, not causality or per-transaction SHAP values.
    """
    if model is None or not DATA_PATH.exists():
        return []

    try:
        data = pd.read_csv(DATA_PATH)
        target = "is_fraud"
        required = FEATURES + [target]

        missing = [
            column for column in required
            if column not in data.columns
        ]

        if missing:
            print(
                "Permutation importance unavailable; missing columns:",
                missing,
            )
            return []

        X = data[FEATURES].copy()
        y = pd.to_numeric(data[target], errors="coerce")

        valid = y.notna()
        X = X.loc[valid].reset_index(drop=True)
        y = y.loc[valid].astype(int).reset_index(drop=True)

        if len(X) < 2 or y.nunique() != 2:
            print(
                "Permutation importance needs labeled examples "
                "from both classes."
            )
            return []

        result = permutation_importance(
            model,
            X,
            y,
            scoring="roc_auc",
            n_repeats=5,
            random_state=42,
        )

        # Only positive AUC drops contribute to displayed importance.
        drops = np.asarray(result.importances_mean, dtype=float)
        positive_drops = np.maximum(drops, 0.0)
        total = float(positive_drops.sum())

        if total <= 0:
            return []

        features = [
            {
                "feature": feature,
                "label": DISPLAY[feature],
                "importance": round(float(value / total), 4),
                "meanAucDrop": round(float(drop), 4),
            }
            for feature, value, drop in zip(
                FEATURES, positive_drops, drops
            )
        ]

        return sorted(
            features,
            key=lambda item: item["importance"],
            reverse=True,
        )

    except Exception as exc:
        # Explanation failure must not prevent transaction scoring.
        print(f"Permutation importance unavailable: {exc}")
        return []


def local_contributions(tx, score):
    """Estimate sensitivity by neutralizing one feature at a time.

    contribution = original score - neutralized score.

    Positive: original value corresponds to a higher model score.
    Negative: original value corresponds to a lower model score.

    This is not SHAP, causal inference, or an additive decomposition.
    """
    if model is None:
        return []

    base = row(tx)
    baseline = float(score)
    output = []

    neutral = {
        "amount": 0.0,
        "hourOfDay": 12,
        "locationMismatch": False,
        "failedAttempts": 0,
        "deviceChanged": False,
        "transactionType": "P2P",
    }

    for feature in FEATURES:
        changed = dict(base)
        changed[feature] = neutral[feature]

        try:
            neutralized_score = model_score(changed)
            delta = baseline - neutralized_score
        except Exception as exc:
            print(f"Local contribution failed for {feature}: {exc}")
            neutralized_score = baseline
            delta = 0.0

        output.append({
            "feature": feature,
            "label": DISPLAY[feature],
            "contribution": round(float(delta), 4),
            "direction": (
                "increases risk"
                if delta > 0.005
                else "decreases risk"
                if delta < -0.005
                else "little change"
            ),
            "neutralizedScore": round(
                float(neutralized_score), 4
            ),
        })

    total = sum(
        abs(item["contribution"]) for item in output
    ) or 1.0

    for item in output:
        item["relativeImportance"] = round(
            abs(item["contribution"]) / total, 4
        )

    return sorted(
        output,
        key=lambda item: abs(item["contribution"]),
        reverse=True,
    )


@app.get("/health")
def health():
    return {
        "status": "UP",
        "modelLoaded": model is not None,
        "mode": (
            "trained-model" if model is not None
            else "rule-based-demo"
        ),
    }


@app.get("/explainability/feature-importance")
def feature_importance():
    features = model_importance()

    return {
        "modelLoaded": model is not None,
        "method": (
            "permutation importance using ROC AUC on labeled demo data"
            if features
            else "unavailable: check labeled demo data and model compatibility"
        ),
        "features": features,
        "note": (
            "Permutation importance estimates global model reliance "
            "on the labeled demo dataset. It is not causal proof or "
            "a per-transaction SHAP explanation."
        ),
    }


@app.post("/debug-predict")
async def debug_predict(request: Request):
    raw_body = await request.body()

    return JSONResponse(content={
        "content_type": request.headers.get("content-type"),
        "body_length": len(raw_body),
        "body": raw_body.decode("utf-8", errors="replace"),
    })


@app.post("/predict")
def predict(tx: TransactionInput):
    rules, rule_factors = rules_score(tx)
    ml = model_score(row(tx))

    if ml is not None:
        score = ml
        source = "TRAINED_SCIKIT_LEARN_MODEL"
        factors = local_contributions(tx, ml)

        explanation = (
            "Transaction factors use single-feature neutralization. "
            "Each factor compares the original score with the score "
            "after replacing one feature with a neutral value. This is "
            "an approximate sensitivity analysis, not SHAP or causal "
            "proof. Global importance is computed separately using "
            "permutation importance with ROC AUC on labeled demo data."
        )
        xai_method = (
            "model-agnostic single-feature ablation approximation"
        )
    else:
        score = rules
        source = "RULE_BASED_DEMO"
        factors = rule_factors

        explanation = (
            "No trained model file is available; this result uses "
            "transparent demo rules and is not a validated ML prediction."
        )
        xai_method = "transparent rules contribution"

    label = (
        "HIGH_RISK" if score >= 0.60
        else "REVIEW" if score >= 0.30
        else "LOW_RISK"
    )

    return {
        "prediction": label,
        "riskScore": round(float(score), 4),
        "mlScore": (
            round(float(ml), 4) if ml is not None else None
        ),
        "rulesScore": round(float(rules), 4),
        "scoreDifference": (
            round(float(ml - rules), 4)
            if ml is not None else None
        ),
        "source": source,
        "explanation": explanation,
        "contributingFactors": factors[:6],
        "ruleTriggers": rule_factors,
        "modelFeatureImportance": model_importance(),
        "xaiMethod": xai_method,
        "disclaimer": (
            "Decision-support demo only. A risk score is not proof "
            "of fraud. Validate model quality, calibration, fairness, "
            "and explanations before real-world use."
        ),
    }
