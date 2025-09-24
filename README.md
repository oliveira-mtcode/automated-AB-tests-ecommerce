## Automated A/B Experimentation Service (Microservices, Polars, Stats, ML, Docker, GCP)

Make smarter product decisions with a modern, scalable A/B experimentation platform built for e‑commerce. This project ingests behavioral data at scale, validates and analyzes experiments with robust statistical methods, estimates revenue impact via lightweight ML models, and exposes results through clean APIs and a minimalist Ruby web UI. Everything runs in containers and targets Google Cloud Run with Cloud SQL for storage.

### Why this exists
- **Move fast, stay rigorous**: Data validation and solid stats guardrails keep experiments trustworthy.
- **Designed for scale**: Polars-powered data ops, asynchronous jobs, and microservice boundaries.
- **Cloud-first**: Docker everywhere; Cloud Run + Cloud SQL ready.
- **Stakeholder-friendly**: Minimal Ruby UI for uploads, visualizations, and downloadables.

---

## High-Level Architecture

### Microservices
- **Ingestion Service (Python/FastAPI)**
  - Accepts CSV/Parquet/JSON event uploads and streaming batches.
  - Validates structure & semantics; enforces schema contracts.
  - Writes validated records to Cloud SQL and Cloud Storage (raw + curated).

- **Analytics Service (Python/FastAPI + Polars)**
  - Reads curated data; computes metrics and statistical significance.
  - Supported tests: two-sample t-test (continuous), chi-square/fisher (categorical), nonparametric U-test.
  - Generates plots (e.g., lift distributions, p-values, CIs) and summary reports.

- **Modeling Service (Python/FastAPI + scikit-learn/lightweight models)**
  - Trains simple models (e.g., logistic regression for conversion, linear regression for AOV/revenue) to estimate treatment effects.
  - Supports holdout validation and cross-validation; exports feature importances.

- **Results API (Python/FastAPI)**
  - Central read-only gateway aggregating experiment summaries, p-values, effect sizes, and ML-estimated revenue deltas.
  - Caches hot queries; emits webhooks for completed analyses.

- **Ruby Web UI (Sinatra)**
  - Minimal UI to upload experiment definitions/data, visualize results, trigger re-runs, and download PDFs/CSVs.
  - Talks only to the Results API (clean separation of concerns).

### Data Stores
- **Cloud SQL (PostgreSQL)**: Experiments, variants, metrics, results, model metadata.
- **Cloud Storage**: Raw uploads, curated Parquet datasets, generated plots and reports.
- **Optional Redis/Memory Cache**: Short-lived caching for hot results.

### Workflow (Text Diagram)
```
Merchant Upload/Stream
        │
        ▼
Ingestion Service ──► Validate & Filter (Polars) ──► Curated Parquet + Cloud SQL
        │                                                   │
        └──────────────────── Webhook/Event ────────────────┘
                                                            ▼
                             Analytics Service (Polars + Stats)
                             │        └─► Plots/Reports to GCS
                             ▼
                         Results API (Cache + DB)
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
         Modeling Service             Ruby Web UI
               │                           │
               └──► Revenue/Behavior Lift   └──► Uploads, Visuals, Downloads
```

---

## Data Model (Core Tables)
- **experiments**: id, name, hypothesis, primary_metric, start_at, end_at, status
- **variants**: id, experiment_id, name (control/treatment), traffic_split
- **events**: user_id, experiment_id, variant_id, event_type, value, timestamp, attributes JSONB
- **metrics**: experiment_id, variant_id, metric_name, value, window
- **results**: experiment_id, p_value, effect_size, lift_pct, ci_low, ci_high, method, computed_at
- **models**: experiment_id, model_type, features, metrics JSONB, artifact_uri, trained_at

Notes:
- Time windows are always UTC. All IDs are UUIDv4. All tables have created_at/updated_at.

---

## Statistical Methods
- **Binary outcomes (conversion)**: Chi-square test (or Fisher’s exact for low counts)
- **Continuous outcomes (AOV/revenue)**: Two-sample t-test with Welch correction; report Cohen’s d and 95% CI
- **Nonparametric backup**: Mann–Whitney U-test
- **Multiple testing**: Benjamini–Hochberg FDR control (optional)
- **Interim looks**: Alpha spending guidance noted in report (no peeking defaults)

All computations use Polars for grouping/aggregations, with SciPy/StatsModels for tests.

---

## Machine Learning Models
- **Conversion uplift**: Logistic regression with regularization
- **Revenue impact**: Linear regression (or Poisson/Quasi-Poisson for counts)
- **Inputs**: variant, device, channel, geo, price bucket, user recency/frequency, etc.
- **Outputs**: Predicted delta vs control, confidence intervals, feature importance
- **Validation**: Stratified CV for classification, K-fold for regression, with leakage checks

Models are intentionally lightweight to run fast on Cloud Run with small memory footprints.

---

## APIs (Representative Endpoints)

All Python services use FastAPI with OpenAPI/Swagger at `/docs`.

### Ingestion Service
```http
POST /v1/ingest/events
Content-Type: multipart/form-data (file) or application/json (records)
Response: { batch_id, accepted, rejected, errors[] }
```

### Analytics Service
```http
POST /v1/analytics/run
Body: { experiment_id, metrics: ["conversion","revenue"], ci: 0.95 }
Response: { job_id, status }

GET /v1/analytics/results/{experiment_id}
Response: summary stats, p-values, lifts, CIs, links to plots
```

### Modeling Service
```http
POST /v1/model/train
Body: { experiment_id, target: "revenue", features: ["device","geo",...] }
Response: { model_id, metrics, artifact_uri }

GET /v1/model/predictions/{experiment_id}
Response: predicted lift and revenue delta with intervals
```

### Results API
```http
GET /v1/experiments/{experiment_id}
GET /v1/experiments/{experiment_id}/summary
GET /v1/experiments/{experiment_id}/report (CSV/PDF)
```

---

## Ruby Web UI (Sinatra)
- Upload experiment definitions and data files
- Trigger analytics runs and model training
- Visualize variant performance, lifts, and intervals (charts rendered from Results API data)
- Download summary CSV/PDF

Routes (representative):
```http
GET /            # dashboard of experiments
GET /experiments/:id
POST /experiments/:id/upload
POST /experiments/:id/run
GET /experiments/:id/download?format=csv|pdf
```

---

## Local Development (Docker‑first)

Prerequisites: Docker Desktop, Make (optional), Python 3.11+, Ruby 3.2+ (only if running UI outside Docker)

```bash
# 1) Build all images
docker compose build

# 2) Start services + local Postgres
docker compose up -d

# 3) View API docs
# Ingestion: http://localhost:8001/docs
# Analytics: http://localhost:8002/docs
# Modeling:  http://localhost:8003/docs
# Results:   http://localhost:8004/docs
# UI:        http://localhost:4567

# 4) Run unit tests (inside containers)
docker compose exec analytics pytest -q
docker compose exec ingestion pytest -q
docker compose exec modeling pytest -q
docker compose exec results pytest -q

# 5) Run end-to-end tests (Postman/Newman)
docker compose exec tests newman run /tests/postman/collection.json -e /tests/postman/local.postman_environment.json
```

Environment configuration lives in `.env` and service‑specific `.env.*` files. See “Configuration” below.

---

## Google Cloud Deployment (Cloud Run + Cloud SQL)

### Infra Overview
- Each service is deployed as a separate Cloud Run service.
- Cloud SQL (PostgreSQL) used by all Python services via private connector.
- Cloud Storage buckets for raw/curated datasets and artifacts.

### Deploy Steps (example, per service)
```bash
# Authenticate
gcloud auth login
gcloud config set project <PROJECT_ID>

# Build image
gcloud builds submit --tag gcr.io/<PROJECT_ID>/abtest-analytics:latest ./services/analytics

# Deploy to Cloud Run
gcloud run deploy abtest-analytics \
  --image gcr.io/<PROJECT_ID>/abtest-analytics:latest \
  --region <REGION> \
  --allow-unauthenticated \
  --set-env-vars DB_INSTANCE=<INSTANCE_CONNECTION_NAME>,DB_USER=...,DB_PASS=...,DB_NAME=... \
  --add-cloudsql-instances <INSTANCE_CONNECTION_NAME>
```

Repeat for `ingestion`, `modeling`, and `results`. The Ruby UI can also be deployed to Cloud Run and configured to call the Results API.

---

## Data Validation & Quality Gates
- Schema enforcement with Pydantic/FastAPI at the edge.
- Polars-based column type checks, range checks, null thresholds, dedupe rules.
- Rejection logs and error samples stored with batch IDs.
- Optional Great Expectations suite can be added for business-level contracts.

---

## Visualization
- Programmatic charts generated with Matplotlib/Seaborn/Plotly and saved to Cloud Storage.
- UI fetches pre-rendered images and also renders interactive charts from JSON where appropriate.
- Summary PDFs bundle key plots, tables, and narrative insights.

---

## Testing Strategy

### Python (Pytest)
- Unit tests for: schema validators, Polars transforms, stat functions, model trainers.
- Integration tests: DB interactions, storage IO, API contracts.
- E2E: Load sample experiment → run analytics → verify results in DB + artifact outputs.

Run locally:
```bash
pytest -q
```

### API Suites (Postman/Newman)
- Collections for each service with happy paths and edge/error cases.
- Environment files for local and cloud endpoints.

Run inside Docker (example):
```bash
newman run tests/postman/collection.json -e tests/postman/local.postman_environment.json
```

---

## Configuration

Environment variables (representative):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`
- `DB_INSTANCE` (Cloud SQL connection name for Cloud Run)
- `GCS_BUCKET_RAW`, `GCS_BUCKET_CURATED`, `GCS_BUCKET_ARTIFACTS`
- `RESULTS_CACHE_TTL_SECONDS`
- `LOG_LEVEL`

Local `.env` files are read by docker-compose; secrets in cloud should use Secret Manager.

---

## Scalability & Reliability
- **Horizontal scaling**: Each microservice scales independently on Cloud Run.
- **Asynchronous jobs**: Long analytics/modeling runs done async with job IDs and callbacks.
- **Idempotency**: Batch IDs and dedupe constraints prevent duplicate ingestion.
- **Observability**: Structured logging, request IDs, basic metrics (latency, error rates) and traces.
- **Backpressure**: Size limits on uploads; chunked ingestion; retry with exponential backoff.
- **Fail-safes**: Circuit breakers for DB/Storage; graceful degradation to cached results.
- **Data safety**: Raw immutable storage + curated, versioned Parquet datasets.

---

## Security & Compliance
- OAuth2 service-to-service auth; API keys for limited automation.
- Input sanitization and strict content types; signed URLs for uploads/downloads.
- Least-privilege IAM roles for Cloud SQL and GCS.

---

## Repository Layout (suggested)
```
.
├── services/
│   ├── ingestion/
│   ├── analytics/
│   ├── modeling/
│   └── results/
├── ui-ruby/
├── tests/
│   ├── python/
│   └── postman/
├── docker/
├── datasets/
└── docs/
```

---

## Quickstart (Sample Experiment)
```bash
# 1) Bring up stack
docker compose up -d --build

# 2) Upload events to ingestion
curl -X POST http://localhost:8001/v1/ingest/events \
  -H "Content-Type: multipart/form-data" \
  -F file=@datasets/sample_events.csv

# 3) Run analytics for an experiment
curl -X POST http://localhost:8002/v1/analytics/run \
  -H "Content-Type: application/json" \
  -d '{"experiment_id": "<uuid>", "metrics": ["conversion","revenue"], "ci": 0.95}'

# 4) Fetch results
curl http://localhost:8004/v1/experiments/<uuid>/summary
```

---

## Humanized Workflow (What happens when you run an experiment?)
1) You upload or stream your user interaction data.
2) The system validates it—wrong types or missing columns are rejected with explainable errors.
3) Clean data lands in curated storage and the database, versioned for traceability.
4) Analytics kicks off: we compute lifts, p-values, and confidence intervals.
5) Lightweight models estimate behavioral change and revenue impact, with simple, interpretable outputs.
6) Results are available via API and the UI—download a one‑page PDF for execs or a CSV for analysts.
7) If you re-run with new data, the system is smart about duplicates and updates.

---

## License
MIT (or your preferred license)

---

## Credits
Built with Polars, FastAPI, SciPy/StatsModels, scikit-learn, Sinatra, Docker, and GCP.

# automated-AB-tests-ecommerce