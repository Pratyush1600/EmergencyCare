/* Shared helpers: CSRF-aware fetch, toasts, formatting. No secrets live in frontend code. */
(function () {
  const meta = document.querySelector('meta[name=csrf]');
  const EC = window.EC = {
    csrf: meta ? meta.content : "",
    STATUS: ["Registered", "Waiting for assessment", "Under assessment", "Treatment in progress", "Referred", "Discharged"],
    STATUS_HI: ["पंजीकृत", "जांच की प्रतीक्षा", "जांच जारी", "इलाज जारी", "रेफर किया गया", "छुट्टी दी गई"],
    $: (s, r = document) => r.querySelector(s),
    $$: (s, r = document) => [...r.querySelectorAll(s)],
    esc: s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),
    async api(url, opts = {}) {
      const o = { credentials: "same-origin", ...opts, headers: { ...(opts.headers || {}) } };
      if (o.body && !(o.body instanceof FormData)) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(o.body); }
      if ((o.method || "GET") !== "GET") o.headers["X-CSRF-Token"] = EC.csrf;
      const r = await fetch(url, o);
      let data = null; try { data = await r.json(); } catch (e) { /* non-JSON */ }
      if (r.status === 401 && url.startsWith("/staff")) { location.href = "/staff/login"; throw new Error("auth"); }
      if (!r.ok) { const e = new Error((data && data.error) || "Request failed"); e.status = r.status; e.data = data; throw e; }
      return data;
    },
    toast(msg, type = "success") {
      const wrap = document.getElementById("toasts"); if (!wrap) return;
      const el = document.createElement("div");
      el.className = `toast align-items-center text-bg-${type === "danger" ? "danger" : type === "info" ? "dark" : type === "warning" ? "warning" : "success"} border-0`;
      el.setAttribute("role", type === "danger" ? "alert" : "status");
      el.innerHTML = `<div class="d-flex"><div class="toast-body">${EC.esc(msg)}</div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
      wrap.appendChild(el);
      const t = new bootstrap.Toast(el, { delay: 3800 }); t.show();
      el.addEventListener("hidden.bs.toast", () => el.remove());
    },
    time: iso => iso ? new Date(iso).toLocaleTimeString(EC.loc || [], { hour: "2-digit", minute: "2-digit" }) : "",
    dt: iso => iso ? new Date(iso).toLocaleString(EC.loc || [], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "",
    ago(iso) {
      const m = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
      return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;
    },
    pill: (i, lang) => `<span class="pill s${i}">${EC.esc(lang === "hi" ? EC.STATUS_HI[i] : EC.STATUS[i])}</span>`,
    pri: p => `<span class="pri pri-${EC.esc(p)}">${EC.esc(p)}</span>`,
    debounce(fn, ms = 250) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
  };
})();
