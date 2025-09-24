Environment Configuration

Create a `.env` file in the project root (same folder as `docker-compose.yml`). If your environment disallows creating dotfiles directly, create `env/env.example`, copy it to `.env` locally.

Variables:
- DB_HOST=postgres
- DB_PORT=5432
- DB_NAME=abtest
- DB_USER=abtest
- DB_PASS=abtest
- GCS_BUCKET_RAW=abtest-raw
- GCS_BUCKET_CURATED=abtest-curated
- GCS_BUCKET_ARTIFACTS=abtest-artifacts
- RESULTS_CACHE_TTL_SECONDS=300
- LOG_LEVEL=INFO
- RESULTS_API_URL=http://localhost:8004


