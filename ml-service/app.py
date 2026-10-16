
import json
import logging
from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="UPI Fraud Scoring Service",
    version="1.4.0"
)

MODEL_PATH = Path(__file__).parent / "fraud_model.joblib"

try:
    model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
    if model is not None:
        logger.info("Model loaded: %s", MODEL_PATH)
    else:
        logger.warning("Model not found; using demo rules.")
except Exception:
    logger.exception("Model loading failed")
    model = None


class TransactionInput(BaseModel):
    senderUpi: str = Field(min_length=1, max_length=120)
    receiverUpi: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    transactionType: Literal[
        "P2P", "P2M", "BILL_PAYMENT", "OTHER"
    ]
    hourOfDay: int = Field(ge=0, le=23)
    locationMismatch: bool
    failedAttempts: int = Field(ge=0, le=100)
    deviceChanged: bool


def calculate_rule_score(tx: TransactionInput):
    score = 0.0
    reasons = []

    if tx.amount >= 50000:
        score += 0.35
        reasons.append("large amount")
    elif tx.amount >= 20000:
        score += 0.20
        reasons.append("elevated amount")

    if tx.hourOfDay <= 5 or tx.hourOfDay >= 23:
        score += 0.15
        reasons.append("unusual hour")

    if tx.locationMismatch:
        score += 0.25
        reasons.append("location mismatch")

    if tx.failedAttempts >= 3:
        score += 0.20
        reasons.append("multiple failed attempts")

    if tx.deviceChanged:
        score += 0.15
        reasons.append("changed device")

    score = min(score, 1.0)

    explanation = (
        "Demo rules only; not a validated UPI fraud model. Signals: "
        + (", ".join(reasons) if reasons else "no configured risk signals")
    )

    return score, explanation


def make_result(score, source, explanation):
    score = max(0.0, min(float(score), 1.0))

    label = (
        "HIGH_RISK" if score >= 0.60
        else "REVIEW" if score >= 0.30
        else "LOW_RISK"
    )

    return {
        "prediction": label,
        "riskScore": round(score, 4),
        "source": source,
        "explanation": explanation
    }


@app.get("/health")
def health():
    return {
        "status": "UP",
        "modelLoaded": model is not None,
        "mode": "trained-model" if model is not None else "rule-based-demo"
    }


@app.post("/predict")
async def predict(request: Request):
    # Read the actual HTTP request body instead of relying on
    # FastAPI's automatic body parsing.
    raw_body = await request.body()

    logger.info(
        "Received /predict request: content-type=%s, body-bytes=%d",
        request.headers.get("content-type"),
        len(raw_body)
    )

    if not raw_body:
        logger.error("The HTTP request arrived with an EMPTY body.")
        return JSONResponse(
            status_code=400,
            content={
                "error": "EMPTY_REQUEST_BODY",
                "message": "No JSON body reached the Python API."
            }
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
        tx = TransactionInput.model_validate(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.exception("Invalid JSON request")
        return JSONResponse(
            status_code=400,
            content={"error": "INVALID_JSON", "message": str(exc)}
        )
    except ValidationError as exc:
        logger.error("Transaction validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )

    logger.info(
        "Validated transaction: amount=%s, type=%s",
        tx.amount, tx.transactionType
    )

    if model is not None:
        try:
            type_mapping = {
                "P2P": "TRANSFER",
                "P2M": "PAYMENT",
                "BILL_PAYMENT": "PAYMENT",
                "OTHER": "DEBIT"
            }

            features = pd.DataFrame([{
                "amount": tx.amount,
                "type": type_mapping[tx.transactionType]
            }])

            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba(features)[0]
                classes = list(model.classes_)

                if 1 not in classes:
                    raise ValueError("Model has no fraud class labelled 1.")

                score = float(probabilities[classes.index(1)])
            else:
                score = float(model.predict(features)[0])

            result = make_result(
                score,
                "TRAINED_PAYSIM_MODEL",
                "Score from a PaySim model using amount and transaction type. "
                "This is not a validated UPI fraud probability."
            )

            logger.info("Prediction result: %s", result)
            return result

        except Exception:
            logger.exception("Model prediction failed; using demo rules")

    score, explanation = calculate_rule_score(tx)

    result = make_result(
        score,
        "RULE_BASED_FALLBACK",
        explanation
    )

    logger.info("Rule-based result: %s", result)
    return result
