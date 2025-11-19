import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

from database import db, create_document, get_documents
from schemas import PitchDeck, Slide

# Helper to convert MongoDB documents to JSON-serializable dicts
from bson import ObjectId

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out

app = FastAPI(title="Pitchdeck Maker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Pitchdeck Maker API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# ---------------- Pitchdeck Maker Endpoints ----------------
class DeckRequest(BaseModel):
    name: str = Field(..., description="Company or product name")
    industry: Optional[str] = Field(None, description="Industry or category")
    audience: Optional[str] = Field(None, description="Audience, e.g., seed investors")
    tone: Optional[str] = Field("concise", description="Tone of writing")
    problem: Optional[str] = Field(None, description="Problem statement")
    solution: Optional[str] = Field(None, description="Solution summary")
    market: Optional[str] = Field(None, description="Target market size/segment")
    traction: Optional[str] = Field(None, description="Key traction metrics or proof points")


def generate_default_slides(payload: DeckRequest) -> List[Slide]:
    name = payload.name
    industry = payload.industry or ""
    audience = payload.audience or "investors"
    tone = payload.tone or "concise"

    slides: List[Slide] = []

    slides.append(Slide(
        title=f"{name}",
        content=f"A {industry} company. A {tone} overview for {audience}.",
        bullets=["Vision: Build something people love", "Model: Efficient, scalable, defensible"],
        kind="title"
    ))

    if payload.problem:
        slides.append(Slide(
            title="Problem",
            content=payload.problem,
            bullets=["Pain is frequent", "Costly and widespread", "Current solutions are clunky"],
            kind="problem"
        ))

    slides.append(Slide(
        title="Solution",
        content=payload.solution or f"{name} delivers a modern, streamlined experience.",
        bullets=["Simple to adopt", "Delightful UX", "10x better on key metrics"],
        kind="solution"
    ))

    if payload.market:
        slides.append(Slide(
            title="Market",
            content=payload.market,
            bullets=["Large and expanding", "Well-defined ICP", "Clear wedge to enter"],
            kind="market"
        ))

    slides.append(Slide(
        title="Product",
        content="Key capabilities and differentiators.",
        bullets=["Core features", "Differentiation", "Roadmap highlights"],
        kind="product"
    ))

    slides.append(Slide(
        title="Business Model",
        content="How we make money.",
        bullets=["Pricing strategy", "Unit economics", "Go-to-market"],
        kind="business"
    ))

    if payload.traction:
        slides.append(Slide(
            title="Traction",
            content=payload.traction,
            bullets=["Growth", "Retention", "Pipeline"],
            kind="traction"
        ))

    slides.append(Slide(
        title="Team",
        content="Who we are and why us.",
        bullets=["Founders", "Relevant experience", "Advisors"],
        kind="team"
    ))

    slides.append(Slide(
        title="Ask",
        content="Funding and use of proceeds.",
        bullets=["Round size", "Use of funds", "Milestones"],
        kind="ask"
    ))

    return slides

@app.post("/api/decks")
def create_deck(req: DeckRequest):
    deck = PitchDeck(
        name=req.name,
        industry=req.industry,
        audience=req.audience,
        tone=req.tone,
        slides=generate_default_slides(req)
    )
    try:
        deck_id = create_document("pitchdeck", deck)
        doc = db["pitchdeck"].find_one({"_id": ObjectId(deck_id)})
        return {"deck": serialize_doc(doc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/decks")
def list_decks(limit: int = 20):
    try:
        docs = get_documents("pitchdeck", {}, limit=limit)
        return {"decks": [serialize_doc(d) for d in docs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/decks/{deck_id}")
def get_deck(deck_id: str):
    try:
        doc = db["pitchdeck"].find_one({"_id": ObjectId(deck_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Deck not found")
        return {"deck": serialize_doc(doc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
