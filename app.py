from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict
import uuid

from kb import load_kb, search_kb
from incident_service import create_incident, list_incidents
from ai_service import ai_support_decision

app = FastAPI(title="Customer Support Chatbot with AWS AI")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

KB_DATA = load_kb()

# NOTE:
# In-memory session works for local testing / single instance.
# For production multi-instance deployment, move this to Redis or DynamoDB.
SESSIONS: Dict[str, dict] = {}

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

def get_or_create_session(session_id: Optional[str]):
    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "mode": "normal",
            "incident_data": {}
        }
    return session_id, SESSIONS[session_id]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id, session = get_or_create_session(req.session_id)
    user_message = req.message.strip()

    if session["mode"] == "collecting_incident":
        required_fields = [
            ("customer_name", "Please provide your name."),
            ("email", "Please provide your email address."),
            ("title", "Please provide a short title for the issue."),
            ("description", "Please describe the issue in detail."),
            ("category", "Please provide the category (Login, Performance, Installation, Billing, etc.)."),
            ("severity", "Please provide the severity (Low, Medium, High, Critical).")
        ]

        # Save current user response into next missing field
        for field, _prompt in required_fields:
            if field not in session["incident_data"]:
                session["incident_data"][field] = user_message
                break

        # Ask next missing field
        for field, prompt in required_fields:
            if field not in session["incident_data"]:
                return {
                    "session_id": session_id,
                    "reply": prompt
                }

        # Create incident once all data collected
        incident = create_incident(session["incident_data"])
        session["mode"] = "normal"
        session["incident_data"] = {}

        return {
            "session_id": session_id,
            "reply": (
                f"Your incident has been created successfully.\n"
                f"Incident ID: {incident['incident_id']}\n"
                f"Title: {incident['title']}\n"
                f"Status: {incident['status']}"
            )
        }

    # KB search first
    best_item, score = search_kb(user_message, KB_DATA)
    kb_answer = best_item["answer"] if best_item and score >= 0.15 else ""

    # AI decides whether to resolve or create incident
    ai_result = ai_support_decision(user_message, kb_answer)

    intent = ai_result.get("intent", "resolve")
    reply = ai_result.get("reply", "I can help you with that.")
    category = ai_result.get("category", "General")
    severity = ai_result.get("severity", "Medium")

    if intent == "create_incident":
        session["mode"] = "collecting_incident"
        session["incident_data"] = {
            "category": category,
            "severity": severity
        }

        # Since category/severity already inferred, collect remaining fields
        if "customer_name" not in session["incident_data"]:
            return {
                "session_id": session_id,
                "reply": "I can create an incident for you. Please provide your name."
            }

    # If no strong KB answer and no incident intent
    if not kb_answer and intent != "create_incident":
        return {
            "session_id": session_id,
            "reply": (
                "I could not find a confident solution right now. "
                "If you want, I can create an incident for you. "
                "Please type 'create ticket'."
            )
        }

    return {
        "session_id": session_id,
        "reply": reply + "\n\nIf this does not solve your issue, type 'create ticket'."
    }

@app.get("/incidents")
async def incidents():
    return list_incidents()
