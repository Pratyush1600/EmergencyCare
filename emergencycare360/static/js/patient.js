/* Patient portal: registration, status tracking, family view, Hindi/English, voice (ElevenLabs via Flask). */
(function () {
  const { $, $$, esc, api, toast } = EC;
  const D = {
    en: {
      skip: "Skip to content", nav_register: "Emergency registration", nav_status: "My status", nav_staff: "Staff login",
      footer: "All patients shown in this demo are fictional. The system only organises information; clinical priority is always set by hospital staff.",
      panel_eyebrow: "Patient portal", panel_h: "Clearer, faster emergency care",
      p1: "Register in about two minutes, before you reach the desk.", p2: "Live status with voice announcements in Hindi and English.",
      p3: "A QR code that helps staff find your record quickly.", p4: "Your family sees your status only if you give consent.",
      p5: "Doctors and nurses decide priority. This tool only organises information.", sos: "In immediate danger? Tell the nearest staff member or call 112.",
      reg_title: "Emergency registration", reg_sub: "Tell us what is happening. Hospital staff will review your details and update your status here.",
      sec_you: "About you", name: "Full name", age: "Age", phone: "Phone number", kin: "Family contact number",
      kin_help: "Optional. Needed only if you want your family to see your status.", sec_sym: "Symptoms", sym: "What is wrong, and when did it start?",
      sec_bg: "Medical background", hist: "Medical history", hist_ph: "Conditions, medicines, or “None”", all: "Allergies", all_ph: "e.g. Penicillin, or “None”",
      rep: "Previous reports (optional)", rep_help: "PDF, JPG or PNG, up to 3 MB.",
      cons: "Let my family contact see my status. Only the status is shared, never medical details.", go: "Submit registration", submitting: "Submitting…", have_id: "Already registered? Check your status",
      err_name_required: "Please enter your full name.", err_age_invalid: "Enter an age between 0 and 120.", err_phone_invalid: "Enter a valid phone number.",
      err_kin_invalid: "Enter a valid phone number or leave this blank.", err_symptoms_required: "Please describe your symptoms.",
      err_file_type: "Only PDF, JPG or PNG files are accepted.", err_file_size: "The file is larger than 3 MB.", err_generic: "Something went wrong. Please try again or see the front desk.",
      look_title: "Check your status", look_sub: "Enter the ID you received at registration and the phone number you used.", look_code: "Patient ID", look_go: "Show my status",
      look_err: "We couldn't match that ID and phone number. Please check and try again.",
      hello: "Hello", your_id: "Your ID", listen: "Listen", stop: "Stop", loading: "Loading…", auto: "Announce updates automatically", transcript: "Announcement",
      read_aloud: "Read form aloud", speak_status: "Speak status", talk_ai: "Talk to AI",
      updated: "Last updated", auto_ref: "Refreshes automatically", reg_done: "Registration complete", reg_done_sub: "Keep your ID ready and wait for hospital staff. This page updates by itself.",
      timeline: "Status timeline", qr_h: "Your QR code", qr_sub: "Show this at the desk so staff can find your record.",
      bed: "Bed", dept: "Department", missing_h: "Help us complete your record", missing_sub: "Add what you can. Staff will ask for anything else.",
      m_history: "Medical history", m_allergies: "Allergies", m_kin_phone: "Family contact number", save: "Save details", saved: "Thank you. Your details were saved.",
      share_h: "Family sharing", share_on: "Your family can see your status (status only).", share_off: "Family sharing is off.", share_link: "Family link", copy: "Copy link", copied: "Link copied",
      status_changed: "Your status is now", voice_fallback: "Playing with your device's voice.", voice_none: "Voice is not available on this device.", tap_listen: "Tap Listen to hear the update.",
      help0: "Hospital staff will review your details shortly.", help1: "Please stay near the emergency desk.", help2: "A member of staff is assessing you.",
      help3: "Your treatment is in progress.", help4: "Please follow the instructions given by staff.", help5: "Please follow the discharge instructions given by staff.",
      not_found: "We couldn't find this record.", fam_h: "Patient status", fam_off: "This link is not active. The patient may have turned sharing off.",
      fam_note: "Only the status is shared. No medical details are visible.", step_next: "Next"
    },
    hi: {
      skip: "मुख्य सामग्री पर जाएं", nav_register: "आपातकालीन पंजीकरण", nav_status: "मेरी स्थिति", nav_staff: "स्टाफ लॉगिन",
      footer: "इस डेमो में सभी मरीज़ काल्पनिक हैं। यह सिस्टम केवल जानकारी व्यवस्थित करता है; चिकित्सकीय प्राथमिकता हमेशा अस्पताल कर्मचारी तय करते हैं।",
      panel_eyebrow: "रोगी पोर्टल", panel_h: "स्पष्ट और तेज़ आपातकालीन देखभाल",
      p1: "काउंटर पर पहुंचने से पहले लगभग दो मिनट में पंजीकरण करें।", p2: "हिन्दी और अंग्रेज़ी में आवाज़ के साथ लाइव स्थिति।",
      p3: "QR कोड से स्टाफ आपका रिकॉर्ड जल्दी ढूंढ सकता है।", p4: "आपकी सहमति होने पर ही परिवार आपकी स्थिति देख सकेगा।",
      p5: "प्राथमिकता डॉक्टर और नर्स तय करते हैं। यह टूल केवल जानकारी व्यवस्थित करता है।", sos: "तुरंत खतरा है? नज़दीकी कर्मचारी को बताएं या 112 पर कॉल करें।",
      reg_title: "आपातकालीन पंजीकरण", reg_sub: "हमें बताइए क्या हो रहा है। अस्पताल कर्मचारी आपकी जानकारी देखकर यहीं आपकी स्थिति अपडेट करेंगे।",
      sec_you: "आपके बारे में", name: "पूरा नाम", age: "आयु", phone: "फ़ोन नंबर", kin: "परिवार का संपर्क नंबर",
      kin_help: "वैकल्पिक। केवल तब चाहिए जब आप चाहते हों कि परिवार आपकी स्थिति देखे।", sec_sym: "लक्षण", sym: "क्या परेशानी है और कब से शुरू हुई?",
      sec_bg: "चिकित्सा पृष्ठभूमि", hist: "चिकित्सा इतिहास", hist_ph: "बीमारियां, दवाएं, या “कोई नहीं”", all: "एलर्जी", all_ph: "जैसे पेनिसिलिन, या “कोई नहीं”",
      rep: "पिछली रिपोर्ट (वैकल्पिक)", rep_help: "PDF, JPG या PNG, अधिकतम 3 MB।",
      cons: "मेरे परिवार के संपर्क को मेरी स्थिति देखने दें। केवल स्थिति साझा होगी, चिकित्सा विवरण कभी नहीं।", go: "पंजीकरण जमा करें", submitting: "जमा हो रहा है…", have_id: "पहले से पंजीकृत हैं? अपनी स्थिति देखें",
      err_name_required: "कृपया अपना पूरा नाम लिखें।", err_age_invalid: "0 से 120 के बीच आयु लिखें।", err_phone_invalid: "सही फ़ोन नंबर लिखें।",
      err_kin_invalid: "सही फ़ोन नंबर लिखें या खाली छोड़ दें।", err_symptoms_required: "कृपया लक्षण बताएं।",
      err_file_type: "केवल PDF, JPG या PNG फ़ाइलें मान्य हैं।", err_file_size: "फ़ाइल 3 MB से बड़ी है।", err_generic: "कुछ गलत हो गया। कृपया फिर प्रयास करें या फ्रंट डेस्क पर संपर्क करें।",
      look_title: "अपनी स्थिति देखें", look_sub: "पंजीकरण पर मिला आईडी और अपना फ़ोन नंबर लिखें।", look_code: "रोगी आईडी", look_go: "मेरी स्थिति दिखाएं",
      look_err: "यह आईडी और फ़ोन नंबर मेल नहीं खाए। कृपया जांचकर फिर प्रयास करें।",
      hello: "नमस्ते", your_id: "आपका आईडी", listen: "सुनें", stop: "रोकें", loading: "लोड हो रहा है…", auto: "अपडेट अपने आप सुनाएं", transcript: "घोषणा",
      read_aloud: "फ़ॉर्म पढ़कर सुनाएं", speak_status: "पूरी स्थिति सुनें", talk_ai: "एआई से बात करें",
      updated: "अंतिम अपडेट", auto_ref: "अपने आप ताज़ा होता है", reg_done: "पंजीकरण पूरा हुआ", reg_done_sub: "अपना आईडी तैयार रखें और अस्पताल कर्मचारियों की प्रतीक्षा करें। यह पेज अपने आप अपडेट होता है।",
      timeline: "स्थिति की समयरेखा", qr_h: "आपका QR कोड", qr_sub: "काउंटर पर दिखाएं ताकि स्टाफ आपका रिकॉर्ड ढूंढ सके।",
      bed: "बिस्तर", dept: "विभाग", missing_h: "अपना रिकॉर्ड पूरा करने में मदद करें", missing_sub: "जो बता सकें जोड़ें। बाकी स्टाफ पूछ लेगा।",
      m_history: "चिकित्सा इतिहास", m_allergies: "एलर्जी", m_kin_phone: "परिवार का संपर्क नंबर", save: "जानकारी सहेजें", saved: "धन्यवाद। आपकी जानकारी सहेज ली गई।",
      share_h: "परिवार के साथ साझा करना", share_on: "आपका परिवार आपकी स्थिति देख सकता है (केवल स्थिति)।", share_off: "परिवार के साथ साझा करना बंद है।", share_link: "परिवार का लिंक", copy: "लिंक कॉपी करें", copied: "लिंक कॉपी हो गया",
      status_changed: "आपकी स्थिति अब है", voice_fallback: "आपके डिवाइस की आवाज़ से चल रहा है।", voice_none: "इस डिवाइस पर आवाज़ उपलब्ध नहीं है।", tap_listen: "अपडेट सुनने के लिए “सुनें” दबाएं।",
      help0: "अस्पताल के कर्मचारी जल्द ही आपकी जानकारी देखेंगे।", help1: "कृपया आपातकालीन डेस्क के पास रहें।", help2: "अस्पताल के कर्मचारी आपकी जांच कर रहे हैं।",
      help3: "आपका इलाज जारी है।", help4: "कृपया कर्मचारियों के निर्देशों का पालन करें।", help5: "कृपया कर्मचारियों द्वारा दिए गए छुट्टी के निर्देशों का पालन करें।",
      not_found: "यह रिकॉर्ड नहीं मिला।", fam_h: "मरीज़ की स्थिति", fam_off: "यह लिंक चालू नहीं है। हो सकता है मरीज़ ने साझा करना बंद कर दिया हो।",
      fam_note: "केवल स्थिति साझा की जाती है। कोई चिकित्सा विवरण दिखाई नहीं देता।", step_next: "आगे"
    }
  };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };
  let lang = store.get("ec_lang") === "hi" ? "hi" : "en";
  const t = k => (D[lang] && D[lang][k]) || D.en[k] || k;

  function applyI18n() {
    $$("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
    $$("[data-lang]").forEach(b => { const on = b.dataset.lang === lang; b.classList.toggle("active", on); b.setAttribute("aria-pressed", on); });
    document.documentElement.lang = lang;
  }
  function setLang(l) { lang = l; EC.loc = l === "hi" ? "hi-IN" : undefined; store.set("ec_lang", l); applyI18n(); document.dispatchEvent(new Event("langchange")); }
  $$("[data-lang]").forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang)));
  const saved = store.get("ec_token");
  if (saved && $("#navStatus")) $("#navStatus").href = "/track/" + saved;
  EC.loc = lang === "hi" ? "hi-IN" : undefined;
  applyI18n();

  // ---------- voice (server-side ElevenLabs proxy, with device-voice fallback)
  const Voice = {
    audio: null, onState: () => {},
    stop() {
      if (this.audio) { this.audio.pause(); this.audio = null; }
      if ("speechSynthesis" in window) speechSynthesis.cancel();
      this.onState(false);
    },
    async play(kind, state, text, enabled, quiet) {
      this.stop(); this.onState(true);
      try {
        if (!enabled) throw new Error("off");
        const a = this.audio = new Audio(`/api/tts?kind=${kind}&state=${state ?? 0}&lang=${lang}`);
        a.onended = () => { this.audio = null; this.onState(false); };
        await a.play();
      } catch (e) {
        this.audio = null;
        if (e && e.name === "NotAllowedError") { this.onState(false); if (quiet) toast(t("tap_listen"), "info"); return; }
        if ("speechSynthesis" in window && text) {
          const u = new SpeechSynthesisUtterance(text); u.lang = lang === "hi" ? "hi-IN" : "en-IN";
          u.onend = () => this.onState(false); speechSynthesis.cancel(); speechSynthesis.speak(u);
          if (!quiet) toast(t("voice_fallback"), "info");
        } else { this.onState(false); toast(t("voice_none"), "warning"); }
      }
    },
    async speakText(text, options = {}) {
      if (this.audio || ("speechSynthesis" in window && speechSynthesis.speaking)) {
        this.stop();
        return;
      }
      this.stop();
      this.onState(true);
      const curLang = options.lang || lang || "en";
      const token = options.token || "";
      try {
        const query = token ? `token=${encodeURIComponent(token)}&lang=${curLang}` : `text=${encodeURIComponent(text)}&lang=${curLang}`;
        const res = await fetch(`/api/tts/speak?${query}`);
        const cType = res.headers.get("Content-Type") || "";
        if (res.ok && cType.includes("audio")) {
          const blob = await res.blob();
          const blobUrl = URL.createObjectURL(blob);
          const a = this.audio = new Audio(blobUrl);
          a.onended = () => {
            URL.revokeObjectURL(blobUrl);
            this.audio = null;
            this.onState(false);
            if (options.onEnd) options.onEnd();
          };
          await a.play();
          toast(curLang === "hi" ? "इलेवनलैब्स मानवीय आवाज़" : "ElevenLabs Human Voice", "success");
          return;
        }
        if (res.ok) {
          const info = await res.json();
          if (info.text) text = info.text;
        }
      } catch (err) {
        console.warn("ElevenLabs TTS endpoint notice:", err);
      }
      if ("speechSynthesis" in window && text) {
        const u = new SpeechSynthesisUtterance(text);
        u.lang = curLang === "hi" ? "hi-IN" : "en-IN";
        u.rate = 0.95;
        u.pitch = 1.0;
        u.onend = () => {
          this.onState(false);
          if (options.onEnd) options.onEnd();
        };
        speechSynthesis.cancel();
        speechSynthesis.speak(u);
        toast(curLang === "hi" ? "आवाज़ में सुनाया जा रहा है" : "Speaking update", "info");
      } else {
        this.onState(false);
        toast(t("voice_none"), "warning");
      }
    }
  };

  const page = document.body.dataset.page;
  if (page === "register") initRegister();
  if (page === "lookup") initLookup();
  if (page === "track") initTrack();
  if (page === "family") initFamily();

  // ---------- registration
  function initRegister() {
    const form = $("#regForm"), btn = $("#go");
    const setErr = (f, code) => { const i = form.elements[f] || $("#f-" + f); const e = $("#e-" + f); if (!i || !e) return; i.classList.toggle("is-invalid", !!code); e.textContent = code ? t("err_" + code) : ""; };
    const FIELDS = ["name", "age", "phone", "kin_phone", "symptoms", "report"];
    form.addEventListener("input", e => { if (e.target.name) setErr(e.target.name, null); });
    document.addEventListener("langchange", () => FIELDS.forEach(f => { const i = form.elements[f]; if (i && i.classList.contains("is-invalid")) $("#e-" + f).dataset.code && setErr(f, $("#e-" + f).dataset.code); }));
    form.addEventListener("submit", async ev => {
      ev.preventDefault();
      const v = n => form.elements[n].value.trim(), errs = {};
      const phoneOk = s => /^[0-9+\-() ]{7,20}$/.test(s) && s.replace(/\D/g, "").length >= 7;
      if (v("name").length < 2) errs.name = "name_required";
      const age = parseInt(v("age"), 10); if (isNaN(age) || age < 0 || age > 120) errs.age = "age_invalid";
      if (!phoneOk(v("phone"))) errs.phone = "phone_invalid";
      if (v("kin_phone") && !phoneOk(v("kin_phone"))) errs.kin_phone = "kin_invalid";
      if (v("symptoms").length < 3) errs.symptoms = "symptoms_required";
      const file = form.elements.report.files[0];
      if (file && file.size > 3 * 1024 * 1024) errs.report = "file_size";
      if (file && !/\.(pdf|jpe?g|png)$/i.test(file.name)) errs.report = "file_type";
      show(errs); if (Object.keys(errs).length) { const first = FIELDS.find(f => errs[f]); form.elements[first].focus(); return; }
      const fd = new FormData(form); fd.set("consent", $("#f-consent").checked ? "1" : "0"); fd.set("lang", lang);
      btn.disabled = true; btn.querySelector("span").textContent = t("submitting");
      try {
        const r = await api("/api/register", { method: "POST", body: fd });
        store.set("ec_token", r.token); location.href = r.track_url + "?new=1";
      } catch (e) {
        btn.disabled = false; btn.querySelector("span").textContent = t("go");
        if (e.data && e.data.errors) show(e.data.errors); else toast(t("err_generic"), "danger");
      }
    });
    function show(errs) { FIELDS.forEach(f => { setErr(f, errs[f]); const e = $("#e-" + f); if (e) e.dataset.code = errs[f] || ""; }); }
    const speakBtn = $("#btnSpeakForm");
    if (speakBtn) {
      speakBtn.addEventListener("click", () => {
        const text = lang === "hi"
          ? "इमरजेंसी केयर 360 पंजीकरण में आपका स्वागत है। कृपया अपना नाम, आयु, फ़ोन नंबर, और अपने लक्षण दर्ज करें। अस्पताल स्टाफ आपकी प्राथमिकता तय करेगा।"
          : "Welcome to EmergencyCare 360 registration. Please enter your full name, age, phone number, and current symptoms. Hospital staff will review your details.";
        Voice.speakText(text, { lang });
      });
    }
    document.addEventListener("click", e => {
      const qp = e.target.closest(".quick-prompt-btn");
      if (qp) {
        e.preventDefault();
        const prompt = qp.dataset.prompt;
        window.openElevenLabsAgent();
        toast(prompt, "info");
      }
    });
  }

  function initLookup() {
    $("#lookForm").addEventListener("submit", async ev => {
      ev.preventDefault(); $("#l-err").textContent = "";
      try { const r = await api("/api/lookup", { method: "POST", body: { code: $("#l-code").value, phone: $("#l-phone").value } }); store.set("ec_token", r.token); location.href = r.track_url; }
      catch (e) { $("#l-err").textContent = t("look_err"); }
    });
  }

  // ---------- tracking
  function initTrack() {
    const app = $("#app"), token = app.dataset.token;
    let data = null, last = null, first = true, isNew = new URLSearchParams(location.search).get("new") === "1", auto = store.get("ec_auto") === "1", cache = {};
    store.set("ec_token", token);
    const put = (id, html) => { const el = $("#" + id); if (el && cache[id] !== html) { cache[id] = html; el.innerHTML = html; } };

    app.innerHTML = `<div id="newBanner"></div><div class="row g-3"><div class="col-lg-8"><section id="hero" class="h-100"></section></div><div class="col-lg-4"><section id="qr" class="h-100"></section></div>
      <div class="col-lg-7"><section id="timeline" class="ec-card h-100"></section></div><div class="col-lg-5 d-flex flex-column gap-3"><section id="missing"></section><section id="share"></section></div></div>
      <p class="sub text-center mt-3" id="stamp" aria-live="off"></p>`;

    Voice.onState = on => {
      const b = $("#listenBtn"); if (!b) return; b.classList.toggle("playing", on);
      b.setAttribute("aria-pressed", on); b.querySelector("i").className = on ? "bi bi-stop-circle-fill" : "bi bi-volume-up-fill"; b.querySelector("span").textContent = on ? t("stop") : t("listen");
    };

    async function load() {
      try { data = await api(`/api/track/${token}`); } catch (e) { if (e.status === 404) { app.innerHTML = `<div class="ec-card text-center mx-auto" style="max-width:480px"><span class="icon-chip mb-3"><i class="bi bi-question-circle"></i></span><p class="mb-3">${t("not_found")}</p><a class="btn btn-primary" href="/track">${t("nav_status")}</a></div>`; clearInterval(timer); } return; }
      if (last !== null && data.status !== last) {
        toast(`${t("status_changed")}: ${lang === "hi" ? data.status_label_hi : data.status_label}`, "info");
        if (auto) Voice.play("status", data.status, data.announce[lang], data.voice, true);
      }
      last = data.status; render();
      if (first) { first = false; if (isNew && data.voice) { Voice.play("registered", 0, data.announce_registered[lang], data.voice, true); } }
    }

    function render() {
      const d = data, hi = lang === "hi";
      put("newBanner", isNew ? `<div class="alert alert-success d-flex gap-3 align-items-start" role="status"><i class="bi bi-check-circle-fill fs-4"></i><div><b>${t("reg_done")}</b><div>${t("reg_done_sub")}</div></div></div>` : "");
      put("hero", `<div class="ec-card status-hero p-4 h-100">
        <div class="d-flex flex-wrap justify-content-between gap-2"><div><div class="eyebrow" style="color:#7fd6d7">${t("hello")}, ${esc(d.first_name)}</div><h1 class="h2 mt-1 mb-2">${esc(hi ? d.status_label_hi : d.status_label)}</h1></div>
        <div class="text-end"><div class="text-muted small">${t("your_id")}</div><div class="fs-4 fw-bold">${esc(d.code)}</div></div></div>
        <p class="mb-3" style="color:#dbe7f3">${t("help" + d.status)}</p>
        <div class="d-flex flex-wrap align-items-center gap-3">
          <button class="btn btn-listen" id="listenBtn" type="button" aria-pressed="false"><i class="bi bi-volume-up-fill fs-5"></i><span>${t("listen")}</span></button>
          <button class="btn btn-soft d-inline-flex align-items-center gap-1" id="speakFullBtn" type="button" title="Speak full personalized status update in human voice"><i class="bi bi-soundwave text-teal fs-5"></i><span>${t("speak_status")}</span></button>
          <button class="btn btn-soft d-inline-flex align-items-center gap-1 trigger-elevenlabs-btn" type="button" title="Speak to ElevenLabs AI Agent"><i class="bi bi-mic-fill text-teal"></i><span>${t("talk_ai")}</span></button>
          <div class="form-check form-switch m-0 ps-0 d-flex align-items-center gap-2"><input class="form-check-input ms-0 mt-0" type="checkbox" role="switch" id="autoSw" ${auto ? "checked" : ""}><label class="form-check-label" for="autoSw">${t("auto")}</label></div></div>
        <div class="transcript" id="tr" hidden><b>${t("transcript")}:</b> <span id="trText"></span></div>
        <div class="d-flex flex-wrap gap-3 mt-3 small" style="color:#b8c9dc">${d.dept ? `<span><i class="bi bi-building me-1"></i>${t("dept")}: ${esc(d.dept)}</span>` : ""}${d.bed ? `<span><i class="bi bi-hospital me-1"></i>${t("bed")}: ${esc(d.bed)}</span>` : ""}</div></div>`);
      put("qr", `<div class="ec-card text-center h-100"><h2 class="h6 mb-3">${t("qr_h")}</h2><div class="qr-box"><img src="${esc(d.qr_url)}" alt="QR code for ${esc(d.code)}" width="168" height="168"></div><div class="fw-bold fs-5 mt-2">${esc(d.code)}</div><p class="sub mb-0">${t("qr_sub")}</p></div>`);
      const done = d.timeline.map((e, i) => `<li class="${i === d.timeline.length - 1 ? "current" : "done"}"><span class="dot"><i class="bi bi-check-lg"></i></span><div class="t-title">${esc(hi ? EC.STATUS_HI[e.status] : EC.STATUS[e.status])}</div><div class="t-time">${EC.dt(e.at)}</div></li>`);
      const up = []; for (let s = d.status + 1; s <= 3; s++) up.push(`<li class="upcoming"><span class="dot"></span><div class="t-title">${esc(hi ? EC.STATUS_HI[s] : EC.STATUS[s])}</div><div class="t-time">${t("step_next")}</div></li>`);
      put("timeline", `<h2 class="h5 mb-3">${t("timeline")}</h2><ol class="tl" aria-label="${t("timeline")}">${done.join("")}${up.join("")}</ol>`);
      put("missing", d.missing.length ? `<div class="ec-card" style="border-color:#f1d9a0;background:#fffaf0"><h2 class="h5 mb-1"><i class="bi bi-exclamation-circle text-warning me-1"></i>${t("missing_h")}</h2><p class="sub">${t("missing_sub")}</p>
        <form id="missForm" novalidate>${d.missing.map(m => `<label class="form-label" for="m-${m.key}">${t("m_" + m.key)}</label><input class="form-control mb-2" id="m-${m.key}" name="${m.key}" ${m.key === "kin_phone" ? 'inputmode="tel"' : ""} maxlength="300">`).join("")}<div class="text-danger small" id="missErr" role="alert"></div><button class="btn btn-primary mt-1" type="submit">${t("save")}</button></form></div>` : "");
      put("share", `<div class="ec-card"><div class="d-flex justify-content-between align-items-start gap-2"><div><h2 class="h5 mb-1">${t("share_h")}</h2><p class="sub mb-0">${d.consent ? t("share_on") : t("share_off")}</p></div>
        <div class="form-check form-switch m-0"><input class="form-check-input" type="checkbox" role="switch" id="consentSw" aria-label="${t("share_h")}" ${d.consent ? "checked" : ""}></div></div>
        ${d.family_url ? `<label class="form-label mt-3" for="famUrl">${t("share_link")}</label><div class="input-group"><input class="form-control" id="famUrl" readonly value="${esc(d.family_url)}"><button class="btn btn-soft" type="button" id="copyFam"><i class="bi bi-clipboard"></i> ${t("copy")}</button></div>` : ""}</div>`);
      $("#stamp").textContent = `${t("updated")} ${EC.time(d.updated_at)} · ${t("auto_ref")}`;
    }

    app.addEventListener("click", e => {
      if (e.target.closest("#listenBtn")) {
        if (Voice.audio || ("speechSynthesis" in window && speechSynthesis.speaking)) return Voice.stop();
        const txt = (isNew && last === 0 ? data.announce_registered : data.announce)[lang];
        $("#tr").hidden = false; $("#trText").textContent = txt;
        Voice.play(isNew && last === 0 ? "registered" : "status", data.status, txt, data.voice, false);
      }
      if (e.target.closest("#speakFullBtn")) {
        Voice.speakText("", { token, lang });
      }
      if (e.target.closest("#copyFam")) { navigator.clipboard && navigator.clipboard.writeText($("#famUrl").value).then(() => toast(t("copied"))); }
    });
    app.addEventListener("change", async e => {
      if (e.target.id === "autoSw") { auto = e.target.checked; store.set("ec_auto", auto ? "1" : "0"); }
      if (e.target.id === "consentSw") { try { data = await api(`/api/track/${token}/details`, { method: "POST", body: { consent: e.target.checked } }); render(); } catch (err) { toast(t("err_generic"), "danger"); } }
    });
    app.addEventListener("submit", async e => {
      if (e.target.id !== "missForm") return; e.preventDefault();
      const body = {}; EC.$$("input", e.target).forEach(i => { if (i.value.trim()) body[i.name] = i.value.trim(); });
      if (!Object.keys(body).length) return;
      try { data = await api(`/api/track/${token}/details`, { method: "POST", body }); cache.missing = null; render(); toast(t("saved")); }
      catch (err) { $("#missErr").textContent = t(err.data && err.data.errors ? "err_kin_invalid" : "err_generic"); }
    });
    document.addEventListener("langchange", () => { cache = {}; if (data) render(); });
    const timer = setInterval(() => { if (!document.hidden) load(); }, 8000);
    load();
  }

  // ---------- family (consent-based, status only)
  function initFamily() {
    const app = $("#app"), token = app.dataset.token;
    async function load() {
      try {
        const d = await api(`/api/family/${token}`), hi = lang === "hi";
        app.innerHTML = `<div class="ec-card p-4 text-center"><span class="icon-chip mb-3"><i class="bi bi-people"></i></span><div class="eyebrow">${t("fam_h")}</div><h1 class="h3 my-2">${esc(d.first_name)}</h1>${EC.pill(d.status, lang).replace('pill', 'pill lg')}<p class="sub mt-3 mb-1">${t("updated")} ${EC.time(d.updated_at)} · ${t("auto_ref")}</p><p class="sub mb-0"><i class="bi bi-shield-lock me-1"></i>${t("fam_note")}</p></div>`;
      } catch (e) { app.innerHTML = `<div class="ec-card text-center"><span class="icon-chip mb-3"><i class="bi bi-lock"></i></span><p class="mb-0">${t("fam_off")}</p></div>`; }
    }
    document.addEventListener("langchange", load); setInterval(() => { if (!document.hidden) load(); }, 10000); load();
  }
})();
