from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Started")
    yield
    print("🛑 Stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name}


@app.get("/")
async def root():
    return {"message": "KingoPortfolio API"}