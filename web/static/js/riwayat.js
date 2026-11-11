/* Riwayat: daftar sesi + grafik perkembangan skor */
(async function () {
  const me = await PC.renderNav("/riwayat");
  if (!me) return (location.href = "/masuk");
  const list = document.getElementById("list");
  const rows = await PC.api("/api/latihan");
  if (!rows.length) { list.innerHTML = `<div class="empty">Belum ada sesi latihan.<br><br><a class="btn solid" href="/latihan">Mulai latihan pertama</a></div>`; return; }

  const ASPEK = { orientasi: "Ori", gestur: "Ges", postur: "Pos", gerak: "Ger" };
  const mmss = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  const tgl = s => new Date(s.replace(" ", "T") + "Z").toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
  list.innerHTML = rows.map(r => `<button class="h-item" data-id="${r.id}"><div class="sc">${r.total}</div>
    <div class="meta"><b>${tgl(r.dibuat)}</b><br>Durasi ${mmss(r.durasi)} · sesi #${r.id}</div>
    <div class="mini">${Object.entries(r.skor).map(([k, v]) => `<span>${ASPEK[k]}<i style="width:${v}%"></i></span>`).join("")}</div></button>`).join("");
  list.onclick = async e => {
    const b = e.target.closest(".h-item"); if (!b) return;
    try { HasilModal.show(await PC.api("/api/latihan/" + b.dataset.id)); } catch (err) { PC.toast(err.message); }
  };

  if (rows.length >= 2) {  // grafik garis dari yang terlama ke terbaru
    document.getElementById("prog").hidden = false;
    const pts = rows.slice().reverse().map(r => r.total), n = pts.length;
    const xy = pts.map((v, i) => [20 + (560 * i) / (n - 1), 130 - v * 1.1]);
    document.getElementById("chart").innerHTML =
      `<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9b75f" stop-opacity=".35"/><stop offset="1" stop-color="#e9b75f" stop-opacity="0"/></linearGradient></defs>
       <path d="M${xy.map(p => p.join(",")).join(" L")} L${xy[n - 1][0]},140 L${xy[0][0]},140Z" fill="url(#ar)"/>
       <path d="M${xy.map(p => p.join(",")).join(" L")}" fill="none" stroke="#b98a3a" stroke-width="2.2" vector-effect="non-scaling-stroke"/>
       ${xy.map((p, i) => `<circle cx="${p[0]}" cy="${p[1]}" r="3.5" fill="#161616"/><text x="${p[0]}" y="${p[1] - 9}" font-size="10" text-anchor="middle" fill="#161616">${pts[i]}</text>`).join("")}`;
  }
})();
