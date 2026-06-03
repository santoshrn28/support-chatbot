from models import SessionLocal, Incident

def create_incident(data: dict):
    db = SessionLocal()
    try:
        incident = Incident(
            customer_name=data["customer_name"],
            email=data["email"],
            title=data["title"],
            description=data["description"],
            category=data.get("category"),
            severity=data.get("severity", "Medium"),
            status="Open",
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident
    finally:
        db.close()

def list_incidents():
    db = SessionLocal()
    try:
        return db.query(Incident).all()
    finally:
        db.close()
``
