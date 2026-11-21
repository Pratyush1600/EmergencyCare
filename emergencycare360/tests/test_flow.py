import io, re, os
import pytest
from unittest import mock
from app import create_app
from models import db, AudioCache, Audit

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("STAFF_PASSWORD", "test-pass-1")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/t.db"})


def csrf(c, path="/"):
    html = c.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" content="([^"]+)"', html).group(1)


def login(c, user="dr.demo", pw="test-pass-1"):
    return c.post("/staff/login", data={"username": user, "password": pw, "csrf_token": csrf(c, "/staff/login")})


def register(c, **kw):
    d = dict(name="Test Patient", age="40", phone="98100 12345", kin_phone="", symptoms="Dizziness", history="", allergies="", consent="1", lang="en")
    d.update(kw)
    return c.post("/api/register", data=d, headers={"X-CSRF-Token": csrf(c)}, content_type="multipart/form-data")


def test_health(app):
    r = app.test_client().get("/health")
    assert r.status_code == 200 and r.json["database"] == "up"


def test_full_flow(app):
    pc, sc = app.test_client(), app.test_client()
    r = register(pc, report=(io.BytesIO(PNG), "scan.png"))
    assert r.status_code == 201
    code, token = r.json["code"], r.json["token"]
    # patient view: priority never exposed, missing info flagged
    t = pc.get(f"/api/track/{token}").json
    assert t["status"] == 0 and "priority" not in t and {m["key"] for m in t["missing"]} == {"history", "allergies", "kin_phone"}
    assert pc.get(f"/qr/{token}.png").data.startswith(b"\x89PNG")
    # staff must log in
    assert sc.get("/staff/api/patients").status_code == 401
    assert login(sc, pw="wrong").status_code == 401
    assert login(sc).status_code == 302
    lst = sc.get("/staff/api/patients?q=Test").json["patients"]
    assert lst[0]["code"] == code
    tok = csrf(sc, "/staff")
    H = {"X-CSRF-Token": tok}
    # nurse cannot set priority, clinician can
    n = app.test_client(); login(n, "nurse.demo")
    nt = csrf(n, "/staff")
    assert n.post(f"/staff/api/patients/{code}/update", json={"priority": "Urgent"}, headers={"X-CSRF-Token": nt}).status_code == 403
    u = sc.post(f"/staff/api/patients/{code}/update", headers=H, json={"status": 2, "priority": "Urgent", "dept": "General", "bed": "ER-01",
                "vitals": {"hr": "90", "bp": "120/80", "spo2": "98", "temp": "98.6"}})
    assert u.status_code == 200 and u.json["patient"]["bed"] == "ER-01"
    # same record visible to patient
    t = pc.get(f"/api/track/{token}").json
    assert t["status"] == 2 and t["bed"] == "ER-01" and len(t["timeline"]) == 2
    # bed conflict and vitals validation
    other = register(app.test_client()).json["code"]
    assert sc.post(f"/staff/api/patients/{other}/update", headers=H, json={"bed": "ER-01"}).status_code == 409
    assert sc.post(f"/staff/api/patients/{code}/update", headers=H, json={"vitals": {"bp": "abc"}}).status_code == 400
    # discharge releases the bed
    sc.post(f"/staff/api/patients/{code}/update", headers=H, json={"status": 5})
    assert next(b for b in sc.get("/staff/api/resources").json["beds"] if b["code"] == "ER-01")["patient"] is None
    # handover, report, overview, audit
    assert sc.get(f"/staff/api/patients/{code}/handover").json["code"] == code
    assert sc.get(f"/staff/api/patients/{code}/report").data == PNG
    assert sc.get("/staff/api/overview").json["stats"]["total"] >= 8
    acts = {e["action"] for e in sc.get("/staff/api/audit").json["entries"]}
    assert {"register", "update", "handover", "login", "login_failed"} <= acts
    # csrf enforced
    assert sc.post(f"/staff/api/patients/{code}/update", json={"status": 1}).status_code == 400


def test_consent_family(app):
    c = app.test_client()
    r = register(c, consent="0").json
    fam = c.get(f"/api/track/{r['token']}").json
    assert fam["family_url"] is None
    ft = Audit  # silence linter
    from models import Patient
    with app.app_context():
        ftoken = Patient.query.filter_by(code=r["code"]).first().family_token
    assert c.get(f"/api/family/{ftoken}").status_code == 404
    c.post(f"/api/track/{r['token']}/details", json={"consent": True}, headers={"X-CSRF-Token": csrf(c)})
    f = c.get(f"/api/family/{ftoken}").json
    assert set(f) == {"first_name", "status", "status_label", "status_label_hi", "updated_at"}


def test_validation_and_lookup(app):
    c = app.test_client()
    assert register(c, name="", age="200", phone="x", symptoms="").status_code == 422
    assert register(c, report=(io.BytesIO(b"MZ not a pdf"), "evil.pdf")).status_code == 422
    r = register(c).json
    assert c.post("/api/lookup", json={"code": r["code"], "phone": "9810012345"}, headers={"X-CSRF-Token": csrf(c)}).status_code == 200
    assert c.post("/api/lookup", json={"code": r["code"], "phone": "0000000000"}, headers={"X-CSRF-Token": csrf(c)}).status_code == 404


def test_tts_privacy_and_cache(app):
    c = app.test_client()
    r = register(c, name="Secret Name").json
    calls = []

    def fake(url, **kw):
        calls.append(kw["json"]["text"])
        return mock.Mock(status_code=200, content=b"ID3fake-mp3")
    with mock.patch("voice.requests.post", fake):
        for _ in range(3):
            assert c.get("/api/tts?kind=status&state=2&lang=hi").data == b"ID3fake-mp3"
        assert c.get("/api/tts?kind=registered&lang=en").status_code == 200
    assert len(calls) == 2  # second and third hit the cache
    assert all("Secret" not in x and r["code"] not in x for x in calls)
    assert c.get("/api/tts?kind=status&state=9&lang=en").status_code == 400
    assert c.get("/api/tts?kind=custom&text=hello").status_code == 400
    with app.app_context():
        assert AudioCache.query.count() == 2


def test_tts_disabled_without_key(app, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    assert app.test_client().get("/api/tts?kind=status&state=1&lang=en").status_code == 503


def test_tts_speak_endpoint(app):
    c = app.test_client()
    assert c.get("/api/tts/speak").status_code == 400
    with mock.patch("voice.requests.post", return_value=mock.Mock(status_code=200, content=b"ID3human-voice")):
        res = c.get("/api/tts/speak?text=Emergency+instruction&lang=en")
        assert res.status_code == 200 and res.data == b"ID3human-voice"


def test_ai_ask_endpoint(app):
    c = app.test_client()
    assert c.post("/api/ai/ask", json={}).status_code == 400
    res = c.post("/api/ai/ask", json={"query": "How does priority triage work?", "lang": "en"})
    assert res.status_code == 200
    assert "priority" in res.json["answer"].lower()
    assert "audio_url" in res.json

    # Test health query and cure suggestions
    res_fever = c.post("/api/ai/ask", json={"query": "What is the cure for fever and body temperature?", "lang": "en"})
    assert res_fever.status_code == 200
    assert "fever" in res_fever.json["answer"].lower()
    assert "paracetamol" in res_fever.json["answer"].lower()

    # Test Hindi health remedy
    res_hi = c.post("/api/ai/ask", json={"query": "सिरदर्द का घरेलू उपचार क्या है?", "lang": "hi"})
    assert res_hi.status_code == 200
    assert "सिरदर्द" in res_hi.json["answer"]

    # Test random health issue cure inquiry
    res_random = c.post("/api/ai/ask", json={"query": "I have an unexplained knee pain and swelling, suggest cure", "lang": "en"})
    assert res_random.status_code == 200
    assert any(w in res_random.json["answer"].lower() for w in ["sprain", "rest", "swelling", "ice", "guidance"])


def test_staff_register_and_login(app):
    c = app.test_client()
    t = csrf(c, "/staff/login")
    # password mismatch
    r_bad = c.post("/staff/register", data={"display_name": "Dr. Sarah", "username": "dr.sarah", "role": "clinician",
                                            "password": "pass1", "confirm_password": "pass2", "csrf_token": t})
    assert r_bad.status_code == 422
    # successful registration
    r_ok = c.post("/staff/register", data={"display_name": "Dr. Sarah", "username": "dr.sarah", "role": "clinician",
                                           "password": "password123", "confirm_password": "password123", "csrf_token": t})
    assert r_ok.status_code == 302 and "/staff" in r_ok.location
    # verify dashboard access
    assert "Dr. Sarah" in c.get("/staff").data.decode()



