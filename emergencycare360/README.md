# EmergencyCare 360

Emergency patient coordination for HackForge 2K26 (team HackTitans). Flask + SQLAlchemy (TiDB/MySQL, SQLite locally), Bootstrap 5, Chart.js, Python `qrcode`, ElevenLabs voice.
The software only organises information. **Clinical priority and status are set by authenticated staff.** All demo patients are fictional.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env        # set SECRET_KEY, STAFF_PASSWORD (and ELEVENLABS_API_KEY for voice)
python app.py               # http://localhost:5000
python -m pytest -q tests
```
Staff accounts (created on first start, password = `STAFF_PASSWORD`): `dr.demo` (clinician: can set priority) and `nurse.demo` (nurse: status, vitals, beds; cannot set priority).
If `STAFF_PASSWORD` is unset a random one is printed once in the server log.

## Pages
Patient: `/` register · `/track` find by ID + phone · `/track/<token>` live status, QR, timeline, Listen · `/family/<token>` status only, consent required.
Staff: `/staff/login` · `/staff` overview · `/staff/patients` (+ Handover snapshot, QR scan) · `/staff/resources` · `/staff/audit`. Health: `/health`.

## Database
`DATABASE_URL` empty → SQLite. TiDB Cloud: `mysql://USER:PASSWORD@HOST:4000/DB` (TLS on by default; `DB_SSL=false` for local MySQL). Tables are created on start. `SEED_DEMO_PATIENTS=false` starts empty.

## Voice (ElevenLabs)
Key lives only in the `ELEVENLABS_API_KEY` env var on the server. The browser calls `/api/tts?kind=status&state=2&lang=hi`; the server maps that to one of 14 fixed sentences (never patient data), generates it once, and stores the MP3 in the database. Without a key, the Listen button falls back to the device's own voice.

## Deploy on Render
Push to GitHub → Render → New → Blueprint (uses `render.yaml`). Set `DATABASE_URL`, `STAFF_PASSWORD`, `ELEVENLABS_API_KEY`. Render's free disk is ephemeral, so use TiDB for `DATABASE_URL`; without it data is lost on restart.

`backup/index_original_prototype.html` is the original single-file prototype.
