import datetime
import json

from fastapi import FastAPI

from .log_config import logger
from .models import Events
from prometheus_client import Counter, Gauge, Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI(title="health-check", version="0.0.1")

events_counter = Counter(
    "infrastructure_events_accepted_total",
    "Total number of accepted infrastructure events",
    ["severity"],
)

events_counter = Counter(
    "infrastructure_events_accepted_total",
    "Total number of accepted infrastructure events",
    ["message"],
)

@app.get("/healthz")
def read_health():
    return {"status": "ok"}


@app.get("/version")
def read_version():
    return {"version": "0.0.1"}


@app.get("/readyz")
def read_readyz():
    return {"status": "ready"}


@app.post("/events")
def events(event: Events):
    data = event.model_dump()
    data["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
    data["event_type"] = "infrastructure_event"

    logger.info(json.dumps(data))
    events_counter.labels(severity="critical").inc()
    events_counter.labels(message="SSH brute force detected").inc()
    return {"status": "accepted"}

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )