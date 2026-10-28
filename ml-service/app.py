
"""Explainable UPI fraud scoring API.
Explanations are diagnostic approximations, not causal proof.
"""

from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="UPI Fraud Scoring + Explainable AI",
    version="2.2.0",
    description=(
        "Returns transaction-level explanations, global feature "
        "importance, and a rules-versus-ML comparison."
    ),
)

# Allow the local Spring Boot dashboard to call the Python API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

MODEL_PATH = Path(__file__).parent / "fraud_model.joblib"

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


def load_model_artifact():
    """Load either the newer dictionary artifact or a legacy model."""
    if not MODEL_PATH.exists():
        return None, {}, "No trained model artifact found"

    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception as exc:
        print(f"Model loading failed: {exc}")
        return None, {}, "Model artifact could not be loaded"

    if isinstance(artifact, dict) and "pipeline" in artifact:
        loaded_model = artifact["pipeline"]
        saved_importance = artifact.get("feature_importance", {}) or {}
        importance_method = artifact.get(
            "importance_method",
            "permutation importance (held-out F1)",
        )
    else:
        loaded_model = artifact
        saved_importance = {}
        importance_method = "model-native importance when available"

    return loaded_model, saved_importance, importance_method


model, SAVED_IMPORTANCE, IMPORTANCE_METHOD = load_model_artifact()


class TransactionInput(BaseModel):
    senderUpi: str = Field(min_length=1, max_length=120)
    receiverUpi: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0, allow_inf_nan=False)
    transactionType: Literal["P2P", "P2M", "BILL_PAYMENT", "OTHER"]
    hourOfDay: int = Field(ge=0, le=23)
    locationMismatch: bool
    failedAttempts: int = Field(ge=0, le=100)
    deviceChanged: bool


def row(tx):
    """Convert the request into the model's expected feature schema."""
    return {
        "amount": tx.amount,
        "hourOfDay": tx.hourOfDay,
        "locationMismatch": tx.locationMismatch,
        "failedAttempts": tx.failedAttempts,
        "deviceChanged": tx.deviceChanged,
        "transactionType": tx.transactionType,
    }


def rules_score(tx):
    """Calculate the demo rules score and list the active rule triggers."""
    factors = []
    score = 0.0

    checks = [
        (tx.amount >= 50000, 0.35, "Large transaction amount", "amount"),
        (
            20000 <= tx.amount < 50000,
            0.20,
            "Elevated transaction amount",
            "amount",
        ),
        (
            tx.hourOfDay <= 5 or tx.hourOfDay >= 23,
            0.15,
            "Unusual transaction hour",
            "hourOfDay",
        ),
        (
            tx.locationMismatch,
            0.25,
            "Location mismatch",
            "locationMismatch",
        ),
        (
            tx.failedAttempts >= 3,
            0.20,
            "Multiple failed attempts",
            "failedAttempts",
        ),
        (
            tx.deviceChanged,
            0.15,
            "Device changed recently",
            "deviceChanged",
        ),
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
            if total > 0
            else 0.0
        )

    return score, factors


def model_score(data):
    """Return a bounded model score, or None if no model is loaded."""
    if model is None:
        return None

    frame = pd.DataFrame([data], columns=FEATURES)

    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(frame))[0]
        classes = list(getattr(model, "classes_", []))

        if len(probabilities) == 0:
            raise ValueError("The model returned no probabilities.")

        if 1 in classes:
            score = float(probabilities[classes.index(1)])
        elif "1" in classes:
            score = float(probabilities[classes.index("1")])
        else:
            score = float(probabilities[-1])

    elif hasattr(model, "decision_function"):
        # This sigmoid conversion is only a demo display score.
        # It is not a calibrated fraud probability.
        margin = float(
            np.asarray(model.decision_function(frame)).ravel()[0]
        )
        score = 1.0 / (
            1.0 + np.exp(-np.clip(margin, -50, 50))
        )

    else:
        prediction = np.asarray(model.predict(frame)).ravel()

        if len(prediction) == 0:
            raise ValueError("The model returned no prediction.")

        score = float(prediction[0])

    return float(np.clip(score, 0.0, 1.0))


def model_importance():
    """Return saved permutation importance or supported native importance."""
    if model is None:
        return []

    if isinstance(SAVED_IMPORTANCE, dict) and SAVED_IMPORTANCE:
        return sorted(
            [
                {
                    "feature": feature,
                    "label": DISPLAY.get(feature, feature),
                    "importance": round(float(value), 6),
                }
                for feature, value in SAVED_IMPORTANCE.items()
                if feature in FEATURES
            ],
            key=lambda item: item["importance"],
            reverse=True,
        )

    estimator = model
    prep = None

    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get(
            "model",
            list(model.named_steps.values())[-1],
        )
        prep = model.named_steps.get("prep")

    if prep is not None and hasattr(estimator, "feature_importances_"):
        try:
            names = list(prep.get_feature_names_out())
            values = np.asarray(
                estimator.feature_importances_,
                dtype=float,
            )
            collapsed = {feature: 0.0 for feature in FEATURES}

            for name, value in zip(names, values):
                cleaned = name.split("__", 1)[-1]

                matched = next(
                    (
                        feature
                        for feature in FEATURES
                        if cleaned == feature
                        or cleaned.startswith(feature + "_")
                    ),
                    None,
                )

                if matched:
                    collapsed[matched] += float(value)

            denominator = sum(collapsed.values())

            if denominator > 0:
                return sorted(
                    [
                        {
                            "feature": feature,
                            "label": DISPLAY[feature],
                            "importance": round(
                                value / denominator, 6
                            ),
                        }
                        for feature, value in collapsed.items()
                    ],
                    key=lambda item: item["importance"],
                    reverse=True,
                )

        except (ValueError, AttributeError, TypeError):
            pass

    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(
            estimator.feature_importances_,
            dtype=float,
        )

        if len(values) == len(FEATURES):
            denominator = float(np.abs(values).sum())

            if denominator > 0:
                return sorted(
                    [
                        {
                            "feature": feature,
                            "label": DISPLAY[feature],
                            "importance": round(
                                float(abs(value) / denominator), 6
                            ),
                        }
                        for feature, value in zip(FEATURES, values)
                    ],
                    key=lambda item: item["importance"],
                    reverse=True,
                )

    if hasattr(estimator, "coef_"):
        values = np.abs(
            np.asarray(estimator.coef_, dtype=float)
        )

        if values.ndim > 1:
            values = values.sum(axis=0)

        values = values.ravel()

        if len(values) == len(FEATURES):
            denominator = float(values.sum())

            if denominator > 0:
                return sorted(
                    [
                        {
                            "feature": feature,
                            "label": DISPLAY[feature],
                            "importance": round(
                                float(value / denominator), 6
                            ),
                        }
                        for feature, value in zip(FEATURES, values)
                    ],
                    key=lambda item: item["importance"],
                    reverse=True,
                )

    return []


def local_contributions(tx, score):
    """Estimate local sensitivity by neutralizing one feature at a time.

    These are approximate sensitivity estimates, not SHAP values
    and not causal explanations.
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
            changed_score = model_score(changed)
            delta = (
                baseline - changed_score
                if changed_score is not None
                else 0.0
            )
        except (ValueError, TypeError, AttributeError, IndexError):
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
            "trained-model"
            if model is not None
            else "rule-based-demo"
        ),
        "modelMessage": (
            None if model is not None else IMPORTANCE_METHOD
        ),
    }


@app.get("/explainability/feature-importance")
def feature_importance():
    features = model_importance()

    if isinstance(SAVED_IMPORTANCE, dict) and SAVED_IMPORTANCE:
        method = IMPORTANCE_METHOD
    elif features:
        method = "model-native importance"
    else:
        method = "unavailable for this model artifact"

    return {
        "modelLoaded": model is not None,
        "method": method,
        "features": features,
        "note": (
            "Permutation importance measures performance change when "
            "a feature is shuffled on held-out data. It indicates model "
            "reliance on the evaluation dataset, not causality. Native "
            "importance methods have different interpretations."
        ),
    }


@app.post("/predict")
def predict(tx: TransactionInput):
    rules, rule_factors = rules_score(tx)

    try:
        ml = model_score(row(tx))
    except (ValueError, TypeError, AttributeError, IndexError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed: {exc}",
        ) from exc

    if ml is not None:
        score = ml
        source = "TRAINED_SCIKIT_LEARN_MODEL"
        factors = local_contributions(tx, ml)
        explanation = (
            "Local feature ablation compares this prediction with a "
            "neutralized feature. It is an approximate sensitivity "
            "explanation, not SHAP or causal proof."
        )
    else:
        score = rules
        source = "RULE_BASED_DEMO"
        factors = rule_factors
        explanation = (
            "No trained model is loaded; this result uses demo rules "
            "only and is not a validated ML prediction."
        )

    label = (
        "HIGH_RISK"
        if score >= 0.60
        else "REVIEW"
        if score >= 0.30
        else "LOW_RISK"
    )

    return {
        "prediction": label,
        "riskScore": round(score, 4),
        "mlScore": round(ml, 4) if ml is not None else None,
        "rulesScore": round(rules, 4),
        "scoreDifference": (
            round(ml - rules, 4) if ml is not None else None
        ),
        "source": source,
        "explanation": explanation,
        "contributingFactors": factors[:6],
        "ruleTriggers": rule_factors,
        "modelFeatureImportance": model_importance(),
        "xaiMethod": (
            "model-agnostic single-feature ablation approximation"
            if ml is not None
            else "transparent rules contribution"
        ),
        "disclaimer": (
            "Decision-support demo only. Validate model quality, "
            "calibration, fairness and explanations before real-world use."
        ),
    }
