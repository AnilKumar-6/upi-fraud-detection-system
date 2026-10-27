"""Explainable UPI fraud scoring API. Explanations are diagnostic, not causal proof."""
from pathlib import Path
from typing import Literal
import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="UPI Fraud Scoring + Explainable AI", version="2.0.0",
              description="Returns per-transaction factor contributions, model-level importance, and a rules-vs-ML comparison.")
MODEL_PATH = Path(__file__).parent / "fraud_model.joblib"
model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
FEATURES = ["amount", "hourOfDay", "locationMismatch", "failedAttempts", "deviceChanged", "transactionType"]
DISPLAY = {"amount":"Transaction amount", "hourOfDay":"Transaction hour", "locationMismatch":"Location mismatch", "failedAttempts":"Failed attempts", "deviceChanged":"Device changed", "transactionType":"Transaction type"}

class TransactionInput(BaseModel):
    senderUpi: str
    receiverUpi: str
    amount: float = Field(gt=0)
    transactionType: Literal["P2P", "P2M", "BILL_PAYMENT", "OTHER"]
    hourOfDay: int = Field(ge=0, le=23)
    locationMismatch: bool
    failedAttempts: int = Field(ge=0, le=100)
    deviceChanged: bool

def row(tx):
    return {"amount":tx.amount,"hourOfDay":tx.hourOfDay,"locationMismatch":tx.locationMismatch,
            "failedAttempts":tx.failedAttempts,"deviceChanged":tx.deviceChanged,"transactionType":tx.transactionType}

def rules_score(tx):
    factors=[]; score=0.0
    checks=[(tx.amount>=50000, .35, "Large transaction amount", "amount"),
            (20000<=tx.amount<50000, .20, "Elevated transaction amount", "amount"),
            (tx.hourOfDay<=5 or tx.hourOfDay>=23, .15, "Unusual transaction hour", "hourOfDay"),
            (tx.locationMismatch, .25, "Location mismatch", "locationMismatch"),
            (tx.failedAttempts>=3, .20, "Multiple failed attempts", "failedAttempts"),
            (tx.deviceChanged, .15, "Device changed recently", "deviceChanged")]
    for active, weight, reason, feature in checks:
        if active:
            score += weight; factors.append({"feature":feature,"label":reason,"contribution":weight,"relativeImportance":0})
    score=min(score,1.0)
    total=sum(f["contribution"] for f in factors)
    for f in factors: f["relativeImportance"]=round(f["contribution"]/total,4) if total else 0
    return score, factors

def model_score(data):
    if model is None: return None
    import pandas as pd
    frame=pd.DataFrame([data],columns=FEATURES)
    if hasattr(model,"predict_proba"):
        classes=list(getattr(model,"classes_",[]))
        probs=model.predict_proba(frame)[0]
        score=float(probs[classes.index(1)]) if 1 in classes else float(probs[-1])
    else: score=float(model.predict(frame)[0])
    return float(np.clip(score,0,1))

def model_importance():
    if model is None: return []
    estimator = model
    if hasattr(model,"named_steps"):
        estimator=model.named_steps.get("model",list(model.named_steps.values())[-1])
        prep=model.named_steps.get("prep")
        if prep is not None and hasattr(estimator,"feature_importances_"):
            names=[]
            try: names=list(prep.get_feature_names_out())
            except Exception: pass
            vals=np.asarray(estimator.feature_importances_,dtype=float)
            # Collapse one-hot encoded categories into original feature families.
            collapsed={f:0.0 for f in FEATURES}
            for n,v in zip(names,vals):
                cleaned=n.split("__",1)[-1]
                match=next((f for f in FEATURES if cleaned==f or cleaned.startswith(f+"_")),None)
                if match: collapsed[match]+=float(v)
            denom=sum(collapsed.values()) or 1
            return sorted([{"feature":k,"label":DISPLAY[k],"importance":round(v/denom,4)} for k,v in collapsed.items()],key=lambda x:x["importance"],reverse=True)
    if hasattr(estimator,"feature_importances_"):
        vals=np.asarray(estimator.feature_importances_,dtype=float); denom=vals.sum() or 1
        return sorted([{"feature":k,"label":DISPLAY[k],"importance":round(float(v/denom),4)} for k,v in zip(FEATURES,vals)],key=lambda x:x["importance"],reverse=True)
    if hasattr(estimator,"coef_"):
        vals=np.abs(np.asarray(estimator.coef_).ravel())
        if len(vals)==len(FEATURES):
            denom=vals.sum() or 1
            return sorted([{"feature":k,"label":DISPLAY[k],"importance":round(float(v/denom),4)} for k,v in zip(FEATURES,vals)],key=lambda x:x["importance"],reverse=True)
    return []

def local_contributions(tx, score):
    """Model-agnostic ablation approximation: compare score with one feature neutralized.
    These are local sensitivity estimates, not SHAP values or causal explanations."""
    if model is None: return []
    import pandas as pd
    base=row(tx); baseline=float(score); out=[]
    neutral={"amount":0.0,"hourOfDay":12,"locationMismatch":False,"failedAttempts":0,"deviceChanged":False,"transactionType":"P2P"}
    for feature in FEATURES:
        changed=dict(base); changed[feature]=neutral[feature]
        try: delta=baseline-model_score(changed)
        except Exception: delta=0.0
        out.append({"feature":feature,"label":DISPLAY[feature],"contribution":round(float(delta),4),"direction":"increases risk" if delta>0.005 else "decreases risk" if delta< -0.005 else "little change"})
    total=sum(abs(x["contribution"]) for x in out) or 1
    for x in out: x["relativeImportance"]=round(abs(x["contribution"])/total,4)
    return sorted(out,key=lambda x:abs(x["contribution"]),reverse=True)

@app.get("/health")
def health():
    return {"status":"UP","modelLoaded":model is not None,"mode":"trained-model" if model is not None else "rule-based-demo"}

@app.get("/explainability/feature-importance")
def feature_importance():
    return {"modelLoaded":model is not None,"method":"model-native importance when available; otherwise unavailable","features":model_importance(),"note":"Importance indicates model reliance, not causality."}

@app.post("/predict")
def predict(tx: TransactionInput):
    rules, rule_factors=rules_score(tx)
    ml=model_score(row(tx))
    if ml is not None:
        score=ml; source="TRAINED_SCIKIT_LEARN_MODEL"
        factors=local_contributions(tx,ml)
        explanation="Local feature ablation compares this prediction with a neutralized feature. It is an approximate sensitivity explanation, not SHAP or causal proof."
    else:
        score=rules; source="RULE_BASED_DEMO"; factors=rule_factors
        explanation="No trained model file found; this result uses demo rules only and is not a validated ML prediction."
    label="HIGH_RISK" if score>=.60 else "REVIEW" if score>=.30 else "LOW_RISK"
    return {"prediction":label,"riskScore":round(score,4),"mlScore":round(ml,4) if ml is not None else None,
            "rulesScore":round(rules,4),"scoreDifference":round(ml-rules,4) if ml is not None else None,
            "source":source,"explanation":explanation,"contributingFactors":factors[:6],
            "ruleTriggers":rule_factors,"modelFeatureImportance":model_importance(),
            "xaiMethod":"model-agnostic single-feature ablation approximation" if ml is not None else "transparent rules contribution",
            "disclaimer":"Decision-support demo only. Validate model quality, calibration, fairness and explanations before real-world use."}
