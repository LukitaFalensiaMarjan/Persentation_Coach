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

  const ICONS = {
    home: `<svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    cam: `<svg viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
    chart: `<svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    user: `<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    chat: `<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
    menu: `<svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
    close: `<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`
  };

  /* active: href halaman ini (mis. "/masuk"), atau null di landing (diatur lewat setActive) */
  async function renderNav(active = null) {
    const me = await getMe();
    const nav = document.getElementById("nav");
    if (!nav) return me;
    const center = LINKS.map(([t, k]) => `<a href="/#${k}" data-k="${k}">${t}</a>`).join("");
    nav.innerHTML = `
      <a class="logo" href="/#0" data-k="0">${LOGO}<span>PERSENTATION COACH</span></a>
      <nav class="nav-center" aria-label="Menu utama">${center}</nav>
      <div class="nav-right"></div>
      <button type="button" class="nav-toggle" id="navToggle" aria-label="Buka menu navigasi" aria-expanded="false">${ICONS.menu}</button>
    `;
    const right = nav.querySelector(".nav-right");
    let drawerContent = "";

    if (me) {
      const a = document.createElement("a");
      a.className = "me"; a.href = "/profil";
      const av = document.createElement(me.foto ? "img" : "i");
      if (me.foto) { av.src = "/uploads/" + me.foto; av.alt = ""; }
      const nameSpan = document.createElement("span");
      nameSpan.textContent = me.nama || me.username;
      a.append(av, nameSpan);
      const out = document.createElement("button");
      out.className = "lnk"; out.title = "Keluar"; out.setAttribute("aria-label", "Keluar");
      out.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>`;
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

      // Drawer untuk user login
      drawerContent = `
        <div class="nd-head">
          <img class="nd-avatar" src="${me.foto ? '/uploads/' + me.foto : 'data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'%23888\'><circle cx=\'12\' cy=\'8\' r=\'4\'/><path d=\'M4 20c0-4 4-6 8-6s8 2 8 6\'/></svg>'}" alt="">
          <div class="nd-user">
            <b>${me.nama || me.username}</b>
            <small>@${me.username}</small>
          </div>
        </div>
        <div class="nd-links">
          <a href="/#0" class="nd-item">${ICONS.home}<span>Beranda</span></a>
          <a href="/latihan" class="nd-item">${ICONS.cam}<span>Latihan</span></a>
          <a href="/riwayat" class="nd-item">${ICONS.chart}<span>Riwayat</span></a>
          <a href="/profil" class="nd-item">${ICONS.user}<span>Profil Saya</span></a>
          <a href="#chat" class="nd-item nd-chat">${ICONS.chat}<span>Tanya Chatbot</span></a>
          <div class="nd-sep"></div>
          <a href="/#1" class="nd-item" data-k="1"><span>Tentang</span></a>
          <a href="/#2" class="nd-item" data-k="2"><span>Fitur</span></a>
          <a href="/#3" class="nd-item" data-k="3"><span>Cara Kerja</span></a>
        </div>
        <div class="nd-auth">
          <button type="button" class="btn ghost nd-logout" style="width:100%">Keluar Akun</button>
        </div>
      `;
    } else {
      right.innerHTML = `<a href="/masuk">MASUK</a><a href="/daftar">DAFTAR</a>`;
      drawerContent = `
        <div class="nd-links" style="margin-top:10px">
          <a href="/#0" class="nd-item" data-k="0">${ICONS.home}<span>Beranda</span></a>
          <a href="/#1" class="nd-item" data-k="1"><span>Tentang</span></a>
          <a href="/#2" class="nd-item" data-k="2"><span>Fitur</span></a>
          <a href="/#3" class="nd-item" data-k="3"><span>Cara Kerja</span></a>
          <div class="nd-sep"></div>
          <a href="/masuk" class="nd-item">${ICONS.user}<span>Masuk</span></a>
          <a href="/daftar" class="nd-item">${ICONS.chat}<span>Daftar Akun</span></a>
        </div>
        <div class="nd-auth">
          <a href="/masuk" class="btn solid">Masuk</a>
          <a href="/daftar" class="btn ghost">Daftar Akun Baru</a>
        </div>
      `;
    }

    // Hapus navigasi bawah lama jika masih ada di DOM
    document.getElementById("mobileBar")?.remove();

    // Pasang Drawer ke body jika belum ada
    let drawer = document.getElementById("navDrawer");
    if (!drawer) {
      drawer = document.createElement("div");
      drawer.id = "navDrawer";
      drawer.className = "nav-drawer";
      document.body.append(drawer);
    }
    drawer.innerHTML = `
      <div class="nav-drawer-box">
        <button type="button" class="nd-close" id="ndClose" aria-label="Tutup menu">${ICONS.close}</button>
        ${drawerContent}
      </div>
    `;

    // Pasang listener drawer
    const toggleBtn = nav.querySelector("#navToggle");
    const closeBtn = drawer.querySelector("#ndClose");
    const closeDrawer = () => { drawer.classList.remove("open"); toggleBtn?.classList.remove("open"); };
    toggleBtn?.addEventListener("click", () => {
      drawer.classList.toggle("open");
      toggleBtn.classList.toggle("open");
    });
    closeBtn?.addEventListener("click", closeDrawer);
    drawer.addEventListener("click", e => { if (e.target === drawer) closeDrawer(); });
    drawer.querySelectorAll("a").forEach(a => a.addEventListener("click", e => {
      closeDrawer();
      if (a.dataset.k != null && location.pathname === "/") {
        e.preventDefault();
        location.hash = "#" + a.dataset.k;
      }
    }));
    drawer.querySelector(".nd-logout")?.addEventListener("click", async () => {
      closeDrawer();
      await api("/api/keluar", { method: "POST" });
      go("/");
    });

    if (active) nav.querySelectorAll(`[href="${active}"]`).forEach(el => el.classList.add("on"));
    return me;
  }

  const setActive = k => {
    document.querySelectorAll("#nav .nav-center [data-k], #navDrawer [data-k]").forEach(el => el.classList.toggle("on", el.dataset.k == k));
  };

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
