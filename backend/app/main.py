from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine

from app.api.job_sources import router as job_sources_router
from app.api.jobs import router as jobs_router
from app.api.user_profiles import router as user_profiles_router
from app.api.job_analyses import router as job_analyses_router


app = FastAPI(
    title=settings.app_name,
    description="AI-powered Job Intelligence Platform",
    version="0.1.0",
)

# CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_sources_router)
app.include_router(jobs_router)
app.include_router(user_profiles_router)
app.include_router(job_analyses_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to WhatToWork API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
    }


@app.get("/health/db")
async def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
