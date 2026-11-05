
"""
AEGIS API

FastAPI application connecting the AEGIS web interface
to the agent engine and persistent conversation memory.

Supports context-aware conversations through SQLite
and Cloudflare Workers AI.
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
from app.memory.database import (
    create_conversation,
    save_conversation_message,
    get_conversation_messages,
    get_all_conversations,
    delete_conversation,
)


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
    allow_methods=["GET", "POST", "DELETE"],
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

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=36,
        description="Existing conversation ID, if continuing a conversation.",
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
# Persistent conversation endpoints
# --------------------------------------------------

@app.get("/api/conversations")
def list_conversations():
    """Return all saved conversations."""

    return {
        "conversations": get_all_conversations(),
    }


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_history(conversation_id: str):
    """Retrieve messages belonging to one conversation."""

    try:

        messages = get_conversation_messages(
            conversation_id
        )

        return {
            "conversation_id": conversation_id,
            "messages": messages,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(conversation_id: str):
    """Delete a conversation and all its messages."""

    try:

        delete_conversation(conversation_id)

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation deleted successfully.",
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


# --------------------------------------------------
# Task execution and conversation persistence
# --------------------------------------------------

@app.post("/api/tasks")
def execute_task(request: TaskRequest):

    conversation_id = request.conversation_id

    try:

        # --------------------------------------------------
        # Step 1: Create or validate the conversation.
        # --------------------------------------------------

        if conversation_id is None:

            conversation_id = create_conversation()

        else:

            # Verify that the conversation exists.
            get_conversation_messages(conversation_id)

        # --------------------------------------------------
        # Step 2: Retrieve previous conversation history.
        # --------------------------------------------------

        # Retrieve history BEFORE saving the current message.
        # This prevents the current message from being sent
        # twice to the language model.

        previous_history = get_conversation_messages(
            conversation_id,
            limit=20,
        )

        # --------------------------------------------------
        # Step 3: Save the incoming user message.
        # --------------------------------------------------

        save_conversation_message(
            conversation_id=conversation_id,
            role="user",
            content=request.task,
        )

        # --------------------------------------------------
        # Step 4: Execute the AEGIS agent with context.
        # --------------------------------------------------

        with agent_lock:

            result = agent.process_request(
                task=request.task,
                conversation_history=previous_history,
            )

        # --------------------------------------------------
        # Step 5: Extract the agent response.
        # --------------------------------------------------

        if not isinstance(result, dict):

            raise RuntimeError(
                "AEGIS returned an invalid execution result."
            )

        assistant_content = result.get("result")

        if assistant_content is None:

            assistant_content = str(result)

        elif not isinstance(assistant_content, str):

            assistant_content = str(assistant_content)

        tool_name = result.get("tool_name")

        if not isinstance(tool_name, str):
            tool_name = None

        # --------------------------------------------------
        # Step 6: Persist the assistant response.
        # --------------------------------------------------

        save_conversation_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            tool_name=tool_name,
        )

        # --------------------------------------------------
        # Step 7: Return the response and conversation ID.
        # --------------------------------------------------

        return {
            "success": True,
            "task": request.task,
            "conversation_id": conversation_id,
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
