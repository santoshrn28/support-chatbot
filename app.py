from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict
import uuid

from models import init_db
from kb import load_kb, search_kb
from incident_service import create_incident, list_incidents

app = FastAPI(title="Customer Support Chatbot")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()
KB_DATA = load_kb()

# In-memory session state for demo purposes
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

def detect_ticket_intent(message: str) -> bool:
    triggers = [
        "create incident", "create ticket", "raise ticket",
        "open incident", "open ticket", "log issue",
        "cannot resolve", "still not working", "need support"
    ]
    msg = message.lower()
    return any(t in msg for t in triggers)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(req: ChatRequest):
    session_id, session = get_or_create_session(req.session_id)
    user_message = req.message.strip()

    # If currently collecting incident details
    if session["mode"] == "collecting_incident":
        required_fields = [
            ("customer_name", "Please provide your name."),
            ("email", "Please provide your email address."),
            ("title", "Please provide a short title for the issue."),
            ("description", "Please describe the issue in detail."),
            ("category", "Please provide the category (e.g. Login, Performance, Installation, Access)."),
            ("severity", "Please provide the severity (Low, Medium, High, Critical).")
        ]

        # Find next missing field and fill it with current user message
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

        # All fields collected, create incident
        incident = create_incident(session["incident_data"])
        session["mode"] = "normal"
        session["incident_data"] = {}

        return {
            "session_id": session_id,
            "reply": (
                f"Your incident has been created successfully.\n"
                f"Incident ID: INC-{incident.id:05d}\n"
                f"Title: {incident.title}\n"
                f"Status: {incident.status}"
            )
        }

    # Explicit incident creation intent
    if detect_ticket_intent(user_message):
        session["mode"] = "collecting_incident"
        session["incident_data"] = {}
        return {
            "session_id": session_id,
            "reply": "Sure, I can create an incident for you. Please provide your name."
        }

    # Knowledge base search
    best_item, score = search_kb(user_message, KB_DATA)

    if best_item and score >= 0.15:
        return {
            "session_id": session_id,
            "reply": f"{best_item['answer']}\n\nIf this does not solve your issue, reply with: 'create ticket'"
        }

    # Fallback
    return {
        "session_id": session_id,
        "reply": (
            "I could not find a confident solution in the knowledge base. "
            "If you want, I can create an incident for you. "
            "Please reply with 'create ticket'."
        )
    }

@app.get("/incidents")
async def incidents():
    data = list_incidents()
    return [
        {
            "id": i.id,
            "customer_name": i.customer_name,
            "email": i.email,
            "title": i.title,
            "description": i.description,
            "category": i.category,
            "severity": i.severity,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in data
    ]
