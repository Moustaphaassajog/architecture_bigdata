from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import entreprises, statuts

app = FastAPI(title="KBO Hotellerie API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # a restreindre en production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entreprises.router)
app.include_router(statuts.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "KBO Hotellerie API"}


@app.get("/health")
def health():
    return {"status": "healthy"}