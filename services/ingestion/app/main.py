from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import polars as pl
import os
from datetime import datetime

app = FastAPI(title="Ingestion Service", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion"}


@app.post("/v1/ingest/events")
async def ingest_events(file: UploadFile = File(...)):
    accepted = 0
    rejected = 0
    errors = []
    try:
        content = await file.read()
        df = pl.read_csv(content)
        required = {"user_id", "experiment_id", "variant", "event_type", "value", "timestamp"}
        missing = required - set(df.columns)
        if missing:
            return JSONResponse(status_code=400, content={"error": f"Missing columns: {sorted(missing)}"})
        # basic typing
        df = df.with_columns([
            pl.col("timestamp").str.strptime(pl.Datetime, strict=False).alias("timestamp"),
            pl.col("value").cast(pl.Float64, strict=False).alias("value"),
        ])
        accepted = df.height
        batch_id = datetime.utcnow().isoformat() + "Z"
        # Stub: in real impl, write to DB and object storage
        os.makedirs("/tmp/ingested", exist_ok=True)
        df.write_csv(f"/tmp/ingested/{batch_id}.csv")
        return {"batch_id": batch_id, "accepted": accepted, "rejected": rejected, "errors": errors}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


