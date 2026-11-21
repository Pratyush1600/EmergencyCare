# 🏥 EmergencyCare 360

[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-000000.svg?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3.svg?style=flat&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local_DB-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![TiDB](https://img.shields.io/badge/TiDB_Cloud-MySQL_Compatible-E40046.svg?style=flat&logo=mysql&logoColor=white)](https://tidbcloud.com/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Multilingual_Voice-FF7700.svg?style=flat)](https://elevenlabs.io/)

> **Real-time emergency patient coordination, digital triage workflow, live tracking, and multilingual AI voice assistance.**  
> Built for **HackForge 2K26** by **Team HackTitans**.

---

## 📋 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [Project Architecture](#-project-architecture)
- [Project Structure](#-project-structure)
- [Quick Start (Local Development)](#-quick-start-local-development)
- [Default Demo Credentials](#-default-demo-credentials)
- [Environment Variables](#-environment-variables)
- [Running Automated Tests](#-running-automated-tests)
- [Deployment Guide (Render + TiDB Cloud)](#-deployment-guide-render--tidb-cloud)
- [Privacy, Ethics & Medical Safety](#-privacy-ethics--medical-safety)
- [License & Acknowledgments](#-license--acknowledgments)

---

## 🌟 Overview

Emergency departments often suffer from communication bottlenecks, overcrowding, and patient anxiety due to opaque waiting processes. **EmergencyCare 360** transforms hospital emergency coordination into an efficient, transparent, and empathetic digital experience.

It connects **patients**, **families**, and **hospital staff** into one synchronized workflow with real-time updates, QR code identification, automated status timelines, bed management, and multilingual voice capabilities.

---

## ✨ Key Features

### 1. 📲 Patient Self-Registration & Digital Pass
- Fast, accessible self-service intake on any phone or kiosk (`/`).
- Captures primary symptoms, medical history, allergies, emergency contacts, and preferred language (**English & Hindi**).
- Optional medical report file upload (PDF, PNG, JPG up to 3MB).
- Generates an instant **Digital QR Pass** and unique tracking tokens.

### 2. 📍 Real-Time Live Patient Tracker (`/track/<token>`)
- Live progress indicator tracking 6 workflow stages:
  1. *Registered* ➡️ 2. *Waiting for assessment* ➡️ 3. *Under assessment* ➡️ 4. *Treatment in progress* ➡️ 5. *Referred* ➡️ 6. *Discharged*
- Dynamic status timeline with timestamps and department allocation.
- Live vital signs monitoring (Heart Rate, Blood Pressure, SpO2, Temperature).
- **Listen Button**: Multilingual audio announcements of current status.

### 3. 👨‍👩‍👧 Kin & Family Portal (`/family/<token>`)
- Consent-gated portal enabling loved ones to track patient progress remotely.
- Displays high-level status updates while protecting sensitive clinical records and vitals.

### 4. 🎙️ Multilingual Voice Announcements (ElevenLabs TTS)
- Status announcements synthesized in English and Hindi (`/api/tts`).
- **Privacy-by-Design**: Only pre-approved status sentence templates are sent to the TTS API—**no patient names, symptoms, or personal data leave the server**.
- **Audio Caching**: Audio clips are stored in the database cache to minimize API calls and latency.
- Graceful client-side fallback to the device's native SpeechSynthesis API when offline or without an API key.

### 5. 🤖 AI Voice & Health Knowledge Assistant
- Built-in conversational assistant for immediate guidance.
- **Emergency Red Flag Detection**: Flags critical symptoms (e.g. chest pain, heavy bleeding, stroke symptoms, respiratory distress) and prompts emergency intervention.
- **First-Aid & Cure Database**: Practical guidance for non-critical conditions (fever, migraine, minor burns, sprains, acidity) in both English and Hindi.
- Context-aware answers explaining emergency department processes, wait times, and triage.

### 6. 🩺 Hospital Staff Dashboard (`/staff`)
- **Role-Based Access Control (RBAC)**:
  - **Clinicians (`dr.demo`)**: Triage prioritization (*Immediate / Urgent / Standard*), status management, vitals, and department referral.
  - **Nurses (`nurse.demo`)**: Status updates, vital signs recording, bed assignments, and handover notes.
- **Live ER Metrics**: Real-time charts of active patient count, department load, and bed occupancy.
- **Bed & Resource Management (`/staff/resources`)**: Ward tracking across *Emergency*, *ICU*, and *General Wards*, with out-of-service flagging.
- **Immutable Clinical Audit Trail (`/staff/audit`)**: Logs all triage changes, status updates, and vital entries with timestamps and staff IDs.

---

## 🏗️ Project Architecture

```
                      ┌─────────────────────────────────────────┐
                      │          Patients & Relatives           │
                      │   (Web Kiosk / Mobile / QR Scanner)     │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           Flask Application Layer                             │
│                                                                               │
│   ┌────────────────────┐   ┌────────────────────┐   ┌─────────────────────┐   │
│   │   Patient Portal   │   │  Staff Dashboard   │   │  AI Voice Assistant │   │
│   │  /track & /family  │   │  /staff & /audit   │   │    ai_assistant.py  │   │
│   └─────────┬──────────┘   └─────────┬──────────┘   └──────────┬──────────┘   │
│             │                        │                         │              │
│             └────────────────────────┼─────────────────────────┘              │
│                                      │                                        │
│                        ┌─────────────┴─────────────┐                          │
│                        │    SQLAlchemy ORM Layer   │                          │
│                        └─────────────┬─────────────┘                          │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────┐                             ┌────────────────────────┐
│  Local: SQLite        │                             │  Production: TiDB      │
│  (emergencycare.db)   │                             │  Cloud / MySQL (TLS)   │
└───────────────────────┘                             └────────────────────────┘
```

---

## 📁 Project Structure

```
emergencycare36/
├── emergencycare360/
│   ├── instance/               # Local SQLite database storage
│   ├── static/
│   │   ├── css/                # Custom CSS styling
│   │   └── js/                 # Patient tracking, QR scanning, voice scripts
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html           # Main layout with AI Voice Modal
│   │   ├── register.html       # Patient registration form
│   │   ├── track.html          # Real-time patient tracker
│   │   ├── family.html         # Consent-gated kin status page
│   │   ├── staff_login.html    # Staff authentication
│   │   ├── staff_overview.html # Hospital ER metrics & charts
│   │   ├── staff_patients.html # Triage queue & patient management
│   │   ├── staff_resources.html# Bed & Ward resource management
│   │   └── staff_audit.html    # Immutable audit trail
│   ├── tests/
│   │   └── test_flow.py        # Automated test suite (Pytest)
│   ├── .env                    # Local environment variables
│   ├── .env.example            # Example configuration template
│   ├── ai_assistant.py         # AI Voice & Health Assistant engine
│   ├── app.py                  # Core Flask application & routes
│   ├── models.py               # SQLAlchemy database models
│   ├── voice.py                # ElevenLabs TTS integration & caching
│   ├── wsgi.py                 # WSGI entry point for Gunicorn
│   ├── render.yaml             # Render infrastructure-as-code blueprint
│   └── requirements.txt        # Python package dependencies
├── .vscode/
│   └── launch.json             # VS Code debugging profiles
├── run.bat                     # Windows CMD quick-launch script
├── run.ps1                     # Windows PowerShell quick-launch script
└── README.md                   # This documentation
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- **Python 3.11+** installed ([python.org](https://www.python.org/))
- **Git** installed

### 1. Clone & Open Project
```bash
git clone <your-repository-url>
cd emergencycare36
```

### 2. Automated Launch (Windows)

You can launch immediately using the included scripts:

* **PowerShell**:
  ```powershell
  .\run.ps1
  ```
* **Command Prompt (CMD)**:
  ```cmd
  run.bat
  ```

---

### 3. Manual Setup (Any OS: Windows / macOS / Linux)

1. **Create and activate a virtual environment:**
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate on Windows PowerShell:
   .\.venv\Scripts\Activate.ps1

   # Activate on Windows CMD:
   .\.venv\Scripts\activate.bat

   # Activate on macOS / Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r emergencycare360/requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cd emergencycare360
   cp .env.example .env
   ```

4. **Run the Flask server:**
   ```bash
   python app.py
   ```

5. **Open in Browser:**
   👉 Visit: **`http://localhost:5000`**

---

### 4. Running with VS Code

Open the project folder in VS Code and press **`F5`** (or select **"Python: Run EmergencyCare 360"** in the Run & Debug tab).

---

## 🔐 Default Demo Credentials

When the app starts for the first time, demo accounts are created automatically:

| Portal | URL Path | Username | Password | Role & Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Doctor / Clinician** | `/staff/login` | `dr.demo` | `EmergencyCare2026!` | Can set Clinical Triage Priority (*Immediate/Urgent/Standard*), update status, enter vitals. |
| **Nurse** | `/staff/login` | `nurse.demo` | `EmergencyCare2026!` | Can update status, record vitals, assign beds (cannot set priority). |
| **Patient Registration**| `/` | *None* | *Public* | Self-registration & token generation. |
| **Status Tracking** | `/track` | *None* | *Public* | Look up by Patient ID + Phone number. |

*(Password is configurable via `STAFF_PASSWORD` in `.env`)*

---

## ⚙️ Environment Variables

Copy `emergencycare360/.env.example` to `emergencycare360/.env`:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask session cryptographic signing key | `dev-secret-key-360-hacktitans` |
| `STAFF_PASSWORD` | Password for default demo staff accounts | `EmergencyCare2026!` |
| `DATABASE_URL` | DB connection string (Empty = local SQLite) | `mysql://user:pass@host:4000/db` |
| `DB_SSL` | Enable TLS encryption for database connection | `true` (required for TiDB Cloud) |
| `SEED_DEMO_PATIENTS` | Populate demo patients & beds on start | `true` |
| `ELEVENLABS_API_KEY` | *(Optional)* API key for ElevenLabs TTS | `sk_...` |
| `ELEVENLABS_VOICE_ID` | Voice ID for status announcements | `21m00Tcm4TlvDq8ikWAM` |
| `ELEVENLABS_AGENT_ID` | ElevenLabs conversational agent ID | `agent_4201m7y7f9q0fcrrmnh2qkh8zjtw` |
| `PORT` | Local server port | `5000` |
| `FLASK_DEBUG` | Flask auto-reload and debug mode | `1` (development) / `0` (production) |

---

## 🧪 Running Automated Tests

A comprehensive Pytest test suite validates patient registration, token generation, triage authorization, status transitions, and bed allocation.

Run tests from the `emergencycare360` directory:

```bash
cd emergencycare360
python -m pytest -v tests
```

---

## ☁️ Deployment Guide (Render + TiDB Cloud)

### Option 1: Blueprint Deployment (Recommended)
1. Push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com/), select **New +** ➡️ **Blueprint**.
3. Select your repository. Render automatically reads `emergencycare360/render.yaml`.
4. Fill in the required environment variables:
   - `STAFF_PASSWORD`
   - `DATABASE_URL` (from TiDB Cloud)
   - `ELEVENLABS_API_KEY` (optional)

---

### Option 2: Manual Web Service Deployment
1. Click **New +** ➡️ **Web Service** in Render.
2. Configure settings:
   - **Runtime**: `Python`
   - **Root Directory**: `emergencycare360`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT`
   - **Health Check Path**: `/health`
3. Add **Environment Variables**:
   - `PYTHON_VERSION`: `3.12.8`
   - `SECRET_KEY`: *(Generate a secure random string)*
   - `STAFF_PASSWORD`: `EmergencyCare2026!`
   - `SEED_DEMO_PATIENTS`: `true`
   - `DATABASE_URL`: Your TiDB MySQL connection URL (e.g. `mysql://user:pass@gateway.tidbcloud.com:4000/emergencycare`)

> **Note on Persistent Storage**: Render free-tier web services have ephemeral storage. Using **TiDB Cloud** (Free Serverless Tier) ensures your patient records, beds, and audio cache persist across deployments.

---

## 🛡️ Privacy, Ethics & Medical Safety

- **Clinical Decision Disclaimer**: EmergencyCare 360 only organizes and visualizes hospital workflow information. **Clinical triage priority and medical diagnoses are strictly set by licensed, authenticated hospital medical personnel.**
- **AI Safety Guardrails**: The conversational assistant provides first-aid references and hospital process orientation only. Critical emergency conditions trigger an immediate recommendation to see medical staff.
- **Privacy by Design**: No patient health identifiers (PHI) or personal details are ever transmitted to external voice APIs. Only standardized, pre-compiled system status strings are synthesized.
- **Consent Gate**: Family status tracking requires explicit patient consent during intake.

---

## 👥 License & Acknowledgments

- **Event**: HackForge 2K26
- **Team**: HackTitans
- **License**: MIT License - open for educational and healthcare innovation purposes.
