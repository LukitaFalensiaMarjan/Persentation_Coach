/* Halaman profil */
(async function () {
  const me = await PC.renderNav("/profil");
  if (!me) return (location.href = "/masuk");
  const $ = id => document.getElementById(id), form = $("form"), msg = $("msg"), av = $("avatar");

  for (const k of ["nama", "username", "email", "hp", "alamat"]) form.elements[k].value = me[k] || "";
  const paint = url => {
    av.style.backgroundImage = url ? `url("${url}")` : "";
    av.textContent = url ? "" : (me.nama || me.username)[0].toUpperCase();
  };
  paint(me.foto ? "/uploads/" + me.foto : "");

  form.elements.username.addEventListener("input", e => { e.target.value = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""); });
  $("pickFoto").onclick = () => form.elements.foto.click();
  form.elements.foto.onchange = e => {
    const f = e.target.files[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) { e.target.value = ""; msg.className = "msg"; msg.textContent = "Foto maks 2 MB"; return; }
    paint(URL.createObjectURL(f));
  };

  // ---------- Telegram ----------
  async function tgRefresh() {
    const s = await PC.api("/api/telegram/status");
    $("tgState").textContent = !s.dikonfigurasi ? "Bot belum dikonfigurasi di server (TELEGRAM_BOT_TOKEN kosong)." : s.terhubung ? "Terhubung. Laporan bisa dikirim ke Telegram-mu." : "Belum terhubung.";
    $("tgConnect").hidden = !s.dikonfigurasi || s.terhubung; $("tgOff").hidden = !s.terhubung;
    if (s.terhubung) $("tgBox").classList.remove("on");
  }
  $("tgConnect").onclick = async () => {
    try {
      const t = await PC.api("/api/telegram/tautan");
      $("tgBox").classList.add("on"); $("tgQr").innerHTML = "";
      if (window.QRCode) new QRCode($("tgQr"), { text: t.url, width: 120, height: 120 });
      const a = document.createElement("a"); a.href = t.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = "buka tautan";
      $("tgTxt").textContent = "Pindai QR ini atau "; $("tgTxt").append(a, " lalu tekan Start di Telegram. Setelah itu muat ulang halaman ini.");
    } catch (e) { PC.toast(e.message); }
  };
  $("tgOff").onclick = async () => { await PC.api("/api/telegram/putus", { method: "POST" }); tgRefresh(); };
  tgRefresh();

  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true; msg.textContent = "";
    try {
      await PC.api("/api/profil", { method: "PUT", body: new FormData(form) });
      msg.className = "msg ok"; msg.textContent = "Profil tersimpan";
      setTimeout(() => location.reload(), 700);
    } catch (e) { msg.className = "msg"; msg.textContent = e.message; btn.disabled = false; }
  });
})();
