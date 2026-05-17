from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import gravity, optimization, cluster

app = FastAPI(
    title="Data Center Intelligence Platform API",
    description="AI-powered data center site selection, optimization, and cluster prediction.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gravity.router)
app.include_router(optimization.router)
app.include_router(cluster.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "gravity_model": "/gravity/scores",
            "nsga_optimization": "/optimization/run",
            "cluster_prediction": "/cluster/predict",
            "api_docs": "/docs",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
