/* Pop-up hasil latihan (dipakai di /latihan dan /riwayat). HasilModal.show(hasil) */
const HasilModal = (() => {
  const NAMA = { netral: "Netral", gestur_aktif: "Gestur aktif", menunjuk_slide: "Menunjuk slide", menunduk: "Menunduk", membelakangi: "Membelakangi", tangan_terlipat: "Tangan terlipat", tangan_tersembunyi: "Tangan tersembunyi" };
  const ASPEK = { orientasi: "Orientasi ke audiens", gestur: "Gestur", postur: "Postur kepala", gerak: "Pergerakan" };
  const BURUK = new Set(["menunduk", "membelakangi", "tangan_terlipat", "tangan_tersembunyi"]);
  const mmss = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
  const verdict = t => (t >= 80 ? "Sangat baik" : t >= 65 ? "Baik" : t >= 50 ? "Cukup" : "Perlu banyak latihan");
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const bar = (label, val, dark) => `<div class="bar"><div class="t"><span>${label}</span><span>${val}</span></div><div class="track"><div class="fill ${dark ? "dark" : ""}" data-w="${Math.min(100, parseFloat(val))}"></div></div></div>`;

  function show(h, { onClose } = {}) {
    const C = 2 * Math.PI * 80;
    const props = Object.entries(h.proporsi).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
    const tl = h.timeline.length
      ? h.timeline.map(([a, b, l]) => `<li><time>${mmss(a)} – ${mmss(b)}</time>${esc(NAMA[l] || l)}</li>`).join("")
      : `<li>Tidak ada momen yang perlu diperbaiki. Bagus!</li>`;
    const m = el("div", "modal");
    m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true"); m.setAttribute("aria-label", "Hasil latihan");
    m.innerHTML = `<div class="box"><div class="res-grid">
      <div>
        <div class="ring"><svg viewBox="0 0 190 190"><circle class="bg" cx="95" cy="95" r="80" fill="none" stroke-width="10"/><circle class="fg" cx="95" cy="95" r="80" fill="none" stroke-width="10" stroke-dasharray="${C}" stroke-dashoffset="${C}"/></svg><b>${h.total}</b><small>dari 100</small></div>
        <div class="verdict">${verdict(h.total)}</div>
        ${Object.entries(h.skor).map(([k, v]) => bar(ASPEK[k], v)).join("")}
        <p class="lead" style="font-size:11.5px;margin-top:10px">Durasi ${mmss(h.durasi_aktual)} dari target ${mmss(h.durasi_target || h.durasi_aktual)}.</p>
      </div>
      <div>
        <div class="sec">Proporsi gestur</div>
        ${props.map(([k, v]) => bar(NAMA[k], v.toFixed(0) + "%", BURUK.has(k))).join("")}
        <div class="sec">Momen yang perlu diperbaiki</div><ul class="tl">${tl}</ul>
        <div class="sec">Saran utama</div><ol class="advice">${h.saran.map(s => `<li>${esc(s)}</li>`).join("")}</ol>
      </div></div>
      <div class="tg-box" id="tgBox"><div class="qr" id="tgQr"></div><p id="tgTxt"></p></div>
      <div class="actions">
        <a class="btn ghost" href="/api/latihan/${h.id}/pdf" download>Unduh PDF</a>
        <button class="btn ghost" id="tgBtn">Kirim ke Telegram</button>
        <a class="btn ghost" href="/riwayat">Riwayat</a>
        <button class="btn solid" id="closeBtn">Selesai</button>
      </div></div>`;
    document.body.append(m);
    requestAnimationFrame(() => {
      m.classList.add("show");
      m.querySelector(".fg").style.strokeDashoffset = C * (1 - h.total / 100);
      m.querySelectorAll(".fill").forEach(f => (f.style.width = f.dataset.w + "%"));
    });
    const close = () => { m.classList.remove("show"); setTimeout(() => m.remove(), 350); document.removeEventListener("keydown", onKey); onClose && onClose(); };
    const onKey = e => e.key === "Escape" && close();
    document.addEventListener("keydown", onKey);
    m.addEventListener("click", e => e.target === m && close());
    m.querySelector("#closeBtn").onclick = close;
    m.querySelector("#tgBtn").onclick = async e => {
      const b = e.currentTarget; b.disabled = true;
      try {
        await PC.post(`/api/latihan/${h.id}/telegram`, {});
        PC.toast("Laporan terkirim ke Telegram");
      } catch (err) {
        if (err.status === 409) await tautkan(m);
        else PC.toast(err.message);
      }
      b.disabled = false;
    };
    m.querySelector(".btn.solid").focus({ preventScroll: true });
    return m;
  }

  // akun Telegram belum terhubung: tampilkan QR deep link t.me/<bot>?start=<kode>
  async function tautkan(m) {
    try {
      const t = await PC.api("/api/telegram/tautan");
      const box = m.querySelector("#tgBox"), qr = m.querySelector("#tgQr");
      box.classList.add("on"); qr.innerHTML = "";
      if (window.QRCode) new QRCode(qr, { text: t.url, width: 120, height: 120, correctLevel: QRCode.CorrectLevel.M });
      m.querySelector("#tgTxt").innerHTML = `Hubungkan akun Telegram dulu: pindai QR ini atau <a href="${esc(t.url)}" target="_blank" rel="noopener">buka tautan</a>, tekan <b>Start</b>, lalu klik "Kirim ke Telegram" lagi.`;
    } catch (err) { PC.toast(err.message); }
  }
  return { show };
})();
