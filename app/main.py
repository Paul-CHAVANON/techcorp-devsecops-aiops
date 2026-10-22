"""TECHCORP Orders API (laboratoire) — version durcie du starter.

Conserve les métriques du starter (techcorp_http_requests_total{path,status},
techcorp_request_duration_seconds{path}) pour rester compatible avec la règle
ElevatedHTTP500 fournie. SIMULATE_FAILURE=true simule le timeout base de données.
"""
import logging
import os
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

RELEASE = os.getenv("APP_VERSION", "2.4.7")
INCIDENT_ID = "INC-2026-1042"

REQUESTS = Counter("techcorp_http_requests_total", "Requests", ["path", "status"])
LATENCY = Histogram(
    "techcorp_request_duration_seconds", "Latency", ["path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
APP_INFO = Gauge("techcorp_app_info", "Release déployée", ["release"])
logger = logging.getLogger("uvicorn.error")

# Pré-initialisation des séries : sans cela, la série status="500" n'existe qu'à
# la première erreur et increase() sous-estime le début de l'incident.
for _path, _status in [("/orders", "200"), ("/orders", "500"), ("/health", "200")]:
    REQUESTS.labels(_path, _status)
APP_INFO.labels(RELEASE).set(1)


def simulate_failure() -> bool:
    return os.getenv("SIMULATE_FAILURE", "false").strip().lower() == "true"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Trace du changement, exploitée par la corrélation AIOps (mission C1)
    logger.info("deployment release=%s simulate_failure=%s event=deploy_success", RELEASE, simulate_failure())
    yield


app = FastAPI(title="TECHCORP Orders API", version=RELEASE, lifespan=lifespan)


@app.get("/health")
def health():
    # Liveness uniquement : ne teste pas la base (point discuté dans le rapport)
    REQUESTS.labels("/health", "200").inc()
    return {"status": "ok", "release": RELEASE}


@app.get("/orders")
def orders():
    start = time.monotonic()
    try:
        if simulate_failure():
            time.sleep(random.uniform(0.2, 0.5))  # attente jusqu'au timeout simulé
            REQUESTS.labels("/orders", "500").inc()
            logger.error("order_processing_failed db_connection_timeout route=/orders release=%s event=%s",
                         RELEASE, INCIDENT_ID)
            raise HTTPException(status_code=500, detail="Order processing unavailable")
        time.sleep(random.uniform(0.005, 0.03))
        REQUESTS.labels("/orders", "200").inc()
        return {"orders": [], "status": "ready"}
    finally:
        LATENCY.labels("/orders").observe(time.monotonic() - start)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
