/* Popup chatbot konsultasi. Dibuka dari ikon chat di navbar atau tombol bulat melayang; ditutup dengan tombol X, tombol Esc, atau ikon chat lagi. */
(function () {
  const SUGG = ["Kenapa skor gestur saya rendah?", "Bagaimana mengatasi gugup?", "Bantu hubungkan Telegram"];
  const I = {
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12l16-8-6 16-3-7-7-1z"/></svg>',
  };
  let root, log, sugg, input, loaded = false, isOpen = false;

  const add = (peran, teks) => {
    const d = document.createElement("div");
    d.className = "cp-b " + peran; d.textContent = teks;  // textContent: jawaban model tidak dirender sebagai HTML
    log.append(d); log.scrollTop = log.scrollHeight; return d;
  };

  function build() {
    root = document.createElement("section");
    root.className = "chat-pop"; root.hidden = true;
    root.setAttribute("role", "dialog"); root.setAttribute("aria-label", "Chatbot konsultasi presentasi");
    root.innerHTML = `<header class="cp-head"><div class="cp-ttl"><b>Pelatih Presentasi</b><span>Tanya seputar presentasi dan hasil latihanmu</span></div>
      <button class="cp-ico" data-a="clear" title="Hapus percakapan" aria-label="Hapus percakapan">${I.trash}</button>
      <button class="cp-ico" data-a="close" title="Tutup" aria-label="Tutup chat">${I.x}</button></header>
      <div class="cp-log" aria-live="polite"></div>
      <div class="cp-sugg">${SUGG.map(s => `<button type="button">${s}</button>`).join("")}</div>
      <form class="cp-in"><input maxlength="500" placeholder="Tulis pertanyaanmu…" autocomplete="off" aria-label="Pertanyaan"><button class="cp-send" aria-label="Kirim">${I.send}</button></form>`;
    document.body.append(root);
    log = root.querySelector(".cp-log"); sugg = root.querySelector(".cp-sugg"); input = root.querySelector("input");

    root.querySelector('[data-a="close"]').onclick = close;
    root.querySelector('[data-a="clear"]').onclick = async () => {
      await PC.api("/api/chat", { method: "DELETE" }); log.innerHTML = ""; add("sys", "Percakapan dihapus."); sugg.hidden = false;
    };
    sugg.onclick = e => e.target.tagName === "BUTTON" && kirim(e.target.textContent);
    root.querySelector("form").onsubmit = e => { e.preventDefault(); kirim(input.value); };
  }

  async function kirim(teks) {
    teks = teks.trim(); if (!teks) return;
    add("user", teks); input.value = ""; sugg.hidden = true;
    const tunggu = add("bot", "…");
    try {
      const r = await PC.post("/api/chat", { pesan: teks });
      tunggu.textContent = r.jawab;
      if (r.aksi === "telegram") tautan();
    } catch (e) { tunggu.textContent = e.status === 401 ? "Sesi berakhir, silakan masuk lagi." : "Maaf, terjadi kesalahan. Coba lagi."; }
    log.scrollTop = log.scrollHeight;
  }

  const muatQR = () => window.QRCode ? Promise.resolve() : new Promise((ok, gagal) => {
    const s = document.createElement("script"); s.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
    s.onload = ok; s.onerror = gagal; document.head.append(s);
  });
  let polling = 0;
  // tampilkan QR deep link di dalam chat, lalu pantau sampai akun Telegram terhubung (maks 5 menit)
  async function tautan() {
    try {
      const t = await PC.api("/api/telegram/tautan");
      const b = add("bot", ""); b.style.display = "flex"; b.style.gap = "12px"; b.style.alignItems = "center";
      const qr = document.createElement("div"); qr.style.cssText = "background:#fff;padding:6px;border-radius:8px;flex:none";
      const a = document.createElement("a"); a.href = t.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "Buka di Telegram";
      a.style.cssText = "text-decoration:underline;text-decoration-color:var(--gold);text-underline-offset:3px";
      b.append(qr, a);
      try { await muatQR(); new QRCode(qr, { text: t.url, width: 104, height: 104 }); } catch { qr.remove(); }
      log.scrollTop = log.scrollHeight;
      clearInterval(polling); const mulai = Date.now();
      polling = setInterval(async () => {
        if (Date.now() - mulai > 300000) return clearInterval(polling);
        try {
          if ((await PC.api("/api/telegram/status")).terhubung) {
            clearInterval(polling); add("bot", "Telegram berhasil terhubung! Cek chat bot-nya, panduan perintah sudah dikirim.");
          }
        } catch { /* coba lagi pada putaran berikutnya */ }
      }, 3000);
    } catch (e) { add("sys", e.message); }
  }

  async function open() {
    if (!root) build();
    isOpen = true; root.hidden = false;
    setTimeout(() => root.classList.add("show"), 20);  // setelah hidden dilepas agar transisi berjalan
    if (!loaded) {
      loaded = true;
      try {
        const h = await PC.api("/api/chat");
        add("sys", h.llm ? "Halo! Tanyakan seputar presentasi dan hasil latihanmu." : "Halo! Mode dasar aktif (LLM belum dikonfigurasi): jawaban dari basis tips dan datamu.");
        h.pesan.forEach(m => add(m.peran, m.isi));
        sugg.hidden = h.pesan.length > 0;
      } catch { add("sys", "Gagal memuat percakapan."); }
    }
    input.focus({ preventScroll: true });
  }
  function close() {
    if (!root || !isOpen) return;
    isOpen = false; root.classList.remove("show");
    setTimeout(() => { if (!isOpen) root.hidden = true; }, 700);  // tunggu animasi tutup selesai
  }

  document.addEventListener("click", e => {
    if (e.target.closest(".chat-fab, .chat-ico")) { e.preventDefault(); isOpen ? close() : open(); }
  });
  document.addEventListener("keydown", e => e.key === "Escape" && close());
})();
