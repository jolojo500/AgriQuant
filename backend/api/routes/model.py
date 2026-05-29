import json

from fastapi import APIRouter, HTTPException
from api.schemas import TrainingHistoryResponse, TrainingRun, TrainingRunSummary
from db.queries import read_latest_training_run, read_training_history

router = APIRouter()

@router.get("/model/latest",  response_model=TrainingRun)
def get_latest_model():
    run = read_latest_training_run()
    if not run:
        raise HTTPException(status_code=404, detail="No training run found")
    
    if isinstance(run.get("feature_importance"), str): #jsonb could come as a string if I dont parse it
        run["feature_importance"] = json.loads(run["feature_importance"])

    return TrainingRun(**run)

@router.get("/model/history", response_model=TrainingHistoryResponse)
def get_model_history():
    runs = read_training_history()
    return TrainingHistoryResponse(
        runs=[TrainingRunSummary(**r) for r in runs]
    )