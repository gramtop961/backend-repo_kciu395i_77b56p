import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from uuid import uuid4

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

# ---------------- In-memory fallback (only used if DATABASE_URL/NAME not set) ----------------
IN_MEMORY_DECKS: List[Dict[str, Any]] = []

def using_db() -> bool:
    return db is not None


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
            response["database"] = "⚠️  Using in-memory fallback"
            response["connection_status"] = "Degraded (In-Memory)"
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


def normalize_tone(t: str) -> str:
    t = (t or "").strip().lower()
    if not t:
        return "concise"
    mapping = {
        "concise": "concise",
        "direct": "concise",
        "visionary": "visionary",
        "inspiring": "visionary",
        "analytical": "analytical",
        "data-driven": "analytical",
        "casual": "casual",
        "friendly": "casual",
    }
    return mapping.get(t, t)


def bulletize(text: Optional[str], fallback: List[str]) -> List[str]:
    if text:
        # split into short bullet-like fragments
        parts = [p.strip() for p in text.replace(";", ".").split(".")]
        bullets = [p for p in parts if p]
        if len(bullets) >= 2:
            return bullets[:5]
    return fallback


def tone_prefix(tone: str) -> str:
    tone = normalize_tone(tone)
    return {
        "concise": "Clear and to the point.",
        "visionary": "Bold, long-term vision.",
        "analytical": "Evidence-led perspective.",
        "casual": "Approachable and human.",
    }.get(tone, "")


def generate_default_slides(payload: DeckRequest) -> List[Slide]:
    name = payload.name
    industry = payload.industry or ""
    audience = payload.audience or "investors"
    tone = normalize_tone(payload.tone or "concise")

    slides: List[Slide] = []

    # 1. Title
    slides.append(Slide(
        title=f"{name}",
        content=f"{tone_prefix(tone)} A {industry} company. A {tone} overview for {audience}.",
        bullets=["Vision: Build something people love", "Defensibility: Moat from data/UX/ops", "Model: Efficient, scalable, repeatable"],
        kind="title"
    ))

    # 2. Problem
    slides.append(Slide(
        title="Problem",
        content=payload.problem or f"{industry or 'The market'} struggles with high friction, poor UX, and legacy tooling.",
        bullets=bulletize(payload.problem, ["Frequent, painful, and costly", "Existing alternatives are clunky", "Fragmented workflows and data"]),
        kind="problem"
    ))

    # 3. Solution
    slides.append(Slide(
        title="Solution",
        content=payload.solution or f"{name} delivers a modern, streamlined experience that reduces friction and increases outcomes.",
        bullets=["10x better on key metrics", "Fast time-to-value", "Secure, compliant, reliable"],
        kind="solution"
    ))

    # 4. Market
    slides.append(Slide(
        title="Market",
        content=payload.market or "Large, expanding, and underserved segments with clear ICP.",
        bullets=bulletize(payload.market, ["Expanding TAM", "Well-defined ICP", "Strong entry wedge"]),
        kind="market"
    ))

    # 5. Product
    slides.append(Slide(
        title="Product",
        content="Core capabilities and differentiators.",
        bullets=["Feature set aligned to ICP", "Delightful UX with automation", "APIs and integrations"],
        kind="product"
    ))

    # 6. Business Model
    slides.append(Slide(
        title="Business Model",
        content="How we make money.",
        bullets=["SaaS subscription and usage tiers", "Healthy unit economics", "Expansion via add-ons"],
        kind="business"
    ))

    # 7. Go-To-Market
    slides.append(Slide(
        title="Go-To-Market",
        content="Efficient, repeatable motion.",
        bullets=["Bottom-up product-led growth", "Partnerships and integrations", "Targeted outbound for ICP"],
        kind="gtm"
    ))

    # 8. Competition
    slides.append(Slide(
        title="Competition",
        content="Clear differentiation against legacy and point solutions.",
        bullets=["Faster implementation", "Superior UX", "All-in-one platform"],
        kind="competition"
    ))

    # 9. Traction
    slides.append(Slide(
        title="Traction",
        content=payload.traction or "Early signs of pull and validation.",
        bullets=bulletize(payload.traction, ["Growing pipeline", "Design partners active", "Strong retention on pilots"]),
        kind="traction"
    ))

    # 10. Team
    slides.append(Slide(
        title="Team",
        content="Why this team wins.",
        bullets=["Founder-market fit", "Deep domain expertise", "Shipped at scale"],
        kind="team"
    ))

    # 11. Financials (optional, lightweight)
    slides.append(Slide(
        title="Financials",
        content="High-level plan and efficiency.",
        bullets=["12-18 months runway", "Disciplined burn", "Milestone-based hiring"],
        kind="financials"
    ))

    # 12. Ask
    slides.append(Slide(
        title="Ask",
        content="Funding and use of proceeds.",
        bullets=["Round size and instrument", "Use of funds by function", "Key milestones"],
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
        if using_db():
            deck_id = create_document("pitchdeck", deck)
            doc = db["pitchdeck"].find_one({"_id": ObjectId(deck_id)})
            return {"deck": serialize_doc(doc)}
        else:
            # In-memory fallback
            now = datetime.now(timezone.utc)
            deck_doc = deck.model_dump()
            deck_doc.update({
                "_id": str(uuid4()),
                "created_at": now,
                "updated_at": now,
            })
            IN_MEMORY_DECKS.append(deck_doc)
            return {"deck": serialize_doc(deck_doc)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decks")
def list_decks(limit: int = 20):
    try:
        if using_db():
            docs = get_documents("pitchdeck", {}, limit=limit)
            return {"decks": [serialize_doc(d) for d in docs]}
        else:
            return {"decks": [serialize_doc(d) for d in IN_MEMORY_DECKS[:limit]]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decks/{deck_id}")
def get_deck(deck_id: str):
    try:
        if using_db():
            doc = db["pitchdeck"].find_one({"_id": ObjectId(deck_id)})
            if not doc:
                raise HTTPException(status_code=404, detail="Deck not found")
            return {"deck": serialize_doc(doc)}
        else:
            for d in IN_MEMORY_DECKS:
                if str(d.get("_id")) == deck_id:
                    return {"deck": serialize_doc(d)}
            raise HTTPException(status_code=404, detail="Deck not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def seed_if_empty():
    try:
        if using_db():
            has_any = db["pitchdeck"].count_documents({}) > 0
            if not has_any:
                # Seed one example deck
                create_deck(DeckRequest(name="Acme AI", industry="Fintech", audience="seed investors", tone="concise", problem="Payment ops are manual and error-prone.", solution="Automate reconciliation and risk.", market="SMBs transacting $500B+/yr online.", traction="Design partners processing $2M/mo."))
        else:
            if not IN_MEMORY_DECKS:
                create_deck(DeckRequest(name="Acme AI", industry="Fintech", audience="seed investors", tone="visionary", problem="SMBs are stuck with legacy payment ops.", solution="AI-driven automation for reconciliation and fraud.", market="Massive TAM with clear ICP wedge.", traction="Design partners and growing pipeline."))
    except Exception:
        # Best effort; don't crash startup
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
