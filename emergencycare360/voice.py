"""ElevenLabs text-to-speech for status announcements.

Privacy: the text sent to ElevenLabs is chosen ONLY from the fixed templates below.
No patient name, ID, symptoms or any other record data can reach the API, because the
request carries just (kind, state, language) and the server maps that to a fixed sentence.
Cost: with 14 distinct sentences, every clip is generated once and then served from the
database cache, which keeps free-tier credit use tiny.
"""
import hashlib
import os
import threading

import requests

from models import AudioCache, db

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"

REGISTERED = {
    "en": "Your emergency registration is complete. Please keep your ID code ready and wait for hospital staff.",
    "hi": "आपका आपातकालीन पंजीकरण पूरा हो गया है। कृपया अपना आईडी कोड तैयार रखें और अस्पताल के कर्मचारियों की प्रतीक्षा करें।",
}
STATUS = [
    {"en": "Your status is now: Registered. Hospital staff will review your details shortly.",
     "hi": "आपकी स्थिति अब: पंजीकृत है। अस्पताल के कर्मचारी जल्द ही आपकी जानकारी देखेंगे।"},
    {"en": "Your status is now: Waiting for assessment. Please stay near the emergency desk.",
     "hi": "आपकी स्थिति अब: जांच की प्रतीक्षा है। कृपया आपातकालीन डेस्क के पास रहें।"},
    {"en": "Your status is now: Under assessment. A member of staff is assessing you.",
     "hi": "आपकी स्थिति अब: जांच जारी है। अस्पताल के कर्मचारी आपकी जांच कर रहे हैं।"},
    {"en": "Your status is now: Treatment in progress.",
     "hi": "आपकी स्थिति अब: इलाज जारी है।"},
    {"en": "Your status is now: Referred. Please follow the instructions given by staff.",
     "hi": "आपकी स्थिति अब: रेफर किया गया है। कृपया कर्मचारियों के निर्देशों का पालन करें।"},
    {"en": "Your status is now: Discharged. Please follow the discharge instructions given by staff.",
     "hi": "आपकी स्थिति अब: छुट्टी दी गई है। कृपया कर्मचारियों द्वारा दिए गए निर्देशों का पालन करें।"},
]


class VoiceError(Exception):
    pass


def enabled():
    return bool(os.getenv("ELEVENLABS_API_KEY"))


def announcement(kind, state, lang):
    """Return the fixed sentence for (kind, state, lang) or None if not allowed."""
    if lang not in ("en", "hi"):
        return None
    if kind == "registered":
        return REGISTERED[lang]
    if kind == "status":
        try:
            i = int(state)
        except (TypeError, ValueError):
            return None
        return STATUS[i][lang] if 0 <= i < len(STATUS) else None
    return None


def _voice_id(lang):
    return (os.getenv("ELEVENLABS_VOICE_ID_HI") if lang == "hi" else None) \
        or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"


_locks = {}
_locks_guard = threading.Lock()


def synthesize(text, lang):
    """Return (mp3_bytes, mime). Reads the cache first; calls ElevenLabs only on a miss."""
    model = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    voice = _voice_id(lang)
    key = hashlib.sha256(f"{model}|{voice}|{lang}|{text}".encode()).hexdigest()
    hit = db.session.get(AudioCache, key)
    if hit:
        return hit.data, hit.mime
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:  # one generation per clip even under concurrent requests
        db.session.expire_all()
        hit = db.session.get(AudioCache, key)
        if hit:
            return hit.data, hit.mime
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise VoiceError("not configured")
        try:
            r = requests.post(
                API.format(voice=voice), params={"output_format": "mp3_44100_64"},
                headers={"xi-api-key": api_key, "Accept": "audio/mpeg"},
                json={"text": text, "model_id": model,
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                timeout=25)
        except requests.RequestException as e:
            raise VoiceError("network") from e
        if r.status_code != 200 or not r.content:
            raise VoiceError(f"upstream {r.status_code}")
        db.session.add(AudioCache(key=key, lang=lang, chars=len(text), data=r.content))
        db.session.commit()
        return r.content, "audio/mpeg"
