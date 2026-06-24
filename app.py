import os
import tools
from fastapi import FastAPI, UploadFile, File, Form
import json as jsonlib
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from tools import get_fields, add_data, load_json, reset_data
from ai_logic import process_pdf, assist_field, itr_selector_llm
from pydantic import BaseModel
from typing import Optional, List, Any
itr_history_store = {}
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")

# ======================
# Reset Session Route
# ======================
@app.post("/reset")
async def reset_session(itr_type: str = Form(default="itr2")):
    # Validate itr_type — accept itr1, itr2, itr3
    if itr_type not in ("itr1", "itr2", "itr3", "itr4"):
        itr_type = "itr2"
    data = reset_data(itr_type)
    return JSONResponse({
        "status": "reset",
        "itr_type": itr_type,
        "session_file": os.path.basename(tools.current_file),
        "data": data
    })


# ======================
# Upload PDF Route
# ======================
@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    boxes: str = Form(default="{}"),
    scale: float = Form(default=1.4)
):
    file_bytes = await file.read()
    print("RAW BOXES STRING:", boxes)
    boxes_dict = jsonlib.loads(boxes)
    print("BOXES DICT:", boxes_dict)
    print("BOX COUNT PER PAGE:", {k: len(v) for k, v in boxes_dict.items()})
    result = await run_in_threadpool(process_pdf, file_bytes, boxes_dict, scale)
    return JSONResponse(result)


# ======================
# Field Assist Route
# ======================
class FieldAssistRequest(BaseModel):
    field: str
    message: str
    options: Optional[List[Any]] = None


@app.post("/field-assist")
async def field_assist(req: FieldAssistRequest):
    result = await run_in_threadpool(
        assist_field,
        req.field,
        req.message,
        req.options
    )
    return result


# ======================
# List Sessions Route
# ======================
@app.get("/sessions")
async def list_sessions():
    files = sorted(os.listdir("data/sessions/"), reverse=True) if os.path.exists("data/sessions/") else []
    return JSONResponse({"sessions": files})


@app.get("/sessions/{filename}")
async def load_session(filename: str):
    safe_filename = os.path.basename(filename)
    tools.current_file = f"data/sessions/{safe_filename}"
    data = tools.load_json()
    return JSONResponse({"data": data})


@app.post("/api/login")
async def login(data: dict):

    # Replace later with DB/session
    if data.get("email") and data.get("password"):
        return {"status": "ok"}

    return {"status": "fail"}



@app.post("/api/chat")
async def chat(data: dict):

    field_key = data.get("field_key")
    message = data.get("message")

    # ===== ITR SELECTOR MODE =====
    if field_key == "itrSelector":

        user_id = "default_user"  # Replace later with real auth

        if user_id not in itr_history_store:
            itr_history_store[user_id] = []

        history = itr_history_store[user_id]

        result = itr_selector_llm(message, history)

        # Save conversation
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": result["reply"]})

        itr_history_store[user_id] = history

        return result

    # ===== NORMAL FIELD ASSIST =====
    result = assist_field(field_key, message)
    return result