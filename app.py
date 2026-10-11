import json
from pathlib import Path
from statistics import mean

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

data_path = Path(__file__).with_name("q-vercel-latency.json")
records = json.loads(data_path.read_text(encoding="utf-8-sig"))


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float = Field(default=180, allow_inf_nan=False)


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] + weight * (values[upper] - values[lower])


@app.get("/")
def home():
    return {"status": "running", "endpoint": "/api/latency"}


@app.post("/api/latency")
def latency_summary(request: AnalyticsRequest):
    results = []

    for region in dict.fromkeys(request.regions):
        rows = [row for row in records if row["region"] == region]

        if not rows:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown region: {region}",
            )

        latencies = [row["latency_ms"] for row in rows]
        uptimes = [row["uptime_pct"] for row in rows]

        results.append({
            "region": region,
            "avg_latency": round(mean(latencies), 2),
            "p95_latency": round(percentile(latencies, 0.95), 2),
            "avg_uptime": round(mean(uptimes), 3),
            "breaches": sum(
                value > request.threshold_ms for value in latencies
            ),
        })

    return {"regions": results}
