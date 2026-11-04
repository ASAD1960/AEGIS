
"""
AEGIS API

FastAPI application connecting the AEGIS web interface
to the existing agent engine.
"""

import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.agent.agent import Agent
from app.core.config import APP_NAME, APP_VERSION


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

app = FastAPI(
    title=f"{APP_NAME} API",
    description="Backend API for the AEGIS intelligent agent.",
    version=APP_VERSION,
)


# --------------------------------------------------
# Frontend communication
# --------------------------------------------------

# Configure allowed frontend origins through an environment
# variable. Multiple origins can be separated by commas.
#
# Local development default:
# http://localhost:3000
#
# Production example:
# http://localhost:3000,https://your-aegis.vercel.app

FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "AEGIS_FRONTEND_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Agent initialization
# --------------------------------------------------

agent = Agent()
agent_lock = Lock()


# --------------------------------------------------
# File storage configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIRECTORY = PROJECT_ROOT / "data" / "uploads"

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


# --------------------------------------------------
# Request models
# --------------------------------------------------

class TaskRequest(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    task: str = Field(
        min_length=1,
        max_length=10000,
        description="Natural-language task for AEGIS.",
    )


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/api/health")
def health_check():

    return {
        "status": "ok",
        "application": APP_NAME,
        "version": APP_VERSION,
    }


# --------------------------------------------------
# Agent status endpoint
# --------------------------------------------------

@app.get("/api/status")
def get_agent_status():

    return {
        "agent": APP_NAME,
        "status": agent.get_status(),
        "version": APP_VERSION,
    }


# --------------------------------------------------
# Registered tools endpoint
# --------------------------------------------------

@app.get("/api/tools")
def get_registered_tools():

    return {
        "tools": agent.list_tools(),
    }


# --------------------------------------------------
# Task execution endpoint
# --------------------------------------------------

@app.post("/api/tasks")
def execute_task(request: TaskRequest):

    try:

        with agent_lock:

            result = agent.process_request(
                task=request.task
            )

        return {
            "success": True,
            "task": request.task,
            "execution": result,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


# --------------------------------------------------
# CSV upload and analysis endpoint
# --------------------------------------------------

@app.post("/api/data/upload")
async def upload_csv(file: UploadFile = File(...)):

    original_filename = file.filename or ""

    # Only accept CSV filenames.
    if Path(original_filename).suffix.lower() != ".csv":

        await file.close()

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted.",
        )

    try:

        # Read at most 5 MB plus one byte.
        contents = await file.read(MAX_UPLOAD_SIZE + 1)

        if not contents:

            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(contents) > MAX_UPLOAD_SIZE:

            raise HTTPException(
                status_code=413,
                detail="File exceeds the 5 MB upload limit.",
            )

        # Validate the file's text encoding.
        try:
            contents.decode("utf-8-sig")

        except UnicodeDecodeError as error:

            raise HTTPException(
                status_code=400,
                detail="CSV file must use UTF-8 encoding.",
            ) from error

        # Generate a safe, unique server-side filename.
        generated_filename = f"{uuid4().hex}.csv"

        UPLOAD_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        saved_path = UPLOAD_DIRECTORY / generated_filename

        saved_path.write_bytes(contents)

        try:

            # Use the existing AEGIS data-analysis tool
            # through the existing agent.
            with agent_lock:

                result = agent.process_request(
                    task="Analyze CSV data",
                    file_path=str(saved_path),
                )

        except ValueError as error:

            saved_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except Exception:

            saved_path.unlink(missing_ok=True)
            raise

        return {
            "success": True,
            "original_filename": original_filename,
            "stored_filename": generated_filename,
            "execution": result,
        }

    finally:

        await file.close()
