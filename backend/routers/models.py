"""
STRYDER AI - Models Router
=============================
Endpoints for ML model inference.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/models", tags=["ML Models"])


class PredictionRequest(BaseModel):
    input_data: dict


@router.post("/eta/predict")
async def predict_eta(req: PredictionRequest):
    """Predict ETA for a shipment."""
    try:
        from backend.ml_models.eta_model import predict
        return predict(req.input_data)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/delay/predict")
async def predict_delay(req: PredictionRequest):
    """Predict delay risk."""
    try:
        from backend.ml_models.delay_model import predict
        return predict(req.input_data)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/carrier/predict")
async def predict_carrier(req: PredictionRequest):
    """Predict carrier reliability."""
    try:
        from backend.ml_models.carrier_model import predict
        return predict(req.input_data)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/congestion/predict")
async def predict_congestion(req: PredictionRequest):
    """Predict hub congestion."""
    try:
        from backend.ml_models.hub_congestion_model import predict
        return predict(req.input_data)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/cascade/predict")
async def predict_cascade(req: PredictionRequest):
    """Predict cascade failure."""
    try:
        from backend.ml_models.cascade_model import predict
        return predict(req.input_data)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/info")
async def model_info():
    """Get info about all available models."""
    return {
        "models": [
            {"name": "eta_prediction", "type": "regression", "endpoint": "/api/models/eta/predict"},
            {"name": "delay_risk", "type": "classification", "endpoint": "/api/models/delay/predict"},
            {"name": "carrier_reliability", "type": "regression", "endpoint": "/api/models/carrier/predict"},
            {"name": "hub_congestion", "type": "classification", "endpoint": "/api/models/congestion/predict"},
            {"name": "cascade_failure", "type": "classification", "endpoint": "/api/models/cascade/predict"},
        ]
    }
