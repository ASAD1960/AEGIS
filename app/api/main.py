
"""
AEGIS API

FastAPI application connecting the AEGIS web interface
to the agent engine and persistent conversation memory.

Supports:
- Supabase authentication
- User-owned conversations
- Context-aware agent execution
- SQLite and PostgreSQL persistence
- Persistent personal memory extraction and retrieval
- Personal memory management API
- CSV data analysis
"""

import json
import os
import urllib.error
import urllib.request

from pathlib import Path
from threading import Lock
from uuid import uuid4

from typing import Literal

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, ConfigDict, Field

from app.agent.agent import Agent
from app.core.config import APP_NAME, APP_VERSION
from app.memory.database_backend import (
    create_conversation,
    save_conversation_message,
    get_conversation_messages,
    get_all_conversations,
    delete_conversation,
    save_user_memory,
    get_user_memories,
    get_user_memory_history,
    delete_user_memory,
)
from app.memory.extraction import extract_personal_memory_candidates


# --------------------------------------------------
# Supabase authentication configuration
# --------------------------------------------------

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    os.getenv("NEXT_PUBLIC_SUPABASE_URL", ""),
).strip().rstrip("/")

SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY",
    os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", ""),
).strip()

AUTH_TIMEOUT_SECONDS = 10

security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Verify the Supabase access token through Supabase Auth.

    The user ID is taken only from the verified Supabase response.
    """

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured on the backend.",
        )

    request = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": f"Bearer {credentials.credentials}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=AUTH_TIMEOUT_SECONDS,
        ) as response:
            user_data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:

        if error.code in (401, 403):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

        raise HTTPException(
            status_code=503,
            detail="Unable to verify authentication with Supabase.",
        ) from error

    except (urllib.error.URLError, TimeoutError, OSError) as error:

        raise HTTPException(
            status_code=503,
            detail="Supabase authentication service is unavailable.",
        ) from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:

        raise HTTPException(
            status_code=502,
            detail="Invalid response from the authentication service.",
        ) from error

    user_id = user_data.get("id") if isinstance(user_data, dict) else None

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=401,
            detail="Unable to identify the authenticated user.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


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


class MemoryCreateRequest(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    memory_key: str = Field(
        min_length=1,
        max_length=160,
    )

    content: str = Field(
        min_length=1,
        max_length=2000,
    )

    category: str = Field(
        min_length=1,
        max_length=80,
    )

    source_type: Literal[
        "explicit_statement",
        "correction",
    ]

    source_text: str = Field(
        min_length=1,
        max_length=5000,
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
def list_conversations(
    user_id: str = Depends(get_current_user_id),
):
    """Return conversations belonging to the authenticated user."""

    return {
        "conversations": get_all_conversations(user_id),
    }


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_history(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve messages belonging to the authenticated user."""

    try:

        messages = get_conversation_messages(
            conversation_id,
            user_id,
        )

        return {
            "conversation_id": conversation_id,
            "messages": messages,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a conversation owned by the authenticated user."""

    try:

        delete_conversation(
            conversation_id,
            user_id,
        )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation deleted successfully.",
        }

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error


# --------------------------------------------------
# Personal memory extraction and persistence
# --------------------------------------------------

def persist_explicit_personal_memories(
    user_id: str,
    message: str,
) -> None:
    """
    Extract and persist supported personal facts.

    Only explicit statements and corrections are saved.

    Ambiguous candidates requiring confirmation are ignored.

    Existing identical active memories are not duplicated.
    """

    candidates = extract_personal_memory_candidates(message)

    for candidate in candidates:

        # Never automatically save ambiguous candidates.
        if candidate.get("action") != "save":
            continue

        source_type = candidate.get("source_type")

        if source_type not in (
            "explicit_statement",
            "correction",
        ):
            continue

        memory_key = candidate["memory_key"]
        memory_content = candidate["content"]

        # Check existing versions for this user and memory key.
        history = get_user_memory_history(
            user_id,
            memory_key=memory_key,
        )

        already_saved = any(
            memory.get("status") == "active"
            and memory.get("content") == memory_content
            for memory in history
        )

        if already_saved:
            continue

        # Save using the authenticated user ID.
        # The database layer handles correction history.
        save_user_memory(
            user_id=user_id,
            memory_key=memory_key,
            content=memory_content,
            category=candidate["category"],
            source_type=source_type,
            source_text=candidate["source_text"],
        )


# --------------------------------------------------
# Persistent personal memory endpoints
# --------------------------------------------------

@app.get("/api/memories")
def list_personal_memories(
    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=80,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    user_id: str = Depends(get_current_user_id),
):
    """
    Return active personal memories belonging to
    the authenticated user.
    """

    try:

        memories = get_user_memories(
            user_id=user_id,
            category=category,
            limit=limit,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        "memories": memories,
        "count": len(memories),
    }


@app.get("/api/memories/{memory_key}/history")
def get_personal_memory_history(
    memory_key: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    user_id: str = Depends(get_current_user_id),
):
    """
    Return the version history for one memory key.

    Only records belonging to the authenticated user
    are returned.
    """

    try:

        history = get_user_memory_history(
            user_id=user_id,
            memory_key=memory_key,
            limit=limit,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    return {
        "memory_key": memory_key,
        "history": history,
        "count": len(history),
    }


@app.post("/api/memories")
def create_personal_memory(
    request: MemoryCreateRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
):
    """
    Manually create or correct a personal memory.
    """

    try:

        existing_history = get_user_memory_history(
            user_id=user_id,
            memory_key=request.memory_key,
        )

        # Avoid creating an identical active record.
        for memory in existing_history:

            if (
                memory.get("status") == "active"
                and memory.get("content") == request.content
            ):

                response.status_code = 200

                return {
                    "message": "This memory already exists.",
                    "created": False,
                    "memory": memory,
                }

        memory_id = save_user_memory(
            user_id=user_id,
            memory_key=request.memory_key,
            content=request.content,
            category=request.category,
            source_type=request.source_type,
            source_text=request.source_text,
        )

        response.status_code = 201

        return {
            "message": "Personal memory saved successfully.",
            "created": True,
            "memory": {
                "id": memory_id,
                "memory_key": request.memory_key,
                "content": request.content,
                "category": request.category,
                "source_type": request.source_type,
                "source_text": request.source_text,
                "status": "active",
            },
        }

    except ValueError as error:

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.delete("/api/memories/{memory_id}")
def remove_personal_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Permanently delete a memory belonging to the
    authenticated user.
    """

    try:

        delete_user_memory(
            user_id=user_id,
            memory_id=memory_id,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail="Memory was not found.",
        ) from error

    return {
        "message": "Personal memory deleted successfully.",
        "deleted": True,
        "memory_id": memory_id,
    }


# --------------------------------------------------
# Task execution and conversation persistence
# --------------------------------------------------

@app.post("/api/tasks")
def execute_task(
    request: TaskRequest,
    user_id: str = Depends(get_current_user_id),
):

    conversation_id = request.conversation_id

    # --------------------------------------------------
    # Step 1: Create or validate the conversation.
    # --------------------------------------------------

    if conversation_id is None:

        conversation_id = create_conversation(user_id)

        previous_history = []

    else:

        try:

            # Fetching history also verifies ownership.
            previous_history = get_conversation_messages(
                conversation_id,
                user_id,
                limit=20,
            )

        except ValueError as error:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            ) from error

    # --------------------------------------------------
    # Step 2: Save the incoming user message.
    # --------------------------------------------------

    try:

        save_conversation_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=request.task,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error

    # --------------------------------------------------
    # Step 3: Extract and persist explicit personal memories.
    # --------------------------------------------------

    persist_explicit_personal_memories(
        user_id=user_id,
        message=request.task,
    )

    # --------------------------------------------------
    # Step 4: Retrieve updated personal memories.
    # --------------------------------------------------

    personal_memories = get_user_memories(
        user_id,
        limit=30,
    )

    # --------------------------------------------------
    # Step 5: Execute the AEGIS agent with separate context.
    # --------------------------------------------------

    try:

        with agent_lock:

            result = agent.process_request(
                task=request.task,
                conversation_history=previous_history,
                personal_memories=personal_memories,
            )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    # --------------------------------------------------
    # Step 6: Extract the agent response.
    # --------------------------------------------------

    if not isinstance(result, dict):

        raise HTTPException(
            status_code=500,
            detail="AEGIS returned an invalid execution result.",
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
    # Step 7: Persist the assistant response.
    # --------------------------------------------------

    try:

        save_conversation_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_content,
            tool_name=tool_name,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error

    # --------------------------------------------------
    # Step 8: Return the response and conversation ID.
    # --------------------------------------------------

    return {
        "success": True,
        "task": request.task,
        "conversation_id": conversation_id,
        "execution": result,
    }


# --------------------------------------------------
# CSV upload and analysis endpoint
# --------------------------------------------------

@app.post("/api/data/upload")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Accept CSV analysis requests from authenticated users."""

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
