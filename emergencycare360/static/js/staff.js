/* Staff dashboard: overview, patients (+ handover, QR scan), beds & resources, audit log. */
(function () {
  const { $, $$, esc, api, toast, pill, pri, dt, ago } = EC;
  const page = document.body.dataset.page;
  const poll = (fn, ms) => { fn(); setInterval(() => { if (!document.hidden) fn(); }, ms); };
  const miss = n => n ? `<span class="miss-chip"><i class="bi bi-exclamation-circle"></i>${n} missing</span>` : `<span class="text-success small"><i class="bi bi-check-circle"></i> Complete</span>`;
  const err = e => toast(e.message || "Something went wrong", "danger");

  if (page === "overview") overview();
  if (page === "patients") patients();
  if (page === "resources") resources();
  if (page === "audit") auditLog();

  // =================================================================== overview
  function overview() {
    let c1, c2;
    const tile = (icon, n, label, warn) => `<div class="col-6 col-lg-4 col-xxl-2"><div class="ec-card stat h-100 ${warn && n ? "alert-tile" : ""}"><span class="icon-chip"><i class="bi bi-${icon}"></i></span><div><b>${n}</b><span>${label}</span></div></div></div>`;
    const bar = (free, total, name) => { const pc = total ? free / total * 100 : 0; return `<div class="mb-3"><div class="d-flex justify-content-between small fw-semibold mb-1"><span>${esc(name)}</span><span>${free} free of ${total}</span></div><div class="meter ${pc < 25 ? "low" : ""}" role="img" aria-label="${esc(name)}: ${free} free of ${total}"><i style="width:${pc}%"></i></div></div>`; };
    poll(async () => {
      let d; try { d = await api("/staff/api/overview"); } catch (e) { return; }
      const s = d.stats;
      $("#stats").innerHTML = tile("people", s.total, "Registered today") + tile("hourglass-split", s.waiting, "Waiting") + tile("activity", s.in_care, "Assessment or treatment") +
        tile("flag", s.awaiting_priority, "Awaiting staff priority", true) + tile("exclamation-triangle", s.missing, "Records with missing info", true) + tile("stopwatch", s.longest_wait_min + " min", "Longest wait");
      const grid = "#E4EBF2", tick = "#58697E";
      if (!c1) {
        c1 = new Chart($("#chStatus"), { type: "bar", data: { labels: ["Registered", "Waiting", "Assessing", "Treatment", "Referred", "Discharged"], datasets: [{ data: d.by_status.values, backgroundColor: "#087E80", borderRadius: 6 }] }, options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1, color: tick }, grid: { color: grid } }, x: { ticks: { color: tick, font: { size: 11 } }, grid: { display: false } } } } });
        c2 = new Chart($("#chPri"), { type: "doughnut", data: { labels: d.by_priority.labels, datasets: [{ data: d.by_priority.values, backgroundColor: ["#C5D0DC", "#B3261E", "#D98A1B", "#087E80"], borderWidth: 2, borderColor: "#fff" }] }, options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom", labels: { color: "#142D4E", usePointStyle: true } } } } });
      } else { c1.data.datasets[0].data = d.by_status.values; c2.data.datasets[0].data = d.by_priority.values; c1.update(); c2.update(); }
      $("#attention").innerHTML = d.attention.length ? `<div class="table-responsive"><table class="table ec-table"><tbody>${d.attention.map(a => `<tr><td><b>${esc(a.name)}</b><div class="sub">${esc(a.code)} · waiting ${ago(a.arrived_at)}</div></td><td>${a.reasons.map(r => `<span class="miss-chip me-1 mb-1">${esc(r)}</span>`).join("")}</td><td class="text-end"><a class="btn btn-soft btn-sm" href="/staff/patients?open=${encodeURIComponent(a.code)}">Open</a></td></tr>`).join("")}</tbody></table></div>` : `<p class="text-muted mb-0"><i class="bi bi-check-circle text-success"></i> Nothing needs attention right now.</p>`;
      $("#capacity").innerHTML = d.wards.map(w => bar(w.free, w.total, w.ward + " beds")).join("") + d.resources.map(r => bar(r.available, r.total, r.name)).join("");
      $("#updated").textContent = "Updated " + EC.time(new Date().toISOString());
    }, 15000);
  }

  // =================================================================== patients
  function patients() {
    const oc = new bootstrap.Offcanvas("#detailOc"), role = $("#listCard").dataset.role;
    let sel = null, cur = null;
    const load = async () => {
      const p = new URLSearchParams({ q: $("#q").value, status: $("#fStatus").value, priority: $("#fPri").value });
      let d; try { d = await api("/staff/api/patients?" + p); } catch (e) { return; }
      $("#rows").innerHTML = d.patients.map(x => `<tr data-code="${esc(x.code)}" tabindex="0" class="${sel === x.code ? "sel" : ""}"><td class="ps-3"><b>${esc(x.name)}</b><div class="sub">${esc(x.code)} · ${x.age} yrs</div></td><td>${pri(x.priority)}</td><td>${pill(x.status)}</td><td>${x.bed ? esc(x.bed) : '<span class="text-muted">—</span>'}</td><td>${EC.time(x.arrived_at)}</td><td class="pe-3">${miss(x.missing)}</td></tr>`).join("") || `<tr><td colspan="6" class="text-center text-muted py-4">No patients match.</td></tr>`;
    };
    $("#q").addEventListener("input", EC.debounce(load)); $("#fStatus").addEventListener("change", load); $("#fPri").addEventListener("change", load);
    $("#rows").addEventListener("click", e => { const r = e.target.closest("tr[data-code]"); if (r) open(r.dataset.code); });
    $("#rows").addEventListener("keydown", e => { if (e.key === "Enter") { const r = e.target.closest("tr[data-code]"); if (r) open(r.dataset.code); } });
    poll(load, 20000);

    async function open(code) {
      sel = code; $$("#rows tr").forEach(r => r.classList.toggle("sel", r.dataset.code === code));
      try { cur = await api("/staff/api/patients/" + encodeURIComponent(code)); } catch (e) { return err(e); }
      render(cur); oc.show();
    }
    const q0 = new URLSearchParams(location.search).get("open"); if (q0) open(q0);

    function render(p) {
      const v = p.vitals, canPri = role === "clinician";
      $("#dTitle").textContent = p.name + ", " + p.age;
      $("#detail").innerHTML = `
      <div class="d-sec"><div class="d-flex gap-3 align-items-start"><img src="${esc(p.qr_url)}" alt="QR code for ${esc(p.code)}" width="84" height="84" class="rounded border">
        <div class="flex-grow-1"><div class="fw-bold fs-5">${esc(p.code)}</div><div class="mb-2">${pill(p.status)} ${pri(p.priority)}</div>
        <div class="sub">${esc(p.dept)} · arrived ${dt(p.arrived_at)}</div></div>
        <button class="btn btn-navy btn-sm" id="hoBtn"><i class="bi bi-arrow-left-right me-1"></i>Handover</button></div></div>
      ${p.missing_items.length ? `<div class="alert alert-warning py-2 mb-3"><b><i class="bi bi-exclamation-triangle me-1"></i>Missing information</b><div class="mt-1">${p.missing_items.map(m => `<span class="miss-chip me-1 mb-1">${esc(m.label)}${m.by === "patient" ? " (patient can add)" : ""}</span>`).join("")}</div></div>` : ""}
      <form id="upd">
      <div class="d-sec"><h3>Care coordination</h3><div class="row g-2">
        <div class="col-sm-6"><label class="form-label" for="u-st">Status</label><select class="form-select" id="u-st">${EC.STATUS.map((s, i) => `<option value="${i}" ${i === p.status ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        <div class="col-sm-6"><label class="form-label" for="u-pr">Priority (assigned by clinician)</label><select class="form-select" id="u-pr" ${canPri ? "" : "disabled"} aria-describedby="prHelp">${["Not set", "Immediate", "Urgent", "Standard"].map(s => `<option ${s === p.priority ? "selected" : ""}>${s}</option>`).join("")}</select>
          <div class="form-text" id="prHelp">${canPri ? (p.priority_by ? `Set by ${esc(p.priority_by)}` : "Not yet assigned") : "Only a clinician can assign priority."}</div></div>
        <div class="col-sm-6"><label class="form-label" for="u-dp">Department</label><select class="form-select" id="u-dp">${["Unassigned", "General", "Cardiology", "Orthopedics", "Pediatrics", "Surgery", "Neurology"].map(s => `<option ${s === p.dept ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        <div class="col-sm-6"><label class="form-label" for="u-bd">Bed</label><select class="form-select" id="u-bd"><option value="">No bed</option>${p.bed ? `<option value="${esc(p.bed)}" selected>${esc(p.bed)} (current)</option>` : ""}${p.beds_free.map(b => `<option value="${esc(b.code)}">${esc(b.code)} · ${b.ward}</option>`).join("")}</select></div></div></div>
      <div class="d-sec"><h3>Vitals <span class="text-lowercase fw-normal">(entered by staff${v.at ? ", " + dt(v.at) : ""})</span></h3><div class="row g-2">
        <div class="col-6 col-sm-3"><label class="form-label" for="v-hr">Pulse</label><input class="form-control" id="v-hr" type="number" min="20" max="250" value="${v.hr ?? ""}"></div>
        <div class="col-6 col-sm-3"><label class="form-label" for="v-bp">BP</label><input class="form-control" id="v-bp" placeholder="120/80" value="${esc(v.bp)}"></div>
        <div class="col-6 col-sm-3"><label class="form-label" for="v-sp">SpO₂ %</label><input class="form-control" id="v-sp" type="number" min="50" max="100" value="${v.spo2 ?? ""}"></div>
        <div class="col-6 col-sm-3"><label class="form-label" for="v-tp">Temp °F</label><input class="form-control" id="v-tp" type="number" step="0.1" value="${v.temp ?? ""}"></div></div></div>
      <div class="save-bar"><button class="btn btn-primary" type="submit"><i class="bi bi-check2-circle me-1"></i>Save update</button></div></form>
      <div class="d-sec mt-3"><h3>Reported by patient</h3><dl class="kv"><dt>Symptoms</dt><dd>${esc(p.symptoms)}</dd><dt>History</dt><dd>${esc(p.history) || '<span class="text-muted">Not provided</span>'}</dd><dt>Allergies</dt><dd>${esc(p.allergies) || '<span class="text-muted">Not provided</span>'}</dd>
        <dt>Phone</dt><dd>${esc(p.phone)}</dd><dt>Family contact</dt><dd>${esc(p.kin_phone) || '<span class="text-muted">Not provided</span>'}</dd>
        <dt>Family sharing</dt><dd>${p.consent ? '<i class="bi bi-check-circle text-success"></i> Patient consented (status only)' : '<i class="bi bi-slash-circle text-muted"></i> No consent'}</dd>
        <dt>Report</dt><dd>${p.report ? `<a href="/staff/api/patients/${esc(p.code)}/report"><i class="bi bi-file-earmark-medical me-1"></i>${esc(p.report.name)}</a>` : '<span class="text-muted">None uploaded</span>'}</dd></dl></div>
      <div class="d-sec"><h3>Status timeline</h3><ol class="tl">${p.timeline.map((e, i) => `<li class="${i === p.timeline.length - 1 ? "current" : "done"}"><span class="dot"><i class="bi bi-check-lg"></i></span><div class="t-title">${esc(EC.STATUS[e.status])}</div><div class="t-time">${dt(e.at)} · ${esc(e.by)}</div></li>`).join("")}</ol></div>`;
      $("#upd").addEventListener("submit", save); $("#hoBtn").addEventListener("click", () => handover(p.code));
    }
    async function save(e) {
      e.preventDefault();
      const body = { status: +$("#u-st").value, dept: $("#u-dp").value, bed: $("#u-bd").value, vitals: { hr: $("#v-hr").value, bp: $("#v-bp").value, spo2: $("#v-sp").value, temp: $("#v-tp").value } };
      if (role === "clinician") body.priority = $("#u-pr").value;
      try { const r = await api(`/staff/api/patients/${cur.code}/update`, { method: "POST", body }); cur = r.patient; render(cur); load(); toast(r.changed ? "Saved. The patient's page updates automatically." : "No changes to save", r.changed ? "success" : "info"); } catch (e2) { err(e2); }
    }

    // ---- handover snapshot
    let hoText = "";
    async function handover(code) {
      let h; try { h = await api(`/staff/api/patients/${code}/handover`); } catch (e) { return err(e); }
      const v = h.vitals, vit = [v.hr != null && `Pulse ${v.hr}`, v.bp && `BP ${v.bp}`, v.spo2 != null && `SpO₂ ${v.spo2}%`, v.temp != null && `Temp ${v.temp}°F`].filter(Boolean).join(" · ") || "Not recorded";
      const open = h.missing_items.map(m => m.label);
      const tl = h.timeline.map(e => `${dt(e.at)} ${EC.STATUS[e.status]}`);
      const prio = h.priority === "Not set" ? "Not yet assigned by staff" : `${h.priority} (assigned by ${h.priority_by || "staff"})`;
      hoText = [`HANDOVER SNAPSHOT: ${h.code}`, `Generated ${dt(h.generated_at)} by ${h.generated_by}`, "",
        `PATIENT: ${h.name}, ${h.age} yrs. Phone ${h.phone}. Family contact ${h.kin_phone || "not provided"}`, `ARRIVED: ${dt(h.arrived_at)}`,
        `REPORTED SYMPTOMS: ${h.symptoms}`, `HISTORY: ${h.history || "Not provided"}`, `ALLERGIES: ${h.allergies || "Not provided"}`,
        `VITALS (staff-entered${v.at ? ", " + dt(v.at) : ""}): ${vit}`, `STATUS: ${EC.STATUS[h.status]}`, `PRIORITY: ${prio}`, `DEPARTMENT: ${h.dept}   BED: ${h.bed || "None"}`,
        `OPEN ITEMS: ${open.length ? open.join("; ") : "None"}`, `TIMELINE: ${tl.join(" > ")}`, "",
        "Information organised from entered data. No diagnosis or clinical recommendation. Demo data is fictional."].join("\n");
      const sec = (t, body) => `<div class="ho-sec"><h5>${t}</h5>${body}</div>`;
      $("#handoverPrint").innerHTML = `<div class="ho"><div class="d-flex justify-content-between flex-wrap gap-2"><div><h4 class="mb-0">${esc(h.name)}, ${h.age} yrs</h4><div class="text-muted">${esc(h.code)} · ${esc(h.dept)} · Bed ${esc(h.bed || "none")}</div></div><div>${pill(h.status)} ${pri(h.priority)}</div></div>
        ${sec("Reported symptoms (patient)", `<p class="mb-0">${esc(h.symptoms)}</p>`)}
        ${sec("Background", `<p class="mb-1"><b>History:</b> ${esc(h.history) || "Not provided"}</p><p class="mb-0"><b>Allergies:</b> ${esc(h.allergies) || "Not provided"}</p>`)}
        ${sec("Vitals (entered by staff)", `<p class="mb-0">${esc(vit)}${v.at ? ` <span class="text-muted">· ${dt(v.at)}</span>` : ""}</p>`)}
        ${sec("Status and priority", `<p class="mb-0"><b>Status:</b> ${esc(EC.STATUS[h.status])}<br><b>Priority:</b> ${esc(prio)}</p>`)}
        ${sec("Open items", open.length ? open.map(o => `<span class="miss-chip me-1 mb-1">${esc(o)}</span>`).join("") : `<span class="text-success"><i class="bi bi-check-circle"></i> None</span>`)}
        ${sec("Timeline", `<ol class="tl mt-2">${h.timeline.map((e, i) => `<li class="${i === h.timeline.length - 1 ? "current" : "done"}"><span class="dot"><i class="bi bi-check-lg"></i></span><div class="t-title">${esc(EC.STATUS[e.status])}</div><div class="t-time">${dt(e.at)} · ${esc(e.by)}</div></li>`).join("")}</ol>`)}
        <p class="safe-note mt-3 mb-0">Generated ${dt(h.generated_at)} by ${esc(h.generated_by)}. Organised from entered data; not a diagnosis or clinical recommendation. Fictional demo data.</p></div>`;
      bootstrap.Modal.getOrCreateInstance("#handoverModal").show();
    }
    $("#hoCopy").addEventListener("click", () => navigator.clipboard.writeText(hoText).then(() => toast("Handover copied")).catch(() => toast("Copy not available", "warning")));
    $("#hoPrint").addEventListener("click", () => window.print());

    // ---- QR scanner (BarcodeDetector where supported; otherwise use search)
    let stream, raf;
    const stopScan = () => { cancelAnimationFrame(raf); if (stream) stream.getTracks().forEach(t => t.stop()); stream = null; };
    $("#scanModal").addEventListener("hidden.bs.modal", stopScan);
    $("#scanBtn").addEventListener("click", async () => {
      bootstrap.Modal.getOrCreateInstance("#scanModal").show();
      const msg = $("#scanMsg"), vid = $("#scanVideo");
      if (!("BarcodeDetector" in window) || !navigator.mediaDevices) { msg.textContent = "Camera scanning is not supported in this browser. Type or paste the patient ID in the search box instead."; return; }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }); vid.srcObject = stream; await vid.play();
        const det = new BarcodeDetector({ formats: ["qr_code"] });
        const tick = async () => { try { const r = await det.detect(vid); if (r.length) { const m = /EC360:(EC-\d+)/.exec(r[0].rawValue); if (m) { stopScan(); bootstrap.Modal.getInstance("#scanModal").hide(); open(m[1]); return; } } } catch (e) { /* retry */ } raf = requestAnimationFrame(tick); };
        tick();
      } catch (e) { msg.textContent = "Camera access was blocked. Allow the camera or search by ID instead."; }
    });
  }

  // =================================================================== resources
  function resources() {
    let data, modal;
    const draw = () => {
      const wards = ["Emergency", "ICU", "Ward"];
      $("#wardCards").innerHTML = wards.map(w => { const bs = data.beds.filter(b => b.ward === w && !b.out_of_service), free = bs.filter(b => !b.patient).length, out = data.beds.filter(b => b.ward === w && b.out_of_service).length, pc = bs.length ? free / bs.length * 100 : 0;
        return `<div class="col-md-4"><div class="ec-card"><div class="d-flex justify-content-between"><b>${w} beds</b><span class="fw-bold">${free}<span class="text-muted fw-normal"> / ${bs.length} free</span></span></div><div class="meter my-2 ${pc < 25 ? "low" : ""}"><i style="width:${pc}%"></i></div><div class="sub">${out ? out + " out of service" : "All beds in service"}</div></div></div>`; }).join("");
      $("#beds").innerHTML = wards.map(w => `<h3 class="h6 mt-3 mb-2 text-muted">${w}</h3><div class="bed-grid">${data.beds.filter(b => b.ward === w).map(b => `<button class="bed ${b.out_of_service ? "out" : b.patient ? "occ" : "free"}" data-id="${b.id}" type="button"><b>${esc(b.code)}</b><span>${b.out_of_service ? "Out of service" : b.patient ? esc(b.patient.first_name) + " · " + esc(b.patient.code) : "Available"}</span></button>`).join("")}</div>`).join("");
      $("#resCards").innerHTML = data.resources.map(r => `<div class="col-md-6"><div class="d-flex align-items-center gap-3 p-3 border rounded-3"><span class="icon-chip"><i class="bi bi-${esc(r.icon)}"></i></span><div class="flex-grow-1"><b>${esc(r.name)}</b><div class="sub">${r.available} available of ${r.total}</div></div>
        <div class="btn-group" role="group" aria-label="Adjust ${esc(r.name)}"><button class="btn btn-soft btn-sm" data-r="${r.id}" data-d="-1" aria-label="Decrease available ${esc(r.name)}"><i class="bi bi-dash-lg"></i></button><button class="btn btn-soft btn-sm" data-r="${r.id}" data-d="1" aria-label="Increase available ${esc(r.name)}"><i class="bi bi-plus-lg"></i></button></div></div></div>`).join("");
    };
    const load = async () => { try { data = await api("/staff/api/resources"); draw(); } catch (e) { /* handled */ } };
    $("#resCards").addEventListener("click", async e => { const b = e.target.closest("[data-r]"); if (!b) return; const r = data.resources.find(x => x.id == b.dataset.r); try { data = await api("/staff/api/resources/" + r.id, { method: "POST", body: { available: r.available + +b.dataset.d, total: r.total } }); draw(); } catch (e2) { err(e2); } });
    $("#beds").addEventListener("click", e => {
      const el = e.target.closest(".bed"); if (!el) return; const b = data.beds.find(x => x.id == el.dataset.id); modal = modal || new bootstrap.Modal("#bedModal");
      $("#bedTitle").textContent = "Bed " + b.code + " · " + b.ward;
      $("#bedBody").innerHTML = b.patient ? `<p><b>${esc(b.patient.first_name)}</b> (${esc(b.patient.code)}) is in this bed.</p><div class="d-flex gap-2"><button class="btn btn-primary" data-act="release">Release bed</button><a class="btn btn-soft" href="/staff/patients?open=${esc(b.patient.code)}">Open record</a></div>`
        : b.out_of_service ? `<p>This bed is out of service.</p><button class="btn btn-primary" data-act="service" data-out="0">Return to service</button>`
        : `<label class="form-label" for="bp">Assign a patient without a bed</label><select class="form-select mb-3" id="bp">${data.unassigned.map(p => `<option value="${esc(p.code)}">${esc(p.name)} (${esc(p.code)})</option>`).join("") || "<option value=''>No patients waiting for a bed</option>"}</select><div class="d-flex gap-2"><button class="btn btn-primary" data-act="assign" ${data.unassigned.length ? "" : "disabled"}>Assign bed</button><button class="btn btn-outline-secondary" data-act="service" data-out="1">Mark out of service</button></div>`;
      $("#bedBody").onclick = async ev => { const a = ev.target.closest("[data-act]"); if (!a) return; const body = { action: a.dataset.act, code: $("#bp") && $("#bp").value, out: a.dataset.out === "1" };
        try { data = await api("/staff/api/beds/" + b.id, { method: "POST", body }); modal.hide(); draw(); toast("Bed updated"); } catch (e2) { err(e2); } };
      modal.show();
    });
    poll(load, 20000);
  }

  // =================================================================== audit
  function auditLog() {
    const load = async () => {
      const p = new URLSearchParams({ q: $("#aq").value, action: $("#aAct").value });
      let d; try { d = await api("/staff/api/audit?" + p); } catch (e) { return; }
      $("#aRows").innerHTML = d.entries.map(x => `<tr><td class="ps-3 text-nowrap">${dt(x.at)}</td><td>${esc(x.actor)}${x.role ? `<div class="sub text-capitalize">${esc(x.role)}</div>` : ""}</td><td><span class="audit-act ${esc(x.action)}">${esc(x.action.replace("_", " "))}</span></td><td>${x.patient ? `<a href="/staff/patients?open=${esc(x.patient)}">${esc(x.patient)}</a>` : "—"}</td><td class="pe-3">${esc(x.detail)}</td></tr>`).join("") || `<tr><td colspan="5" class="text-center text-muted py-4">No entries.</td></tr>`;
    };
    $("#aq").addEventListener("input", EC.debounce(load)); $("#aAct").addEventListener("change", load); poll(load, 20000);
  }
})();
