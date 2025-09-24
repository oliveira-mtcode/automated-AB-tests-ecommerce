from fastapi import FastAPI
from fastapi.responses import JSONResponse
import polars as pl
from scipy import stats
from typing import Literal

app = FastAPI(title="Analytics Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics"}


@app.post("/v1/analytics/run")
def run_analytics(payload: dict):
    # Stub: In practice fetch curated Parquet by experiment_id
    experiment_id = payload.get("experiment_id")
    metrics = payload.get("metrics", ["conversion"])  # conversion | revenue
    ci = float(payload.get("ci", 0.95))

    # Generate tiny demo data frame
    df = pl.DataFrame({
        "variant": ["control"] * 100 + ["treatment"] * 100,
        "converted": [0] * 60 + [1] * 40 + [0] * 50 + [1] * 50,
        "revenue": [0.0] * 60 + [50.0] * 40 + [0.0] * 50 + [55.0] * 50,
    })

    summary = {}
    if "conversion" in metrics:
        conv = df.group_by("variant").agg(pl.col("converted").mean().alias("cr"))
        c = float(conv.filter(pl.col("variant") == "control")["cr"][0])
        t = float(conv.filter(pl.col("variant") == "treatment")["cr"][0])
        table = pl.DataFrame({
            "variant": ["control", "treatment"],
            "success": [int(40), int(50)],
            "fail": [int(60), int(50)],
        })
        chi2, p, _, _ = stats.chi2_contingency([
            [table["success"][0], table["fail"][0]],
            [table["success"][1], table["fail"][1]],
        ])
        lift = (t - c) / max(c, 1e-9)
        summary["conversion"] = {"control_cr": c, "treatment_cr": t, "p_value": float(p), "lift": float(lift)}

    if "revenue" in metrics:
        ctrl = df.filter(pl.col("variant") == "control")["revenue"].to_list()
        trt = df.filter(pl.col("variant") == "treatment")["revenue"].to_list()
        tstat, p = stats.ttest_ind(trt, ctrl, equal_var=False)
        summary["revenue"] = {"p_value": float(p), "t_stat": float(tstat)}

    return {"experiment_id": experiment_id, "ci": ci, "summary": summary}


