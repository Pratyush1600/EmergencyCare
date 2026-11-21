"""EmergencyCare 360 – Flask application.

The software only organises information. Clinical priority and status are always
set by authenticated hospital staff; nothing here diagnoses or triages.
"""
import hmac
import io
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta
from functools import wraps

import certifi
import qrcode
import requests
from dotenv import load_dotenv
from flask import (Flask, Response, abort, g, jsonify, redirect, render_template,
                   request, session, url_for)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import ai_assistant
import voice
from models import (ACTIVE_MAX, DEPARTMENTS, PRIORITIES, STATUSES, STATUSES_HI, WARDS, Audit,
                    Bed, Patient, Resource, Staff, StatusEvent, db, iso, missing_info, utcnow)

MAX_REPORT = 3 * 1024 * 1024
MAGIC = {b"%PDF": ("pdf", "application/pdf"), b"\xff\xd8\xff": ("jpg", "image/jpeg"),
         b"\x89PNG": ("png", "image/png")}
BP_RE = re.compile(r"^\d{2,3}/\d{2,3}$")
_hits = defaultdict(deque)


# ---------------------------------------------------------------- helpers
def hit(key, window):
    """Record an event and return how many happened in the last `window` seconds."""
    now, q = time.time(), _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    q.append(now)
    return len(q)


def recent(key, window):
    now, q = time.time(), _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    return len(q)


def clean(v, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", (v or "").strip())[:n]


def digits(v):
    return re.sub(r"\D", "", v or "")


def valid_phone(v):
    return 7 <= len(digits(v)) <= 15 and re.fullmatch(r"[0-9+\-() ]{7,20}", v or "") is not None


def audit(actor, role, action, code=None, detail=""):
    db.session.add(Audit(actor=actor, role=role, action=action, patient_code=code, detail=detail[:400]))


def db_uri(app):
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        os.makedirs(app.instance_path, exist_ok=True)
        return "sqlite:///" + os.path.join(app.instance_path, "emergencycare.db")
    for old in ("mysql://", "mysql+mysqlconnector://", "tidb://"):
        if url.startswith(old):
            url = "mysql+pymysql://" + url[len(old):]
    return url


def engine_options(uri):
    if uri.startswith("mysql"):
        args = {"charset": "utf8mb4"}
        if os.getenv("DB_SSL", "true").lower() != "false":  # TiDB Cloud requires TLS
            args["ssl"] = {"ca": os.getenv("DB_SSL_CA") or certifi.where()}
        return {"pool_pre_ping": True, "pool_recycle": 280, "connect_args": args}
    return {}


# ---------------------------------------------------------------- app factory
def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    on_render = bool(os.getenv("RENDER"))
    secret = os.getenv("SECRET_KEY")
    if not secret:
        if on_render:
            raise RuntimeError("SECRET_KEY must be set in production")
        secret = secrets.token_hex(32)
    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=db_uri(app),
        MAX_CONTENT_LENGTH=MAX_REPORT + 512 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_render or os.getenv("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        JSON_SORT_KEYS=False,
        ELEVENLABS_AGENT_ID=os.getenv("ELEVENLABS_AGENT_ID", "agent_4201m7y7f9q0fcrrmnh2qkh8zjtw"))
    if config:
        app.config.update(config)
    if on_render and not os.getenv("DATABASE_URL"):
        print("[EmergencyCare360] WARNING: DATABASE_URL not set on Render. SQLite data will be lost on restart.", flush=True)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options(app.config["SQLALCHEMY_DATABASE_URI"])
    if on_render or os.getenv("TRUST_PROXY") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)

    @app.template_global()
    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(24)
        return session["csrf"]

    @app.before_request
    def csrf_guard():
        if request.path in ("/api/ai/ask", "/api/tts/speak"):
            return
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            if not sent or not hmac.compare_digest(sent.encode(), session.get("csrf", "").encode()):
                return jsonify(error="Security check failed. Refresh the page and try again."), 400

    @app.after_request
    def headers(r):
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["Permissions-Policy"] = "camera=(self), microphone=*, geolocation=()"
        r.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: https://elevenlabs.io https://cdn.jsdelivr.net; "
            "worker-src 'self' blob: data: https://elevenlabs.io; "
            "child-src 'self' blob: data: https://elevenlabs.io; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://elevenlabs.io; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https://*.elevenlabs.io https://elevenlabs.io https://storage.googleapis.com; "
            "media-src 'self' blob: data: https://*.elevenlabs.io https://elevenlabs.io https://storage.googleapis.com; "
            "connect-src 'self' https://api.elevenlabs.io https://api.us.elevenlabs.io https://*.elevenlabs.io https://elevenlabs.io https://storage.googleapis.com https://cdn.jsdelivr.net wss://*.elevenlabs.io; "
            "frame-src 'self' https://elevenlabs.io; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if request.path.startswith(("/staff", "/api/track", "/track/")):
            r.headers["Cache-Control"] = "no-store"
        return r

    # -------- auth
    def current_staff():
        if "staff" not in g:
            g.staff = db.session.get(Staff, session["staff_id"]) if session.get("staff_id") else None
        return g.staff

    def staff_required(api=False):
        def deco(fn):
            @wraps(fn)
            def inner(*a, **kw):
                if not current_staff():
                    if api:
                        return jsonify(error="Please sign in again."), 401
                    return redirect(url_for("staff_login"))
                return fn(*a, **kw)
            return inner
        return deco

    @app.context_processor
    def inject():
        return {"staff": current_staff(), "STATUSES": STATUSES, "PRIORITIES": PRIORITIES,
                "DEPARTMENTS": DEPARTMENTS}

    def me():
        s = current_staff()
        return s.display_name, s.role

    # -------- serializers
    def public_view(p):
        patient_missing = [m for m in missing_info(p) if m["by"] == "patient"]
        return {
            "code": p.code, "first_name": p.first_name, "status": p.status,
            "status_label": STATUSES[p.status], "status_label_hi": STATUSES_HI[p.status],
            "created_at": iso(p.created_at), "updated_at": iso(p.updated_at),
            "timeline": [{"status": e.status, "at": iso(e.at)} for e in p.events],
            "bed": p.bed.code if p.bed else None,
            "dept": p.dept if p.dept != "Unassigned" else None,
            "missing": patient_missing, "consent": p.consent,
            "family_url": url_for("family_page", token=p.family_token, _external=True) if p.consent else None,
            "announce": {l: voice.announcement("status", p.status, l) for l in ("en", "hi")},
            "announce_registered": {l: voice.announcement("registered", None, l) for l in ("en", "hi")},
            "voice": voice.enabled(), "qr_url": url_for("qr_public", token=p.token)}

    def row(p):
        return {"code": p.code, "name": p.name, "age": p.age, "status": p.status,
                "status_label": STATUSES[p.status], "priority": p.priority, "dept": p.dept,
                "bed": p.bed.code if p.bed else None, "arrived_at": iso(p.created_at),
                "missing": len(missing_info(p)), "consent": p.consent}

    def detail(p):
        free = Bed.query.filter_by(patient_id=None, out_of_service=False).order_by(Bed.code).all()
        d = row(p)
        d.update({
            "phone": p.phone, "kin_phone": p.kin_phone, "symptoms": p.symptoms,
            "history": p.history, "allergies": p.allergies, "lang": p.lang,
            "vitals": {"hr": p.hr, "bp": p.bp, "spo2": p.spo2, "temp": p.temp, "at": iso(p.vitals_at)},
            "priority_by": p.priority_by, "priority_at": iso(p.priority_at),
            "report": {"name": p.report_name} if p.report_name else None,
            "missing_items": missing_info(p), "updated_at": iso(p.updated_at),
            "timeline": [{"status": e.status, "at": iso(e.at), "by": e.by} for e in p.events],
            "beds_free": [{"code": b.code, "ward": b.ward} for b in free],
            "qr_url": url_for("qr_staff", code=p.code)})
        return d

    def qr_response(data):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        buf = io.BytesIO()
        qr.make_image(fill_color="#142D4E", back_color="white").save(buf, format="PNG")
        return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "private, max-age=3600"})

    # ================================================================ PUBLIC PAGES
    @app.get("/")
    def register_page():
        return render_template("register.html")

    @app.get("/track")
    def track_lookup_page():
        return render_template("lookup.html")

    @app.get("/track/<token>")
    def track_page(token):
        return render_template("track.html", token=token)

    @app.get("/family/<token>")
    def family_page(token):
        return render_template("family.html", token=token)

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            ok = True
        except Exception:
            db.session.rollback()
            ok = False
        return jsonify(status="ok" if ok else "degraded", database="up" if ok else "down",
                       voice="enabled" if voice.enabled() else "disabled"), (200 if ok else 503)

    # ================================================================ PUBLIC API
    @app.post("/api/register")
    def api_register():
        if hit(f"reg:{request.remote_addr}", 3600) > 15:
            return jsonify(error="Too many registrations. Please see the front desk."), 429
        f, errors = request.form, {}
        name = clean(f.get("name"), 80)
        if len(name) < 2:
            errors["name"] = "name_required"
        try:
            age = int(f.get("age", ""))
            if not 0 <= age <= 120:
                raise ValueError
        except ValueError:
            age, errors["age"] = 0, "age_invalid"
        phone = clean(f.get("phone"), 20)
        if not valid_phone(phone):
            errors["phone"] = "phone_invalid"
        kin = clean(f.get("kin_phone"), 20)
        if kin and not valid_phone(kin):
            errors["kin_phone"] = "kin_invalid"
        symptoms = clean(f.get("symptoms"), 600)
        if len(symptoms) < 3:
            errors["symptoms"] = "symptoms_required"
        rep_name = rep_mime = rep_data = None
        file = request.files.get("report")
        if file and file.filename:
            rep_data = file.read(MAX_REPORT + 1)
            if len(rep_data) > MAX_REPORT:
                errors["report"] = "file_size"
            else:
                m = next((v for k, v in MAGIC.items() if rep_data.startswith(k)), None)
                if not m:
                    errors["report"] = "file_type"
                else:
                    rep_mime = m[1]
                    rep_name = secure_filename(file.filename)[:100] or f"report.{m[0]}"
        if errors:
            return jsonify(errors=errors), 422
        p = Patient(name=name, age=age, phone=phone, kin_phone=kin, symptoms=symptoms,
                    history=clean(f.get("history"), 300), allergies=clean(f.get("allergies"), 300),
                    lang="hi" if f.get("lang") == "hi" else "en", consent=f.get("consent") == "1",
                    report_name=rep_name, report_mime=rep_mime, report_data=rep_data)
        db.session.add(p)
        db.session.flush()
        p.code = f"EC-{1000 + p.id}"
        db.session.add(StatusEvent(patient_id=p.id, status=0, by="System"))
        audit("Patient", "patient", "register", p.code, "Emergency registration submitted"
              + (" (report attached)" if rep_name else ""))
        db.session.commit()
        return jsonify(code=p.code, token=p.token, track_url=url_for("track_page", token=p.token)), 201

    @app.post("/api/lookup")
    def api_lookup():
        if hit(f"look:{request.remote_addr}", 600) > 10:
            return jsonify(error="rate"), 429
        d = request.get_json(silent=True) or {}
        code = clean(d.get("code"), 12).upper()
        ph = digits(d.get("phone"))[-10:]
        p = Patient.query.filter_by(code=code).first()
        if not p or len(ph) < 7 or digits(p.phone)[-10:] != ph:
            return jsonify(error="not_found"), 404
        return jsonify(track_url=url_for("track_page", token=p.token), token=p.token)

    def patient_by_token(token):
        p = Patient.query.filter_by(token=token).first()
        if not p:
            abort(404)
        return p

    @app.get("/api/track/<token>")
    def api_track(token):
        return jsonify(public_view(patient_by_token(token)))

    @app.post("/api/track/<token>/details")
    def api_track_details(token):
        p = patient_by_token(token)
        if hit(f"det:{token}", 3600) > 40:
            return jsonify(error="rate"), 429
        d = request.get_json(silent=True) or {}
        changed = []
        for key, n in (("history", 300), ("allergies", 300)):
            if key in d:
                setattr(p, key, clean(d[key], n))
                changed.append(key)
        if "kin_phone" in d:
            kin = clean(d["kin_phone"], 20)
            if kin and not valid_phone(kin):
                return jsonify(errors={"kin_phone": "kin_invalid"}), 422
            p.kin_phone = kin
            changed.append("family contact")
        if "consent" in d:
            p.consent = bool(d["consent"])
            changed.append("family sharing " + ("on" if p.consent else "off"))
        if changed:
            p.updated_at = utcnow()
            audit("Patient", "patient", "patient_update", p.code, "Patient updated: " + ", ".join(changed))
            db.session.commit()
        return jsonify(public_view(p))

    @app.get("/api/family/<token>")
    def api_family(token):
        p = Patient.query.filter_by(family_token=token).first()
        if not p or not p.consent:
            return jsonify(error="inactive"), 404
        return jsonify(first_name=p.first_name, status=p.status, status_label=STATUSES[p.status],
                       status_label_hi=STATUSES_HI[p.status], updated_at=iso(p.updated_at))

    @app.get("/qr/<token>.png")
    def qr_public(token):
        return qr_response("EC360:" + patient_by_token(token).code)

    @app.get("/api/tts")
    def api_tts():
        text_ = voice.announcement(request.args.get("kind", "status"), request.args.get("state"),
                                   request.args.get("lang", "en"))
        if not text_:
            return jsonify(error="bad_request"), 400
        if not voice.enabled():
            return jsonify(error="voice_unavailable"), 503
        if hit(f"tts:{request.remote_addr}", 3600) > 120:
            return jsonify(error="rate"), 429
        try:
            data, mime = voice.synthesize(text_, request.args.get("lang", "en"))
        except voice.VoiceError:
            return jsonify(error="voice_unavailable"), 502
        return Response(data, mimetype=mime, headers={"Cache-Control": "public, max-age=86400"})

    @app.route("/api/tts/speak", methods=["GET", "POST"])
    def api_tts_speak():
        lang = request.args.get("lang") or (request.json.get("lang") if request.is_json else "") or "en"
        if lang not in ("en", "hi"):
            lang = "en"
        text_ = (request.args.get("text") or (request.json.get("text") if request.is_json else "") or "").strip()
        token = request.args.get("token") or (request.json.get("token") if request.is_json else None)

        if token:
            p = Patient.query.filter_by(token=token).first()
            if p:
                status_txt = STATUSES_HI[p.status] if lang == "hi" else STATUSES[p.status]
                bed_obj = Bed.query.filter_by(patient_id=p.id).first()
                bed_txt = f", बिस्तर: {bed_obj.code}" if (bed_obj and lang == "hi") else (f", Bed: {bed_obj.code}" if bed_obj else "")
                dept_txt = f", विभाग: {p.dept}" if (p.dept and lang == "hi") else (f", Department: {p.dept}" if p.dept else "")
                if lang == "hi":
                    text_ = f"नमस्ते {p.first_name}। आपकी वर्तमान स्थिति {status_txt} है।{dept_txt}{bed_txt}। अस्पताल के कर्मचारी आपकी सहायता कर रहे हैं।"
                else:
                    text_ = f"Hello {p.first_name}. Your emergency status is currently {status_txt}{dept_txt}{bed_txt}. Hospital staff are coordinating your care."

        if not text_:
            return jsonify(error="text_required"), 400
        if len(text_) > 600:
            text_ = text_[:600]

        if hit(f"tts:{request.remote_addr}", 3600) > 120:
            return jsonify(error="rate_limit"), 429

        if voice.enabled():
            try:
                data, mime = voice.synthesize(text_, lang)
                return Response(data, mimetype=mime, headers={"Cache-Control": "public, max-age=86400", "X-Voice-Engine": "ElevenLabs"})
            except voice.VoiceError as err:
                return jsonify(error="upstream_elevenlabs", detail=str(err), text=text_, lang=lang), 502

        return jsonify(
            status="client_playback",
            text=text_,
            lang=lang,
            voice_engine="device_speech_synthesis",
            notice="Set ELEVENLABS_API_KEY in .env to stream studio-grade ElevenLabs human voice audio."
        ), 200

    @app.get("/api/elevenlabs/agent")
    def api_elevenlabs_agent():
        agent_id = app.config.get("ELEVENLABS_AGENT_ID")
        return jsonify(agent_id=agent_id)

    @app.get("/api/elevenlabs/signed-url")
    def api_elevenlabs_signed_url():
        agent_id = app.config.get("ELEVENLABS_AGENT_ID")
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not agent_id:
            return jsonify(error="No agent ID configured"), 400
        if not api_key:
            return jsonify(signed_url=None, agent_id=agent_id)
        try:
            resp = requests.get(
                f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}",
                headers={"xi-api-key": api_key},
                timeout=10,
            )
            if resp.ok:
                return jsonify(resp.json())
            return jsonify(error=f"ElevenLabs returned {resp.status_code}"), 502
        except requests.RequestException as e:
            return jsonify(error=str(e)), 502

    @app.route("/api/ai/ask", methods=["GET", "POST"])
    def api_ai_ask():
        data = request.get_json(silent=True) or {}
        query = (request.args.get("q") or request.args.get("query") or data.get("query") or data.get("q") or "").strip()
        lang = request.args.get("lang") or data.get("lang") or "en"
        token = request.args.get("token") or data.get("token")

        if not query:
            return jsonify(error="query_required"), 400

        patient_ctx = None
        if token:
            p = Patient.query.filter_by(token=token).first()
            if p:
                bed_obj = Bed.query.filter_by(patient_id=p.id).first()
                patient_ctx = {
                    "name": p.first_name,
                    "status": p.status,
                    "status_label": STATUSES_HI[p.status] if lang == "hi" else STATUSES[p.status],
                    "dept": p.dept or "Emergency",
                    "bed": bed_obj.code if bed_obj else None
                }

        answer_text = ai_assistant.answer_question(query, lang=lang, patient_context=patient_ctx)
        has_elevenlabs = voice.enabled()
        audio_url = f"/api/tts/speak?text={requests.utils.quote(answer_text)}&lang={lang}"

        return jsonify(
            query=query,
            answer=answer_text,
            lang=lang,
            audio_url=audio_url,
            voice_engine="elevenlabs" if has_elevenlabs else "speech_synthesis",
            elevenlabs_active=has_elevenlabs
        )

    # ================================================================ STAFF AUTH
    @app.route("/staff/login", methods=["GET", "POST"])
    def staff_login():
        if request.method == "GET":
            if current_staff():
                return redirect(url_for("staff_overview"))
            tab = request.args.get("tab", "login")
            return render_template("staff_login.html", error=None, success=None, tab=tab)
        u = clean(request.form.get("username"), 40).lower()
        key = f"login:{request.remote_addr}:{u}"
        if recent(key, 600) >= 10:
            return render_template("staff_login.html", error="Too many attempts. Try again in 10 minutes.", tab="login"), 429
        s = Staff.query.filter_by(username=u).first()
        ok = check_password_hash(s.password_hash if s else app.config["DUMMY_HASH"], request.form.get("password", ""))
        if not (s and ok):
            hit(key, 600)
            audit(u or "unknown", "", "login_failed", None, "Failed sign-in attempt")
            db.session.commit()
            return render_template("staff_login.html", error="Incorrect username or password.", tab="login"), 401
        session.clear()
        session.permanent = True
        session["staff_id"] = s.id
        audit(s.display_name, s.role, "login", None, "Signed in")
        db.session.commit()
        return redirect(url_for("staff_overview"))

    @app.route("/staff/register", methods=["GET", "POST"])
    def staff_register():
        if request.method == "GET":
            if current_staff():
                return redirect(url_for("staff_overview"))
            return render_template("staff_login.html", error=None, success=None, tab="register")
        display_name = clean(request.form.get("display_name"), 80)
        u = clean(request.form.get("username"), 40).lower()
        role = clean(request.form.get("role"), 20).lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not display_name or len(display_name) < 2:
            return render_template("staff_login.html", error="Please enter your full name and title.", tab="register"), 422
        if not u or not re.match(r"^[a-zA-Z0-9._-]{3,40}$", u):
            return render_template("staff_login.html", error="Username must be 3-40 characters (letters, numbers, dots, dashes).", tab="register"), 422
        if role not in ("clinician", "nurse"):
            return render_template("staff_login.html", error="Please select a valid staff role (Doctor / Clinician or Nurse).", tab="register"), 422
        if not password or len(password) < 6:
            return render_template("staff_login.html", error="Password must be at least 6 characters.", tab="register"), 422
        if password != confirm:
            return render_template("staff_login.html", error="Passwords do not match.", tab="register"), 422

        if Staff.query.filter_by(username=u).first():
            return render_template("staff_login.html", error="A staff account with this username already exists.", tab="register"), 409

        new_staff = Staff(
            username=u,
            display_name=display_name,
            role=role,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_staff)
        db.session.flush()
        audit(display_name, role, "register", None, f"Staff account created ({role})")
        db.session.commit()

        session.clear()
        session.permanent = True
        session["staff_id"] = new_staff.id
        return redirect(url_for("staff_overview"))

    @app.post("/staff/logout")
    def staff_logout():
        s = current_staff()
        if s:
            audit(s.display_name, s.role, "logout", None, "Signed out")
            db.session.commit()
        session.clear()
        return redirect(url_for("staff_login"))

    app.config["DUMMY_HASH"] = generate_password_hash(secrets.token_hex(8))

    # ================================================================ STAFF PAGES
    for path, endpoint, tpl in (("/staff", "staff_overview", "staff_overview.html"),
                                ("/staff/patients", "staff_patients", "staff_patients.html"),
                                ("/staff/resources", "staff_resources", "staff_resources.html"),
                                ("/staff/audit", "staff_audit", "staff_audit.html")):
        app.add_url_rule(path, endpoint, staff_required()(lambda t=tpl: render_template(t)))

    # ================================================================ STAFF API
    @app.get("/staff/api/overview")
    @staff_required(api=True)
    def api_overview():
        ps = Patient.query.all()
        act = [p for p in ps if p.active]
        by_status = [sum(p.status == i for p in ps) for i in range(len(STATUSES))]
        by_pri = {k: sum(p.priority == k for p in act) for k in PRIORITIES}
        waits = [(utcnow() - p.created_at).total_seconds() / 60 for p in ps if p.status in (0, 1)]
        attention = []
        for p in sorted(act, key=lambda x: x.created_at):
            reasons = []
            if p.priority == "Not set":
                reasons.append("Priority not set")
            reasons += [m["label"] for m in missing_info(p)]
            if reasons:
                attention.append({"code": p.code, "name": p.name, "status": p.status,
                                  "arrived_at": iso(p.created_at), "reasons": reasons})
        beds = Bed.query.all()
        wards = [{"ward": w, "total": sum(b.ward == w and not b.out_of_service for b in beds),
                  "free": sum(b.ward == w and not b.out_of_service and not b.patient_id for b in beds),
                  "out": sum(b.ward == w and b.out_of_service for b in beds)} for w in WARDS]
        return jsonify(
            stats={"total": len(ps), "waiting": by_status[0] + by_status[1],
                   "in_care": by_status[2] + by_status[3],
                   "awaiting_priority": sum(p.priority == "Not set" for p in act),
                   "missing": sum(bool(missing_info(p)) for p in act),
                   "longest_wait_min": int(max(waits)) if waits else 0},
            by_status={"labels": STATUSES, "values": by_status},
            by_priority={"labels": PRIORITIES, "values": [by_pri[k] for k in PRIORITIES]},
            wards=wards,
            resources=[{"name": r.name, "icon": r.icon, "total": r.total, "available": r.available}
                       for r in Resource.query.order_by(Resource.id)],
            attention=attention[:8])

    @app.get("/staff/api/patients")
    @staff_required(api=True)
    def api_patients():
        qs = Patient.query
        q = clean(request.args.get("q"), 60)
        if q.upper().startswith("EC360:"):
            q = q[6:]
        if q:
            qs = qs.filter(db.or_(Patient.name.icontains(q, autoescape=True),
                                  Patient.code.icontains(q, autoescape=True),
                                  Patient.phone.icontains(q, autoescape=True)))
        st = request.args.get("status", "")
        if st.isdigit():
            qs = qs.filter(Patient.status == int(st))
        if request.args.get("priority") in PRIORITIES:
            qs = qs.filter(Patient.priority == request.args["priority"])
        rows = qs.all()
        # Active patients first in arrival order (first come, first listed); closed cases after.
        rows.sort(key=lambda p: (not p.active, p.created_at if p.active else -p.created_at.timestamp()))
        return jsonify(patients=[row(p) for p in rows])

    def get_patient(code):
        p = Patient.query.filter_by(code=code).first()
        if not p:
            abort(404)
        return p

    @app.get("/staff/api/patients/<code>")
    @staff_required(api=True)
    def api_patient(code):
        p = get_patient(code)
        a, r = me()
        if recent(f"view:{a}:{code}", 300) == 0:  # one audit line per 5 minutes per record
            audit(a, r, "view", code, "Opened patient record")
            db.session.commit()
        hit(f"view:{a}:{code}", 300)
        return jsonify(detail(p))

    def release_bed(p):
        if p.bed:
            code, p.bed.patient_id = p.bed.code, None
            db.session.flush()
            return code

    def assign_bed(p, bed):
        if bed.out_of_service:
            return "That bed is out of service."
        if bed.patient_id and bed.patient_id != p.id:
            return "That bed is already occupied."
        release_bed(p)
        bed.patient_id = p.id
        db.session.flush()

    @app.post("/staff/api/patients/<code>/update")
    @staff_required(api=True)
    def api_update(code):
        p, d, s = get_patient(code), request.get_json(silent=True) or {}, current_staff()
        changes = []

        def bad(msg, status=400):
            db.session.rollback()
            return jsonify(error=msg), status

        if "priority" in d and d["priority"] != p.priority:
            if d["priority"] not in PRIORITIES:
                return bad("Invalid priority.")
            if s.role != "clinician":
                return bad("Only a clinician can assign clinical priority.", 403)
            changes.append(f"priority {p.priority} → {d['priority']}")
            p.priority, p.priority_by, p.priority_at = d["priority"], s.display_name, utcnow()
        if "status" in d and int(d["status"]) != p.status:
            new = int(d["status"])
            if not 0 <= new < len(STATUSES):
                return bad("Invalid status.")
            changes.append(f"status {STATUSES[p.status]} → {STATUSES[new]}")
            p.status = new
            db.session.add(StatusEvent(patient_id=p.id, status=new, by=s.display_name))
            if new > ACTIVE_MAX:
                freed = release_bed(p)
                if freed:
                    changes.append(f"bed {freed} released")
        if "dept" in d and d["dept"] != p.dept:
            if d["dept"] not in DEPARTMENTS:
                return bad("Invalid department.")
            changes.append(f"department {p.dept} → {d['dept']}")
            p.dept = d["dept"]
        if "bed" in d and (d["bed"] or "") != (p.bed.code if p.bed else ""):
            if d["bed"]:
                b = Bed.query.filter_by(code=d["bed"]).first()
                if not b:
                    return bad("Unknown bed.")
                err = assign_bed(p, b)
                if err:
                    return bad(err, 409)
                changes.append(f"bed {b.code} assigned")
            else:
                changes.append(f"bed {release_bed(p)} released")
        v = d.get("vitals")
        if isinstance(v, dict):
            try:
                new = {
                    "hr": int(v["hr"]) if str(v.get("hr", "")).strip() else None,
                    "bp": str(v.get("bp", "")).strip(),
                    "spo2": int(v["spo2"]) if str(v.get("spo2", "")).strip() else None,
                    "temp": round(float(v["temp"]), 1) if str(v.get("temp", "")).strip() else None}
            except (ValueError, TypeError):
                return bad("Vitals must be numbers.")
            if (new["hr"] is not None and not 20 <= new["hr"] <= 250) or \
               (new["spo2"] is not None and not 50 <= new["spo2"] <= 100) or \
               (new["temp"] is not None and not 85 <= new["temp"] <= 115) or \
               (new["bp"] and not BP_RE.match(new["bp"])):
                return bad("Vitals out of range. BP format is 120/80, temperature in °F.")
            if (new["hr"], new["bp"], new["spo2"], new["temp"]) != (p.hr, p.bp, p.spo2, p.temp):
                p.hr, p.bp, p.spo2, p.temp, p.vitals_at = new["hr"], new["bp"], new["spo2"], new["temp"], utcnow()
                changes.append("vitals updated")
        if changes:
            p.updated_at = utcnow()
            audit(s.display_name, s.role, "update", p.code, "; ".join(changes))
            db.session.commit()
        return jsonify(ok=True, changed=bool(changes), patient=detail(p))

    @app.get("/staff/api/patients/<code>/handover")
    @staff_required(api=True)
    def api_handover(code):
        p = get_patient(code)
        a, r = me()
        audit(a, r, "handover", code, "Generated handover snapshot")
        db.session.commit()
        d = detail(p)
        d.update(generated_at=iso(utcnow()), generated_by=a)
        return jsonify(d)

    @app.get("/staff/api/patients/<code>/report")
    @staff_required(api=True)
    def api_report(code):
        p = get_patient(code)
        if not p.report_data:
            abort(404)
        a, r = me()
        audit(a, r, "report", code, "Opened uploaded report")
        db.session.commit()
        return Response(p.report_data, mimetype=p.report_mime, headers={
            "Content-Disposition": f'attachment; filename="{secure_filename(p.report_name or "report")}"'})

    @app.get("/staff/api/patients/<code>/qr.png")
    @staff_required(api=True)
    def qr_staff(code):
        return qr_response("EC360:" + get_patient(code).code)

    # ---- beds & resources
    def resources_payload():
        beds = Bed.query.order_by(Bed.ward, Bed.code).all()
        order = {w: i for i, w in enumerate(WARDS)}
        beds.sort(key=lambda b: (order.get(b.ward, 9), b.code))
        return {
            "beds": [{"id": b.id, "code": b.code, "ward": b.ward, "out_of_service": b.out_of_service,
                      "patient": {"code": b.patient.code, "first_name": b.patient.first_name}
                      if b.patient else None} for b in beds],
            "resources": [{"id": r.id, "name": r.name, "icon": r.icon, "total": r.total,
                           "available": r.available} for r in Resource.query.order_by(Resource.id)],
            "unassigned": [{"code": p.code, "name": p.name} for p in Patient.query.order_by(Patient.created_at)
                           if p.active and not p.bed]}

    @app.get("/staff/api/resources")
    @staff_required(api=True)
    def api_resources():
        return jsonify(resources_payload())

    @app.post("/staff/api/beds/<int:bid>")
    @staff_required(api=True)
    def api_bed(bid):
        b = db.session.get(Bed, bid) or abort(404)
        d, (a, r) = request.get_json(silent=True) or {}, me()
        act = d.get("action")
        if act == "assign":
            p = Patient.query.filter_by(code=d.get("code")).first()
            if not p or not p.active:
                return jsonify(error="Choose an active patient."), 400
            err = assign_bed(p, b)
            if err:
                return jsonify(error=err), 409
            audit(a, r, "bed", p.code, f"Bed {b.code} assigned")
        elif act == "release":
            if b.patient:
                code = b.patient.code
                b.patient_id = None
                audit(a, r, "bed", code, f"Bed {b.code} released")
        elif act == "service":
            if b.patient_id:
                return jsonify(error="Release the bed before taking it out of service."), 409
            b.out_of_service = bool(d.get("out"))
            audit(a, r, "bed", None, f"Bed {b.code} marked {'out of service' if b.out_of_service else 'in service'}")
        else:
            return jsonify(error="Unknown action."), 400
        db.session.commit()
        return jsonify(resources_payload())

    @app.post("/staff/api/resources/<int:rid>")
    @staff_required(api=True)
    def api_resource(rid):
        res = db.session.get(Resource, rid) or abort(404)
        d, (a, r) = request.get_json(silent=True) or {}, me()
        try:
            total = int(d.get("total", res.total))
            avail = int(d.get("available", res.available))
        except (TypeError, ValueError):
            return jsonify(error="Enter whole numbers."), 400
        if not (0 <= avail <= total <= 999):
            return jsonify(error="Available must be between 0 and the total."), 400
        if (total, avail) != (res.total, res.available):
            audit(a, r, "resource", None, f"{res.name}: {res.available}/{res.total} → {avail}/{total}")
            res.total, res.available = total, avail
            db.session.commit()
        return jsonify(resources_payload())

    @app.get("/staff/api/audit")
    @staff_required(api=True)
    def api_audit():
        qs = Audit.query
        act = request.args.get("action", "")
        if act:
            qs = qs.filter(Audit.action == act)
        q = clean(request.args.get("q"), 60)
        if q:
            qs = qs.filter(db.or_(Audit.patient_code.icontains(q, autoescape=True),
                                  Audit.actor.icontains(q, autoescape=True),
                                  Audit.detail.icontains(q, autoescape=True)))
        rows = qs.order_by(Audit.at.desc(), Audit.id.desc()).limit(300).all()
        return jsonify(entries=[{"at": iso(x.at), "actor": x.actor, "role": x.role, "action": x.action,
                                 "patient": x.patient_code, "detail": x.detail} for x in rows])

    @app.errorhandler(404)
    def nf(e):
        if request.path.startswith(("/api", "/staff/api")):
            return jsonify(error="not_found"), 404
        return render_template("error.html", code=404, msg="We couldn't find that page."), 404

    @app.errorhandler(413)
    def too_big(e):
        return jsonify(errors={"report": "file_size"}), 413

    init_db(app)
    return app


# ---------------------------------------------------------------- seeding
def init_db(app):
    with app.app_context():
        db.create_all()
        try:
            seed_staff()
            seed_beds()
            if os.getenv("SEED_DEMO_PATIENTS", "true").lower() != "false" and not Patient.query.first():
                seed_patients()
            db.session.commit()
        except IntegrityError:  # another worker seeded first
            db.session.rollback()


def seed_staff():
    if Staff.query.first():
        return
    pw = os.getenv("STAFF_PASSWORD")
    if not pw:
        pw = secrets.token_urlsafe(10)
        print(f"[EmergencyCare360] No STAFF_PASSWORD set. Generated demo password: {pw}", flush=True)
    for u, n, r in (("dr.demo", "Dr. Demo", "clinician"), ("nurse.demo", "Nurse Demo", "nurse")):
        db.session.add(Staff(username=u, display_name=n, role=r, password_hash=generate_password_hash(pw)))


def seed_beds():
    if Bed.query.first():
        return
    for ward, prefix, n in (("Emergency", "ER", 12), ("ICU", "ICU", 6), ("Ward", "WD", 12)):
        for i in range(1, n + 1):
            db.session.add(Bed(code=f"{prefix}-{i:02d}", ward=ward))
    for name, icon, total, avail in (("Ventilators", "wind", 8, 4), ("Staff on duty", "people", 20, 14)):
        db.session.add(Resource(name=name, icon=icon, total=total, available=avail))


def seed_patients():
    """Fictional demo patients so the dashboard is not empty on first run."""
    from datetime import timedelta
    now = utcnow()
    demo = [
        ("Rohan Mehta", 34, "98100 00011", "98100 00012", "Chest tightness and shortness of breath since morning",
         "Hypertension", "None known", (104, "146/92", 96, 98.4), 1, "Urgent", "Cardiology", True, None, 140, "ECG_2025.pdf"),
        ("Sunita Rao", 61, "98100 00021", "", "Fall at home, pain in left hip",
         "Type 2 diabetes", "Penicillin", (88, "130/84", 98, 98.1), 2, "Urgent", "Orthopedics", False, "ER-03", 110, None),
        ("Imran Khan", 8, "98100 00031", "98100 00032", "High fever for two days, vomiting",
         "", "", (118, "", 97, 101.8), 0, "Not set", "Pediatrics", True, None, 85, None),
        ("Meena Joshi", 47, "98100 00041", "98100 00042", "Deep cut on forearm",
         "None", "Latex", (82, "122/80", 99, 98.2), 3, "Standard", "Surgery", True, "ER-04", 200, None),
        ("Arjun Sethi", 29, "98100 00051", "98100 00052", "Severe headache, sensitivity to light",
         "Migraine", "None known", (76, "118/76", 99, 98.0), 4, "Standard", "Neurology", False, None, 260, "MRI_2024.pdf"),
        ("Kavita Nair", 52, "98100 00061", "98100 00062", "Abdominal pain",
         "Gallstones", "None known", (80, "124/82", 98, 98.6), 5, "Standard", "General", True, None, 330, None)]
    for (name, age, ph, kin, sym, hist, al, v, st, pri, dept, cons, bed, mins, rep) in demo:
        t0 = now - timedelta(minutes=mins)
        p = Patient(name=name, age=age, phone=ph, kin_phone=kin, symptoms=sym, history=hist, allergies=al,
                    hr=v[0], bp=v[1], spo2=v[2], temp=v[3], vitals_at=t0, status=st, priority=pri,
                    priority_by="Dr. Demo" if pri != "Not set" else None,
                    priority_at=t0 if pri != "Not set" else None, dept=dept, consent=cons,
                    report_name=rep, report_mime="application/pdf" if rep else None,
                    report_data=b"%PDF-1.4 fictional demo report" if rep else None,
                    created_at=t0, updated_at=t0 + timedelta(minutes=min(mins, 20) // 2))
        db.session.add(p)
        db.session.flush()
        p.code = f"EC-{1000 + p.id}"
        for i in range(st + 1):
            db.session.add(StatusEvent(patient_id=p.id, status=i, at=t0 + timedelta(minutes=i * 12),
                                       by="System" if i == 0 else "Nurse Demo"))
        if bed:
            Bed.query.filter_by(code=bed).first().patient_id = p.id
        db.session.add(Audit(at=t0, actor="Patient", role="patient", action="register",
                             patient_code=p.code, detail="Emergency registration submitted"))


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
