"""Database models and shared constants for EmergencyCare 360."""
import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import deferred

db = SQLAlchemy()
BLOB = LargeBinary().with_variant(LONGBLOB(), "mysql")

STATUSES = ["Registered", "Waiting for assessment", "Under assessment",
            "Treatment in progress", "Referred", "Discharged"]
STATUSES_HI = ["पंजीकृत", "जांच की प्रतीक्षा", "जांच जारी",
               "इलाज जारी", "रेफर किया गया", "छुट्टी दी गई"]
ACTIVE_MAX = 3  # statuses 0-3 are "active"; 4 (Referred) and 5 (Discharged) are closed
PRIORITIES = ["Not set", "Immediate", "Urgent", "Standard"]
DEPARTMENTS = ["Unassigned", "General", "Cardiology", "Orthopedics",
               "Pediatrics", "Surgery", "Neurology"]
WARDS = ["Emergency", "ICU", "Ward"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def new_token(n=12):
    return secrets.token_urlsafe(n)


class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="nurse")  # clinician | nurse
    password_hash = db.Column(db.String(255), nullable=False)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, index=True)
    token = db.Column(db.String(32), unique=True, nullable=False, default=new_token)
    family_token = db.Column(db.String(32), unique=True, nullable=False, default=new_token)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    kin_phone = db.Column(db.String(20), nullable=False, default="")
    symptoms = db.Column(db.Text, nullable=False)
    history = db.Column(db.String(300), nullable=False, default="")
    allergies = db.Column(db.String(300), nullable=False, default="")
    lang = db.Column(db.String(2), nullable=False, default="en")
    consent = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    priority = db.Column(db.String(12), nullable=False, default="Not set")
    priority_by = db.Column(db.String(80))
    priority_at = db.Column(db.DateTime)
    dept = db.Column(db.String(24), nullable=False, default="Unassigned")
    hr = db.Column(db.Integer)
    bp = db.Column(db.String(8), nullable=False, default="")
    spo2 = db.Column(db.Integer)
    temp = db.Column(db.Float)
    vitals_at = db.Column(db.DateTime)
    report_name = db.Column(db.String(120))
    report_mime = db.Column(db.String(40))
    report_data = deferred(db.Column(BLOB))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    events = db.relationship("StatusEvent", backref="patient", order_by="StatusEvent.at, StatusEvent.id",
                             cascade="all, delete-orphan")

    @property
    def active(self):
        return self.status <= ACTIVE_MAX

    @property
    def first_name(self):
        return (self.name or "").split(" ")[0]


class StatusEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False, index=True)
    status = db.Column(db.Integer, nullable=False)
    at = db.Column(db.DateTime, nullable=False, default=utcnow)
    by = db.Column(db.String(80), nullable=False, default="System")


class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False)
    ward = db.Column(db.String(12), nullable=False)
    out_of_service = db.Column(db.Boolean, nullable=False, default=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), unique=True)
    patient = db.relationship("Patient", backref=db.backref("bed", uselist=False))


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    icon = db.Column(db.String(30), nullable=False, default="box")
    total = db.Column(db.Integer, nullable=False, default=0)
    available = db.Column(db.Integer, nullable=False, default=0)


class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    actor = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="")
    action = db.Column(db.String(24), nullable=False, index=True)
    patient_code = db.Column(db.String(12))
    detail = db.Column(db.String(400), nullable=False, default="")


class AudioCache(db.Model):
    """Generated speech, keyed by hash of (model, voice, language, fixed text)."""
    key = db.Column(db.String(64), primary_key=True)
    lang = db.Column(db.String(2), nullable=False)
    chars = db.Column(db.Integer, nullable=False)
    mime = db.Column(db.String(30), nullable=False, default="audio/mpeg")
    data = db.Column(BLOB, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


def missing_info(p):
    """Flag incomplete records. `by` says who can fill the gap."""
    out = []
    if not p.history:
        out.append({"key": "history", "label": "Medical history", "by": "patient"})
    if not p.allergies:
        out.append({"key": "allergies", "label": "Allergies", "by": "patient"})
    if not p.kin_phone:
        out.append({"key": "kin_phone", "label": "Family contact number", "by": "patient"})
    gaps = [n for n, v in (("blood pressure", p.bp), ("pulse", p.hr), ("SpO₂", p.spo2), ("temperature", p.temp))
            if v in ("", None)]
    if gaps:
        out.append({"key": "vitals", "label": "Vitals: " + ", ".join(gaps), "by": "staff"})
    return out
