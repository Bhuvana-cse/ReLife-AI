import base64
import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Annotated

import httpx
import opening_hours as opening_hours_parser
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.database import connect, initialize


SECRET = os.getenv("RELIFE_SECRET_KEY", "local-development-key-change-me")
if len(SECRET) < 24 and SECRET != "local-development-key-change-me":
    raise RuntimeError("RELIFE_SECRET_KEY must contain at least 24 characters")

app = FastAPI(title="ReLife AI API", version="1.0.0")
origins = os.getenv(
    "RELIFE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bearer = HTTPBearer(auto_error=False)
OPENSTREETMAP_USER_AGENT = "ReLifeAI/1.0 (local circular recovery directory)"
LIVE_CENTER_CACHE: dict[str, tuple[float, dict]] = {}
GEOCODE_CACHE: dict[str, tuple[float, tuple[float, float] | None]] = {}
NOMINATIM_LOCK = asyncio.Lock()
LAST_NOMINATIM_REQUEST = 0.0
LIVE_CACHE_TTL_SECONDS = 600


@app.on_event("startup")
def startup() -> None:
    initialize()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, saved: str) -> bool:
    try:
        salt_hex, digest_hex = saved.split(":", 1)
        candidate = hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def issue_token(user_id: int) -> str:
    payload = json.dumps({"sub": user_id, "exp": int(time.time()) + 60 * 60 * 24}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    try:
        encoded, signature = credentials.credentials.split(".", 1)
        expected = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < time.time():
            raise ValueError
        with connect() as db:
            user = db.execute("SELECT id, name, email, student_id, created_at FROM users WHERE id = ?", (payload["sub"],)).fetchone()
        if not user:
            raise ValueError
        return dict(user)
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Session is invalid or expired")


User = Annotated[dict, Depends(current_user)]


def product_for_user(db, product_id: int, user_id: int):
    row = db.execute("SELECT * FROM products WHERE id = ? AND user_id = ?", (product_id, user_id)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    student_id: str | None = Field(default=None, max_length=32)


class LoginInput(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str


class UpdateInput(BaseModel):
    update_type: str = Field(min_length=2, max_length=40)
    detail: str = Field(min_length=2, max_length=500)


class TransferInput(BaseModel):
    new_owner_email: str = Field(min_length=3, max_length=254)
    note: str = Field(default="Ownership transfer recorded by current user", max_length=300)


class ComponentInput(BaseModel):
    category: str
    condition_states: dict[str, str] = Field(default_factory=dict)
    confirmations: dict[str, bool] = Field(default_factory=dict)


class SimulationInput(BaseModel):
    product_id: int
    repair_cost: float = Field(ge=0, le=100000)
    resale_value: float = Field(ge=0, le=100000)
    useful_life_years: float = Field(ge=0, le=50)
    period_years: int = Field(default=3, ge=1, le=30)
    reuse_value: float = Field(default=0, ge=0, le=100000)
    salvage_value: float = Field(default=0, ge=0, le=100000)
    replacement_cost_per_year: float = Field(default=0, ge=0, le=100000)


class PlanStateInput(BaseModel):
    status: str


class MatchStateInput(BaseModel):
    status: str


@app.get("/api/health")
def health():
    return {"status": "ok", "inference": "rule-based demo; no computer-vision model is configured"}


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterInput):
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    student_id = body.student_id.strip().upper() if body.student_id and body.student_id.strip() else None
    if student_id and not re.fullmatch(r"[A-Z0-9-]{3,32}", student_id):
        raise HTTPException(status_code=422, detail="Student ID may contain letters, numbers, and hyphens")
    with connect() as db:
        try:
            cursor = db.execute(
                "INSERT INTO users(name, email, student_id, password_hash) VALUES (?, ?, ?, ?)",
                (body.name.strip(), email, student_id, hash_password(body.password)),
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc):
                raise HTTPException(status_code=409, detail="An account with this email or student ID already exists")
            raise
        user_id = cursor.lastrowid
    return {"token": issue_token(user_id), "user": {"id": user_id, "name": body.name.strip(), "email": email, "student_id": student_id}}


@app.post("/api/auth/login")
def login(body: LoginInput):
    identifier = body.identifier.strip()
    with connect() as db:
        user = db.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR upper(student_id) = ?",
            (identifier.lower(), identifier.upper()),
        ).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"token": issue_token(user["id"]), "user": {"id": user["id"], "name": user["name"], "email": user["email"], "student_id": user["student_id"]}}


@app.get("/api/auth/me")
def me(user: User):
    return user


@app.post("/api/analyses", status_code=201)
async def analyze(
    user: User,
    category: Annotated[str, Form(min_length=2, max_length=40)],
    age_years: Annotated[float, Form(ge=0, le=100)],
    condition: Annotated[str, Form()],
    location: Annotated[str, Form(max_length=100)] = "",
    visible_damage: Annotated[str, Form(max_length=1000)] = "",
    repair_cost: Annotated[float, Form(ge=0, le=100000)] = 0,
    resale_value: Annotated[float, Form(ge=0, le=100000)] = 0,
    useful_life_years: Annotated[float, Form(ge=0, le=50)] = 2,
    product_name: Annotated[str, Form(max_length=80)] = "",
    product_id: Annotated[int | None, Form()] = None,
    image: UploadFile | None = File(default=None),
):
    category = category.strip().lower()
    condition = condition.strip().lower()
    if condition not in {"excellent", "good", "fair", "poor", "broken"}:
        raise HTTPException(status_code=422, detail="Choose a supported condition")
    image_name = None
    if image:
        if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WebP image")
        content = await image.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
        image_name = "uploaded image"
    product_name = product_name.strip() or category.replace("_", " ").title()
    if condition == "broken":
        recommendation = "component salvage"
        explanation = "The item is reported broken. Do not reuse it as a whole; inspect parts individually and use a suitable recycling route if parts are unsafe."
    elif condition in {"poor", "fair"} and repair_cost <= max(resale_value * 0.8, 50):
        recommendation = "repair"
        explanation = "The item is reported poor/fair and the stated repair cost is within the demo rule's 80% of resale value (or $50 floor). Confirm the estimate with a provider."
    elif condition in {"excellent", "good"} and resale_value > repair_cost:
        recommendation = "resale"
        explanation = "The reported condition is good/excellent and stated resale value exceeds repair cost. The sale price and buyer demand are not guaranteed."
    elif condition == "fair":
        recommendation = "donation"
        explanation = "The reported fair condition and current inputs make donation or reuse the initial choice; a recipient must confirm acceptance."
    elif condition == "poor" and repair_cost > max(resale_value * 0.8, 50):
        recommendation = "component salvage"
        explanation = "The reported repair cost exceeds the configured threshold. Check individual components before selecting salvage or recycling."
    else:
        recommendation = "reuse"
        explanation = "No resale value or clear repair advantage was supplied. Consider safe reuse, then component recovery or an appropriate recycler."
    with connect() as db:
        if product_id is not None:
            product = product_for_user(db, product_id, user["id"])
            db.execute(
                """UPDATE products SET category=?, product_name=?, age_years=?, useful_life_years=?,
                condition=?, visible_damage=?, location=? WHERE id=? AND user_id=?""",
                (category, product_name, age_years, useful_life_years, condition, visible_damage.strip(),
                 location.strip(), product_id, user["id"]),
            )
        else:
            cursor = db.execute(
                """INSERT INTO products(user_id, category, product_name, age_years, useful_life_years,
                condition, visible_damage, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], category, product_name, age_years, useful_life_years, condition,
                 visible_damage.strip(), location.strip()),
            )
            product_id = cursor.lastrowid
        cursor = db.execute(
            "INSERT INTO analyses(product_id, user_id, recommendation, explanation, repair_cost, resale_value, image_name) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (product_id, user["id"], recommendation, explanation, repair_cost, resale_value, image_name),
        )
        analysis_id = cursor.lastrowid
        passport = db.execute("SELECT public_id, events FROM passports WHERE product_id=?", (product_id,)).fetchone()
        if passport:
            public_id = passport["public_id"]
            events = json.loads(passport["events"])
            events.append({"type": "analysis", "detail": f"Updated assessment: {recommendation}", "at": datetime.now(timezone.utc).isoformat()})
            db.execute("UPDATE passports SET events=? WHERE product_id=?", (json.dumps(events), product_id))
        else:
            public_id = f"RL-{uuid.uuid4().hex[:10].upper()}"
            initial = [{"type": "analysis", "detail": f"Initial assessment: {recommendation}", "at": datetime.now(timezone.utc).isoformat()}]
            db.execute("INSERT INTO passports(product_id, user_id, public_id, events) VALUES (?, ?, ?, ?)",
                       (product_id, user["id"], public_id, json.dumps(initial)))
    options_by_action = {
        "repair": {"estimate": f"User cost estimate: {repair_cost:.2f}", "estimated_cost": repair_cost,
                   "estimated_proceeds": None, "eligible": condition != "broken",
                   "note": "Check the quote against the stated resale estimate and the additional useful life."},
        "resale": {"estimate": f"User value estimate: {resale_value:.2f}", "estimated_cost": 0,
                   "estimated_proceeds": resale_value, "eligible": condition in {"excellent", "good"} and resale_value > 0,
                   "note": "Disclose defects accurately; the sale price is not guaranteed."},
        "donation": {"estimate": "Recipient-dependent", "estimated_cost": None,
                     "estimated_proceeds": None, "eligible": condition in {"excellent", "good", "fair"},
                     "note": "Confirm recipient requirements and item safety before handoff."},
        "reuse": {"estimate": "User-dependent", "estimated_cost": None,
                  "estimated_proceeds": None, "eligible": condition != "broken",
                  "note": "Use only for a safe, intended purpose."},
        "component salvage": {"estimate": "Inspection required", "estimated_cost": None,
                              "estimated_proceeds": None, "eligible": True,
                              "note": "Inspect each component; do not assume internal parts work."},
        "recycling": {"estimate": "Facility-dependent", "estimated_cost": None,
                      "estimated_proceeds": None, "eligible": True,
                      "note": "Check accepted materials and safe local handling."},
    }
    preferred_order = [recommendation] + [action for action in options_by_action if action != recommendation]
    comparison = [dict(action=action, **options_by_action[action], recommended=action == recommendation)
                  for action in preferred_order]
    if condition in {"poor", "fair"}:
        threshold = max(resale_value * 0.8, 50)
        calculation = f"Repair threshold = max(80% × resale estimate ({resale_value:.2f}), 50.00) = {threshold:.2f}; entered repair estimate = {repair_cost:.2f}."
    elif condition in {"good", "excellent"}:
        calculation = f"Resale rule checks stated resale estimate ({resale_value:.2f}) against repair estimate ({repair_cost:.2f})."
    else:
        calculation = "Reported broken condition prioritizes component inspection and appropriate recycling over whole-item resale or donation."
    return {
        "id": analysis_id, "product_id": product_id, "passport_id": public_id,
        "category": category, "condition": condition, "recommendation": recommendation,
        "product_name": product_name, "useful_life_years": useful_life_years,
        "location": location.strip(),
        "explanation": explanation, "repair_cost": repair_cost, "resale_value": resale_value,
        "decision_calculation": calculation,
        "options": comparison,
        "inference_mode": "rule-based demo",
        "image_note": "Images are validated but not analyzed. A photo cannot establish internal faults." if image_name else "No image supplied. Inputs are user-reported.",
    }


@app.get("/api/history")
def history(user: User):
    with connect() as db:
        rows = db.execute(
            """SELECT a.id, a.product_id, p.category, p.product_name, p.age_years, p.useful_life_years,
            p.condition, p.visible_damage, p.location,
            a.recommendation, a.explanation, a.repair_cost, a.resale_value, a.created_at,
            ps.public_id AS passport_id
            FROM analyses a JOIN products p ON p.id=a.product_id
            JOIN passports ps ON ps.product_id=p.id
            WHERE a.user_id=? ORDER BY a.id DESC""",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


def passport_details(db, product_id: int, user_id: int, frontend_origin: str):
    row = db.execute(
        """SELECT ps.public_id, ps.events, ps.created_at, p.id AS product_id, p.category,
        p.product_name, p.age_years, p.useful_life_years, p.condition, p.visible_damage, p.location
        FROM passports ps JOIN products p ON p.id=ps.product_id
        WHERE p.id=? AND ps.user_id=?""", (product_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Passport not found")
    result = dict(row)
    result["events"] = json.loads(result["events"])
    result["analysis_history"] = [dict(item) for item in db.execute(
        "SELECT recommendation, explanation, repair_cost, resale_value, created_at FROM analyses WHERE product_id=? AND user_id=? ORDER BY id DESC",
        (product_id, user_id),
    ).fetchall()]
    components = db.execute(
        "SELECT components FROM component_assessments WHERE product_id=? AND user_id=? ORDER BY id DESC LIMIT 1",
        (product_id, user_id),
    ).fetchone()
    result["components"] = json.loads(components["components"]) if components else []
    plan = db.execute(
        "SELECT id FROM recovery_plans WHERE product_id=? AND user_id=? ORDER BY id DESC LIMIT 1",
        (product_id, user_id),
    ).fetchone()
    result["recovery_plan"] = None
    if plan:
        result["recovery_plan"] = [dict(item) for item in db.execute(
            "SELECT action, reason, status FROM plan_steps WHERE plan_id=? ORDER BY id",
            (plan["id"],),
        ).fetchall()]
    result["verification_note"] = "Ownership and user-submitted history are not independently verified."
    result["qr_payload"] = f"{frontend_origin.rstrip('/')}?passport={result['public_id']}"
    return result


@app.get("/api/passports/lookup/{public_id}")
def passport_by_public_id(public_id: str, request: Request, user: User):
    with connect() as db:
        row = db.execute("SELECT product_id FROM passports WHERE public_id=? AND user_id=?",
                         (public_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Passport not found for this account")
        origin = request.headers.get("origin") or os.getenv("RELIFE_FRONTEND_URL", "http://localhost:5173")
        return passport_details(db, row["product_id"], user["id"], origin)


@app.get("/api/passports/{product_id}")
def get_passport(product_id: int, request: Request, user: User):
    with connect() as db:
        origin = request.headers.get("origin") or os.getenv("RELIFE_FRONTEND_URL", "http://localhost:5173")
        return passport_details(db, product_id, user["id"], origin)


@app.post("/api/passports/{product_id}/updates", status_code=201)
def passport_update(product_id: int, body: UpdateInput, user: User):
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        db.execute("INSERT INTO product_updates(user_id, product_id, update_type, detail) VALUES (?, ?, ?, ?)",
                   (user["id"], product_id, body.update_type, body.detail))
        passport = db.execute("SELECT events FROM passports WHERE product_id=?", (product_id,)).fetchone()
        events = json.loads(passport["events"])
        events.append({"type": body.update_type, "detail": body.detail, "at": datetime.now(timezone.utc).isoformat()})
        db.execute("UPDATE passports SET events=? WHERE product_id=?", (json.dumps(events), product_id))
    return {"status": "recorded", "note": "This user-submitted event is not independently verified."}


@app.post("/api/passports/{product_id}/transfer", status_code=201)
def transfer_passport(product_id: int, body: TransferInput, user: User):
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        passport = db.execute("SELECT events FROM passports WHERE product_id=?", (product_id,)).fetchone()
        events = json.loads(passport["events"])
        events.append({"type": "demo ownership transfer", "detail": f"Transfer proposed to {body.new_owner_email}: {body.note}", "at": datetime.now(timezone.utc).isoformat()})
        db.execute("UPDATE passports SET events=? WHERE product_id=?", (json.dumps(events), product_id))
    return {"status": "pending", "note": "Demo transfer recorded only; ownership is not verified or changed."}


@app.get("/api/matches/{product_id}")
def matches(product_id: int, user: User):
    with connect() as db:
        product = product_for_user(db, product_id, user["id"])
        requests = db.execute("SELECT * FROM recipient_requests").fetchall()
        decisions = db.execute("SELECT request_id, status FROM match_decisions WHERE user_id=? AND product_id=?",
                               (user["id"], product_id)).fetchall()
    statuses = {row["request_id"]: row["status"] for row in decisions}
    quality = {"excellent": 4, "good": 3, "fair": 2, "poor": 1, "broken": 0}.get(product["condition"], 0)
    ranked = []
    for request in requests:
        category_match = request["category"] == product["category"] or request["category"] == "household" and product["category"] in {"appliance", "household"}
        if not category_match:
            continue
        required = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}.get(request["min_condition"], 2)
        location_match = bool(product["location"] and (
            product["location"].casefold() in request["location"].casefold()
            or request["location"].casefold() in product["location"].casefold()
        ))
        location_points = 20 if location_match else 10 if not product["location"] else 0
        score = 50 + (30 if quality >= required else 0) + location_points
        location_reason = (
            f"Location matches ({request['location']})." if location_match
            else f"Location differs from {request['location']}." if product["location"]
            else "No product location supplied; location match is neutral."
        )
        ranked.append({**dict(request), "score": score, "status": statuses.get(request["id"], "pending"),
                       "reason": f"Category fits; condition {'meets' if quality >= required else 'may not meet'} the stated requirement. {location_reason} Recipient location is sample data."})
    return sorted(ranked, key=lambda item: (-item["score"], item["name"]))


@app.patch("/api/matches/{product_id}/{request_id}")
def update_match(product_id: int, request_id: int, body: MatchStateInput, user: User):
    if body.status not in {"pending", "accepted", "completed"}:
        raise HTTPException(status_code=422, detail="Status must be pending, accepted, or completed")
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        if not db.execute("SELECT id FROM recipient_requests WHERE id=?", (request_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Sample request not found")
        db.execute("""INSERT INTO match_decisions(user_id, product_id, request_id, status) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, product_id, request_id) DO UPDATE SET status=excluded.status""",
            (user["id"], product_id, request_id, body.status))
    return {"request_id": request_id, "status": body.status, "note": "Demo match status; recipient response is not real."}


@app.post("/api/salvage/{product_id}", status_code=201)
def salvage(product_id: int, body: ComponentInput, user: User):
    choices = {
        "electronics": [("power cable", "replacement cable or e-waste recovery"), ("enclosure", "storage or parts reuse"), ("display", "replacement screen only after testing"), ("battery", "approved battery recovery; do not assume working")],
        "laptop": [("display", "screen reuse after a separate function test"), ("RAM", "memory reuse after compatibility and function tests"), ("SSD", "storage reuse after health and data-erasure checks"), ("keyboard", "replacement part after testing"), ("power adapter", "reuse only after electrical safety checks"), ("battery", "approved battery recovery; do not assume working")],
        "mobile_phone": [("display", "screen reuse after a separate function test"), ("camera modules", "parts recovery after testing and compatibility checks"), ("speaker", "parts recovery after testing"), ("charging port", "replacement part after testing"), ("battery", "approved battery recovery; do not assume working")],
        "furniture": [("frame", "repair or workshop material"), ("hardware", "replacement fasteners"), ("panels", "small shelves or craft material"), ("upholstery", "patch material or textile recovery")],
        "chair": [("frame", "repair only after checking structural integrity"), ("casters", "replacement or reuse after testing"), ("armrests", "replacement part after checking"), ("upholstery", "patch material or textile recovery")],
        "clothing": [("buttons / zippers", "garment repair"), ("fabric panels", "patches or craft reuse"), ("lining", "textile reuse"), ("fasteners", "repair supplies")],
        "household": [("outer casing", "parts or material recovery"), ("cord / fittings", "reuse only after safety checks"), ("containers", "storage reuse if clean"), ("metal / glass", "appropriate material stream")],
        "household_appliance": [("power cord", "reuse only after electrical safety checks"), ("motor", "parts recovery after a qualified function test"), ("control panel", "parts recovery after testing"), ("casing", "material recovery after safe disassembly"), ("battery", "approved battery recovery; do not assume working")],
    }
    if body.category not in choices:
        raise HTTPException(status_code=422, detail="Choose a supported product type")
    prior = {}
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        saved = db.execute(
            "SELECT components FROM component_assessments WHERE user_id=? AND product_id=? ORDER BY id DESC LIMIT 1",
            (user["id"], product_id),
        ).fetchone()
        if saved:
            prior = {item["name"]: item for item in json.loads(saved["components"])}
        components = []
        value_ranges = {
            "display": (15, 50), "ram": (10, 40), "ssd": (10, 35), "keyboard": (5, 20),
            "power adapter": (5, 20), "casters": (5, 20), "armrests": (5, 15),
            "power cable": (3, 12), "camera modules": (5, 25), "speaker": (3, 15),
            "charging port": (3, 15), "motor": (10, 40), "control panel": (8, 30),
        }
        for name, use in choices[body.category]:
            old = prior.get(name, {})
            state = body.condition_states.get(name)
            if state is None and name in body.confirmations:
                state = "working" if body.confirmations[name] else "untested"
            state = state or old.get("condition_state", "untested")
            if state not in {"working", "damaged", "untested"}:
                raise HTTPException(status_code=422, detail=f"Invalid condition state for {name}")
            estimate = value_ranges.get(name.casefold()) if state == "working" else None
            components.append({
                "name": name, "potential_use": use, "condition_state": state,
                "user_confirmed_condition": state == "working",
                "estimated_value_range": {"low": estimate[0], "high": estimate[1], "basis": "illustrative demo range; verify locally"} if estimate else None,
                "recovery_route": "reuse after verification" if state == "working" else "inspection before reuse" if state == "untested" else "parts/material recovery or appropriate recycling",
                "verification": "Condition is user-reported; functional safety is not independently verified.",
            })
        db.execute("INSERT INTO component_assessments(user_id, product_id, components) VALUES (?, ?, ?)",
                   (user["id"], product_id, json.dumps(components)))
    total_low = sum(item["estimated_value_range"]["low"] for item in components if item["estimated_value_range"])
    total_high = sum(item["estimated_value_range"]["high"] for item in components if item["estimated_value_range"])
    return {"components": components, "estimated_salvage_value": {"low": total_low, "high": total_high} if total_high else None,
            "value_note": "Illustrative demo ranges for user-marked working components only; not market quotes. Untested or hidden components receive no value estimate.",
            "recovery_options": ["component reuse after inspection", "authorized material recovery", "appropriate local recycling"]}


@app.get("/api/salvage/{product_id}")
def get_salvage(product_id: int, user: User):
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        row = db.execute(
            "SELECT components FROM component_assessments WHERE user_id=? AND product_id=? ORDER BY id DESC LIMIT 1",
            (user["id"], product_id),
        ).fetchone()
    return {"components": json.loads(row["components"]) if row else [], "saved": bool(row)}


@app.post("/api/simulations")
def simulate(body: SimulationInput, user: User):
    with connect() as db:
        product_for_user(db, body.product_id, user["id"])
    years = body.period_years
    # Costs and waste quantities are user-entered proxies, not measured environmental impacts.
    results = [
        {"action": "repair", "estimated_cost": round(body.repair_cost, 2), "estimated_value": round(body.resale_value, 2), "useful_life_years": body.useful_life_years,
         "waste_avoided_units": min(years, body.useful_life_years), "impact": "Potentially extends product use; no emissions estimate."},
        {"action": "resale", "estimated_cost": 0, "estimated_value": round(body.resale_value, 2), "useful_life_years": body.useful_life_years,
         "waste_avoided_units": min(years, body.useful_life_years), "impact": "Potential continued use by another owner; not measured."},
        {"action": "donation", "estimated_cost": 0, "estimated_value": 0, "useful_life_years": body.useful_life_years,
         "waste_avoided_units": min(years, body.useful_life_years), "impact": "Recipient use and acceptance are uncertain."},
        {"action": "reuse", "estimated_cost": round(body.reuse_value, 2), "estimated_value": 0, "useful_life_years": body.useful_life_years,
         "waste_avoided_units": min(years, body.useful_life_years), "impact": "Depends on the new use and product condition."},
        {"action": "salvage", "estimated_cost": 0, "estimated_value": round(body.salvage_value, 2), "useful_life_years": 0,
         "waste_avoided_units": 0.5 if body.salvage_value > 0 else 0, "impact": "Potential parts recovery; component condition must be checked."},
        {"action": "recycling", "estimated_cost": 0, "estimated_value": 0, "useful_life_years": 0,
         "waste_avoided_units": 0.25, "impact": "Recovery depends on local facilities and accepted materials."},
    ]
    for result in results:
        result["period_years"] = years
        used_years = min(years, result["useful_life_years"])
        uncovered_years = years - used_years
        result["estimated_total_cost"] = round(
            result["estimated_cost"] + body.replacement_cost_per_year * uncovered_years, 2
        )
        result["estimated_net_cost"] = round(result["estimated_total_cost"] - result["estimated_value"], 2)
        result["cost_per_additional_year"] = (
            round(result["estimated_total_cost"] / result["useful_life_years"], 2)
            if result["useful_life_years"] > 0 else None
        )
        result["uncertainty"] = "Illustrative estimate based on user inputs; not a measured environmental outcome."
    with connect() as db:
        db.execute("INSERT INTO scenario_comparisons(user_id, product_id, assumptions, results) VALUES (?, ?, ?, ?)",
                   (user["id"], body.product_id, body.model_dump_json(), json.dumps(results)))
    best = min(results, key=lambda item: item["estimated_net_cost"])
    return {"results": results, "best_action": best["action"], "formula": "Estimated total cost = one-time pathway cost + user-entered replacement cost per uncovered year; estimated net cost = total cost - user-entered resale/salvage value. Cost per additional year = estimated total cost / assumed additional useful-life years. Potential continued-use proxy = assumed use years within the selected period.",
            "assumptions": body.model_dump(), "disclaimer": "No precise carbon or environmental savings are calculated."}


@app.get("/api/simulations/{product_id}")
def get_simulation(product_id: int, user: User):
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        row = db.execute(
            """SELECT assumptions, results FROM scenario_comparisons WHERE user_id=? AND product_id=?
            ORDER BY id DESC LIMIT 1""",
            (user["id"], product_id),
        ).fetchone()
    if not row:
        return None
    results = json.loads(row["results"])
    best = min(results, key=lambda item: item["estimated_net_cost"]) if results else None
    return {
        "assumptions": json.loads(row["assumptions"]),
        "results": results,
        "best_action": best["action"] if best else None,
        "formula": "Estimated total cost = one-time pathway cost + user-entered replacement cost per uncovered year; estimated net cost = total cost - user-entered resale/salvage value. Cost per additional year = estimated total cost / assumed additional useful-life years. Potential continued-use proxy = assumed use years within the selected period.",
        "disclaimer": "No precise carbon or environmental savings are calculated.",
    }


@app.get("/api/centers")
def centers(user: User, category: str = "", location: str = "", kind: str = ""):
    query = "SELECT * FROM recovery_centers WHERE 1=1"
    params = []
    if category:
        query += " AND (categories LIKE ?)"
        params.append(f"%{category.lower()}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if kind:
        query += " AND kind = ?"
        params.append(kind.lower())
    with connect() as db:
        rows = db.execute(query, params).fetchall()
    return [{**dict(row), "availability": "sample listing; live availability and contact details are not provided"} for row in rows]


def overpass_query(latitude: float, longitude: float, kind: str) -> str:
    around = f"(around:12000,{latitude},{longitude})"
    selectors = {
        "repair": [
            f'nwr{around}[craft~"repair|electronics_repair|bicycle_repair"];',
            f'nwr{around}[shop=repair];',
            f'nwr{around}[amenity=repair];',
        ],
        "donation": [
            f'nwr{around}[shop=charity];',
            f'nwr{around}[amenity=charity];',
        ],
        "reuse": [
            f'nwr{around}[shop~"second_hand|used|furniture|clothes"];',
            f'nwr{around}[amenity=second_hand];',
        ],
        "recycling": [
            f'nwr{around}[amenity=recycling];',
            f'nwr{around}[recycling_type=centre];',
        ],
        "": [
            f'nwr{around}[craft~"repair|electronics_repair|bicycle_repair"];',
            f'nwr{around}[shop~"repair|charity|second_hand|used|furniture|clothes"];',
            f'nwr{around}[amenity~"repair|charity|recycling|second_hand"];',
            f'nwr{around}[recycling_type=centre];',
        ],
    }
    return "[out:json][timeout:15];(" + "".join(selectors[kind]) + ");out center tags 60;"


async def geocode_location(location: str) -> tuple[float, float] | None:
    global LAST_NOMINATIM_REQUEST
    key = location.casefold().strip()
    cached = GEOCODE_CACHE.get(key)
    if cached and monotonic() - cached[0] < LIVE_CACHE_TTL_SECONDS:
        return cached[1]

    async with NOMINATIM_LOCK:
        cached = GEOCODE_CACHE.get(key)
        if cached and monotonic() - cached[0] < LIVE_CACHE_TTL_SECONDS:
            return cached[1]
        wait_seconds = 1.0 - (monotonic() - LAST_NOMINATIM_REQUEST)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)
        LAST_NOMINATIM_REQUEST = monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(6, connect=3),
                headers={"User-Agent": OPENSTREETMAP_USER_AGENT},
            ) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location, "format": "jsonv2", "limit": 1},
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Location lookup timed out. Try again in a moment.")
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Location lookup is temporarily unavailable.")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Location lookup is temporarily unavailable.")
        try:
            results = response.json()
            coordinates = (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
        except (ValueError, KeyError, TypeError, IndexError):
            raise HTTPException(status_code=502, detail="Location lookup returned an invalid response.")
        if len(GEOCODE_CACHE) > 200:
            GEOCODE_CACHE.clear()
        GEOCODE_CACHE[key] = (monotonic(), coordinates)
        return coordinates


def classify_osm_center(tags: dict) -> str:
    if tags.get("amenity") == "recycling" or tags.get("recycling_type") == "centre":
        return "recycling"
    if tags.get("shop") == "charity" or tags.get("amenity") == "charity":
        return "donation"
    if tags.get("craft") in {"repair", "electronics_repair", "bicycle_repair"} or tags.get("shop") == "repair":
        return "repair"
    if tags.get("shop") in {"second_hand", "used", "furniture", "clothes"} or tags.get("amenity") == "second_hand":
        return "reuse"
    return "recovery"


def evaluate_opening_hours(hours: str | None, latitude: float, longitude: float) -> tuple[str, str]:
    if not hours:
        return "unknown", "Opening hours not listed; current status unknown."
    try:
        schedule = opening_hours_parser.OpeningHours(
            hours,
            coords=(latitude, longitude),
            auto_timezone=True,
            auto_country=True,
        )
        state, _comment = schedule.state()
    except (SyntaxError, ValueError, opening_hours_parser.ParserError,
            opening_hours_parser.InvalidCoordinatesError, opening_hours_parser.UnknownCountryError):
        return "unknown", f"Hours listed ({hours}); could not determine current status."
    if state == opening_hours_parser.State.OPEN:
        return "open", f"Open now according to listed hours: {hours}."
    if state == opening_hours_parser.State.CLOSED:
        return "closed", f"Closed now according to listed hours: {hours}."
    return "unknown", f"Hours listed ({hours}); current status unknown."


def refresh_center_availability(center: dict) -> None:
    status, summary = evaluate_opening_hours(
        center.get("opening_hours"),
        center["latitude"],
        center["longitude"],
    )
    center["availability_status"] = status
    center["availability"] = summary


async def query_openstreetmap(location: str, kind: str) -> dict:
    cache_key = f"{location.casefold().strip()}|{kind}"
    cached = LIVE_CENTER_CACHE.get(cache_key)
    if cached and monotonic() - cached[0] < LIVE_CACHE_TTL_SECONDS:
        for center in cached[1]["centers"]:
            refresh_center_availability(center)
        return cached[1]

    coordinates = await geocode_location(location)
    if coordinates is None:
        result = {
            "centers": [],
            "message": "No matching location was found. Try a city, district, or postal code.",
        }
        LIVE_CENTER_CACHE[cache_key] = (monotonic(), result)
        return result

    query = overpass_query(coordinates[0], coordinates[1], kind)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(9, connect=3),
            headers={"User-Agent": OPENSTREETMAP_USER_AGENT},
        ) as client:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                content=query,
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Nearby provider search timed out. Try again shortly.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Nearby provider search is temporarily unavailable.")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="The OpenStreetMap provider search is temporarily unavailable.")
    try:
        elements = response.json().get("elements", [])
    except (ValueError, AttributeError):
        raise HTTPException(status_code=502, detail="The provider search returned an invalid response.")

    found = []
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("operator")
        if not name:
            continue
        center = element.get("center", element)
        latitude = center.get("lat")
        longitude = center.get("lon")
        osm_type = element.get("type")
        osm_id = element.get("id")
        if not osm_type or not osm_id or latitude is None or longitude is None:
            continue
        address = ", ".join(
            part for part in (
                tags.get("addr:street"),
                tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:suburb"),
                tags.get("addr:postcode"),
            ) if part
        )
        phone = tags.get("contact:phone") or tags.get("phone") or tags.get("phone:mobile")
        email = tags.get("contact:email") or tags.get("email")
        website = tags.get("contact:website") or tags.get("website") or tags.get("url")
        if website and not website.startswith(("https://", "http://")):
            website = f"https://{website}"
        found.append({
            "id": f"osm-{osm_type}-{osm_id}",
            "name": name,
            "kind": classify_osm_center(tags),
            "location": address or "Address not listed",
            "description": tags.get("description") or tags.get("service:description") or "OpenStreetMap provider listing.",
            "phone": phone,
            "email": email,
            "website": website,
            "opening_hours": tags.get("opening_hours"),
            "availability": "",
            "availability_status": "unknown",
            "contact_note": "Only contact details present in OpenStreetMap are shown." if any((phone, email, website)) else "No phone, email, or website is listed in OpenStreetMap.",
            "categories": "",
            "map_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
            "latitude": latitude,
            "longitude": longitude,
            "demo": False,
        })
        refresh_center_availability(found[-1])
    result = {"centers": found, "message": None}
    if len(LIVE_CENTER_CACHE) > 200:
        LIVE_CENTER_CACHE.clear()
    LIVE_CENTER_CACHE[cache_key] = (monotonic(), result)
    return result


@app.get("/api/centers/live")
async def live_centers(
    user: User,
    location: str = Query(min_length=2, max_length=100),
    kind: str = "",
):
    normalized_kind = kind.strip().lower()
    if normalized_kind not in {"", "repair", "donation", "reuse", "recycling"}:
        raise HTTPException(status_code=422, detail="Choose a supported recovery pathway")
    location = location.strip()
    if not location or not re.search(r"[A-Za-z0-9]", location):
        raise HTTPException(status_code=422, detail="Enter a city, district, or postal code")
    result = await query_openstreetmap(location, normalized_kind)
    return {
        **result,
        "source": "OpenStreetMap",
        "searched_location": location,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "attribution": "© OpenStreetMap contributors",
        "availability_note": "Listings and published hours come from OpenStreetMap and may be incomplete or out of date. OpenStreetMap does not provide appointment slots or real-time service capacity; contact the provider to confirm.",
    }


@app.post("/api/plans/{product_id}", status_code=201)
def create_plan(product_id: int, user: User):
    with connect() as db:
        product = product_for_user(db, product_id, user["id"])
        analysis = db.execute("SELECT * FROM analyses WHERE product_id=? ORDER BY id DESC LIMIT 1", (product_id,)).fetchone()
        centers = db.execute("SELECT * FROM recovery_centers").fetchall()
        cursor = db.execute("INSERT INTO recovery_plans(user_id, product_id) VALUES (?, ?)", (user["id"], product_id))
        plan_id = cursor.lastrowid
        steps = []
        repair_ok = bool(analysis and analysis["repair_cost"] <= max(analysis["resale_value"] * 0.8, 50))
        condition = product["condition"]
        allowed = {
            "excellent": ["resale", "donation", "reuse", "repair", "component salvage", "recycling"],
            "good": ["resale", "donation", "reuse", "repair", "component salvage", "recycling"],
            "fair": ["repair", "donation", "reuse", "component salvage", "recycling"],
            "poor": ["repair", "component salvage", "recycling"],
            "broken": ["component salvage", "recycling"],
        }[condition]
        reason_by_action = {
            "repair": "Reported condition may be recoverable and the latest stated repair estimate meets the demo threshold; get a qualified quote.",
            "resale": "Reported good condition and stated resale estimate support trying a transfer; disclose defects accurately.",
            "donation": "A suitable recipient may extend use; confirm condition and acceptance before handoff.",
            "reuse": "Consider only a safe, intended new use and do not bypass electrical or structural checks.",
            "component salvage": "Inspect components one by one; use trained handling for batteries, mains-powered equipment, and hazardous materials.",
            "recycling": "Use a suitable facility and follow local material and safety rules.",
        }
        order = [analysis["recommendation"]] if analysis and analysis["recommendation"] in allowed else []
        order.extend(action for action in allowed if action not in order)
        steps = [(action, reason_by_action[action]) for action in order
                 if action != "repair" or repair_ok]
        result_steps = []
        for action, reason in steps:
            provider = next((center for center in centers if center["kind"] in action or action in center["kind"] and product["category"] in center["categories"]), None)
            cursor = db.execute("INSERT INTO plan_steps(plan_id, action, reason, provider_id) VALUES (?, ?, ?, ?)",
                                (plan_id, action, reason, provider["id"] if provider else None))
            result_steps.append({"id": cursor.lastrowid, "action": action, "reason": reason, "status": "pending",
                                 "provider": provider["name"] if provider else None,
                                 "fallback": "Search sample centers or choose another pathway if no provider is listed." if not provider else None})
    return {"id": plan_id, "product_id": product_id, "steps": result_steps, "rules": "Configurable demo rules; estimates and provider availability are not verified."}


@app.get("/api/plans/{product_id}")
def get_plan(product_id: int, user: User):
    with connect() as db:
        product_for_user(db, product_id, user["id"])
        plan = db.execute("SELECT id FROM recovery_plans WHERE user_id=? AND product_id=? ORDER BY id DESC LIMIT 1",
                      (user["id"], product_id)).fetchone()
        if not plan:
            return None
        return _plan_response(db, plan["id"], product_id)


def _plan_response(db, plan_id: int, product_id: int):
    steps = db.execute(
        """SELECT s.id, s.action, s.reason, s.status, c.name AS provider FROM plan_steps s
        LEFT JOIN recovery_centers c ON c.id=s.provider_id WHERE s.plan_id=? ORDER BY s.id""",
        (plan_id,),
    ).fetchall()
    return {"id": plan_id, "product_id": product_id, "steps": [
        {**dict(row), "fallback": "Search for an alternative provider or choose the next recovery route." if not row["provider"] else None}
        for row in steps
    ], "rules": "Configurable demo rules; estimates and provider availability are not verified."}


@app.post("/api/plans/{product_id}/steps/{step_id}/alternative")
def add_plan_alternative(product_id: int, step_id: int, user: User):
    with connect() as db:
        product = product_for_user(db, product_id, user["id"])
        step = db.execute(
            """SELECT s.id, s.plan_id, s.status FROM plan_steps s JOIN recovery_plans p ON p.id=s.plan_id
            WHERE s.id=? AND p.product_id=? AND p.user_id=? ORDER BY p.id DESC LIMIT 1""",
            (step_id, product_id, user["id"]),
        ).fetchone()
        if not step:
            raise HTTPException(status_code=404, detail="Recovery step not found")
        if step["status"] != "unavailable":
            raise HTTPException(status_code=409, detail="Mark the step unavailable before requesting an alternative")
        existing = {row["action"] for row in db.execute("SELECT action FROM plan_steps WHERE plan_id=?",
                                                    (step["plan_id"],)).fetchall()}
        safe_alternatives = [
            ("repair", "Fallback only if a qualified provider confirms the item can be safely repaired."),
            ("resale", "Only suitable when the item is functional and its condition is accurately disclosed."),
            ("donation", "Only if the item is safe and the recipient confirms it meets requirements."),
            ("reuse", "Only for a safe, intended use; do not bypass electrical or structural checks."),
            ("component salvage", "Use trained handling for batteries, mains-powered equipment, and hazardous materials."),
            ("recycling", "Use an appropriate facility and follow local handling rules."),
        ]
        allowed = {
            "excellent": {"repair", "resale", "donation", "reuse", "component salvage", "recycling"},
            "good": {"repair", "resale", "donation", "reuse", "component salvage", "recycling"},
            "fair": {"repair", "donation", "reuse", "component salvage", "recycling"},
            "poor": {"repair", "component salvage", "recycling"},
            "broken": {"component salvage", "recycling"},
        }[product["condition"]]
        next_pending = db.execute(
            """SELECT id, action, reason FROM plan_steps WHERE plan_id=? AND id>? AND status='pending'
            ORDER BY id LIMIT 1""", (step["plan_id"], step_id)
        ).fetchone()
        if next_pending:
            response = _plan_response(db, step["plan_id"], product_id)
            response["alternative"] = dict(next_pending)
            return response
        next_step = next(((action, reason) for action, reason in safe_alternatives
                      if action in allowed and action not in existing), None)
        if not next_step:
            response = _plan_response(db, step["plan_id"], product_id)
            response["alternative"] = None
            response["alternative_note"] = "No further safe, unlisted route is available for this reported condition."
            return response
        action, reason = next_step
        cursor = db.execute("INSERT INTO plan_steps(plan_id, action, reason, status) VALUES (?, ?, ?, 'pending')",
                        (step["plan_id"], action, reason))
        response = _plan_response(db, step["plan_id"], product_id)
        response["alternative"] = {"id": cursor.lastrowid, "action": action, "reason": reason}
        return response


@app.patch("/api/plans/steps/{step_id}")
def update_step(step_id: int, body: PlanStateInput, user: User):
    if body.status not in {"pending", "completed", "unavailable"}:
        raise HTTPException(status_code=422, detail="Status must be pending, completed, or unavailable")
    with connect() as db:
        row = db.execute("SELECT s.id FROM plan_steps s JOIN recovery_plans p ON p.id=s.plan_id WHERE s.id=? AND p.user_id=?",
                         (step_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plan step not found")
        db.execute("UPDATE plan_steps SET status=? WHERE id=?", (body.status, step_id))
    return {"id": step_id, "status": body.status}


@app.get("/api/impact")
def impact(user: User):
    with connect() as db:
        rows = db.execute(
            """SELECT a.id, p.category, a.recommendation, a.repair_cost, a.resale_value, a.created_at,
            ps.public_id,
            (SELECT COUNT(*) FROM plan_steps s JOIN recovery_plans rp ON rp.id=s.plan_id
             WHERE rp.product_id=p.id AND rp.user_id=a.user_id AND s.status='completed') AS completed_steps
            ,(SELECT COUNT(*) FROM plan_steps s JOIN recovery_plans rp ON rp.id=s.plan_id
             WHERE rp.product_id=p.id AND rp.user_id=a.user_id) AS plan_steps
            ,(SELECT COUNT(*) FROM plan_steps s JOIN recovery_plans rp ON rp.id=s.plan_id
             WHERE rp.product_id=p.id AND rp.user_id=a.user_id AND s.status='unavailable') AS unavailable_steps
            FROM analyses a JOIN products p ON p.id=a.product_id
            JOIN passports ps ON ps.product_id=p.id WHERE a.user_id=? ORDER BY a.id DESC""",
            (user["id"],),
        ).fetchall()
        weekly = db.execute(
            """SELECT strftime('%Y-%W', created_at) AS period, COUNT(*) AS assessments
            FROM analyses WHERE user_id=? GROUP BY period ORDER BY period DESC LIMIT 8""",
            (user["id"],),
        ).fetchall()
        monthly = db.execute(
            """SELECT strftime('%Y-%m', created_at) AS period, COUNT(*) AS assessments
            FROM analyses WHERE user_id=? GROUP BY period ORDER BY period DESC LIMIT 12""",
            (user["id"],),
        ).fetchall()
    items = [dict(row) for row in rows]
    return {"analyses": items, "total_analyses": len(items),
            "estimated_money_saved": None, "potential_waste_avoided": None,
            "note": "Money saved and waste avoided are not measured; no numeric impact totals are fabricated.",
            "weekly": [dict(row) for row in reversed(weekly)],
            "monthly": [dict(row) for row in reversed(monthly)]}
