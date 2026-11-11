/* Persentation Coach — helper bersama: API, navbar, toast */
const PC = (() => {
  const LINKS = [["BERANDA", 0], ["TENTANG", 1], ["FITUR", 2], ["CARA KERJA", 3]];
  const LOGO = `<svg viewBox="0 0 28 24" fill="none" stroke="currentColor" stroke-width=".95" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.8 5A10.5 10.5 0 1 0 21.8 19M20.3 6.3A8.5 8.5 0 1 0 20.3 17.7M21.8 5L20.3 6.3M21.8 19L20.3 17.7"/><path d="M8 18V6h2.2M8 18h2.2M10.2 18v-5.6M10.2 6a3.2 3.2 0 0 1 0 6.4M10.2 8a1.2 1.2 0 0 1 0 2.4z"/><circle cx="17" cy="9" r="1.2"/><path d="M17 10.2V14.8M17 14.8l-1.5 3.2M17 14.8l1.5 3.2M17 11.5l2.6-1.2"/></svg>`;

  const CHAT_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-8l-5 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/><circle cx="8.5" cy="11" r=".6" fill="currentColor"/><circle cx="12" cy="11" r=".6" fill="currentColor"/><circle cx="15.5" cy="11" r=".6" fill="currentColor"/></svg>`;

  async function api(path, opts = {}) {
    const r = await fetch(path, { credentials: "same-origin", ...opts });
    let data = null;
    try { data = await r.json(); } catch { /* respons tanpa body */ }
    if (!r.ok) {
      const d = data && data.detail;
      throw Object.assign(new Error(typeof d === "string" ? d : "Data yang dimasukkan tidak valid"), { status: r.status });
    }
    return data;
  }
  const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  let mePromise;
  const getMe = () => (mePromise ??= api("/api/saya").catch(() => null));

  function toast(msg) {
    let t = document.querySelector(".toast");
    if (!t) { t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); document.body.append(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2600);
  }

  /* active: href halaman ini (mis. "/masuk"), atau null di landing (diatur lewat setActive) */
  async function renderNav(active = null) {
    const me = await getMe();
    const nav = document.getElementById("nav");
    const center = LINKS.map(([t, k]) => `<a href="/#${k}" data-k="${k}">${t}</a>`).join("");
    nav.innerHTML = `<a class="logo" href="/#0" data-k="0">${LOGO}<span>PERSENTATION COACH</span></a>
      <nav class="nav-center" aria-label="Menu utama">${center}</nav><div class="nav-right"></div>`;
    const right = nav.querySelector(".nav-right");
    if (me) {
      const a = document.createElement("a");
      a.className = "me"; a.href = "/profil";
      const av = document.createElement(me.foto ? "img" : "i");
      if (me.foto) { av.src = "/uploads/" + me.foto; av.alt = ""; }
      a.append(av, document.createTextNode(me.nama || me.username));
      const out = document.createElement("button");
      out.className = "lnk"; out.textContent = "KELUAR";
      out.onclick = async () => { await api("/api/keluar", { method: "POST" }); go("/"); };
      // LATIHAN dan RIWAYAT menyatu dengan menu utama (satu baris, jarak sama)
      nav.querySelector(".nav-center").insertAdjacentHTML("beforeend", `<a href="/latihan">LATIHAN</a><a href="/riwayat">RIWAYAT</a>`);
      const chat = document.createElement("a");
      chat.className = "chat-ico"; chat.href = "#chat"; chat.title = "Chatbot konsultasi"; chat.setAttribute("aria-label", "Chatbot konsultasi"); chat.innerHTML = CHAT_ICON;
      const acct = document.createElement("div"); acct.className = "acct"; acct.append(chat, a);  // ikon chat menempel di foto profil
      right.append(acct, out);
      if (!document.getElementById("chatpop-js")) {  // popup chatbot dimuat hanya untuk user yang sudah masuk
        const l = document.createElement("link"); l.rel = "stylesheet"; l.href = "/static/css/chatpop.css";
        const s = document.createElement("script"); s.id = "chatpop-js"; s.src = "/static/js/chatpop.js";
        document.head.append(l, s);
      }
      if (!document.querySelector(".chat-fab")) {
        const fab = document.createElement("a");
        fab.className = "chat-fab"; fab.href = "#chat"; fab.title = "Tanya chatbot"; fab.setAttribute("aria-label", "Tanya chatbot"); fab.innerHTML = CHAT_ICON;
        document.body.append(fab);
      }
    } else {
      right.innerHTML = `<a href="/masuk">MASUK</a><a href="/daftar">DAFTAR</a>`;
    }
    if (active) nav.querySelectorAll(`[href="${active}"]`).forEach(el => el.classList.add("on"));
    return me;
  }
  const setActive = k => document.querySelectorAll("#nav .nav-center [data-k]").forEach(el => el.classList.toggle("on", el.dataset.k == k));

  // transisi keluar: tirai naik menutupi halaman, baru pindah (tirai masuk dimainkan CSS di halaman tujuan)
  function go(url) {
    const f = document.querySelector(".frame");
    if (!f || matchMedia("(prefers-reduced-motion: reduce)").matches) { location.href = url; return; }
    if (f.classList.contains("leaving")) return;
    f.classList.add("leaving");
    setTimeout(() => { location.href = url; }, 620);
  }
  document.addEventListener("click", e => {
    if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest("a[href]");
    if (!a || a.target || a.hasAttribute("download")) return;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin || /^\/(api|static|uploads)\//.test(u.pathname)) return;
    if (u.pathname === location.pathname && (u.hash || a.getAttribute("href").startsWith("#"))) return;  // hanya pindah hash di halaman yang sama
    e.preventDefault(); go(u.href);
  });
  addEventListener("pageshow", e => { if (e.persisted) document.querySelector(".frame")?.classList.remove("leaving"); });  // tombol back

  return { api, post, getMe, toast, renderNav, setActive, go };
})();
