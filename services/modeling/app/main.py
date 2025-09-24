from fastapi import FastAPI
from fastapi.responses import JSONResponse
import polars as pl
from sklearn.linear_model import LogisticRegression, LinearRegression
from typing import Dict, Any

app = FastAPI(title="Modeling Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "modeling"}


@app.post("/v1/model/train")
def train_model(payload: Dict[str, Any]):
    target = payload.get("target", "conversion")
    # Demo dataset
    df = pl.DataFrame({
        "variant": [0] * 100 + [1] * 100,
        "device_mobile": [0, 1] * 100,
        "geo_us": [1, 0] * 100,
        "conversion": [0] * 60 + [1] * 40 + [0] * 50 + [1] * 50,
        "revenue": [0.0] * 60 + [50.0] * 40 + [0.0] * 50 + [55.0] * 50,
    })
    X = df.select(["variant", "device_mobile", "geo_us"]).to_pandas()
    if target == "conversion":
        y = df["conversion"].to_pandas()
        model = LogisticRegression(max_iter=1000)
        model.fit(X, y)
        score = float(model.score(X, y))
        return {"target": target, "metrics": {"accuracy": score}}
    else:
        y = df["revenue"].to_pandas()
        model = LinearRegression()
        model.fit(X, y)
        r2 = float(model.score(X, y))
        return {"target": target, "metrics": {"r2": r2}}


