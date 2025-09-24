from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI(title="Results Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "results"}


@app.get("/v1/experiments/{experiment_id}/summary")
def get_summary(experiment_id: str):
    # Stubbed aggregated response
    return {
        "experiment_id": experiment_id,
        "summary": {
            "conversion": {"control_cr": 0.4, "treatment_cr": 0.5, "p_value": 0.04, "lift": 0.25},
            "revenue": {"p_value": 0.06, "t_stat": 1.89},
        },
        "artifacts": [],
    }


