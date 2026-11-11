/* Halaman tujuan tautan reset password: cek kode, lalu simpan password baru */
(async function () {
  await PC.renderNav();
  const $ = id => document.getElementById(id), form = $("form"), msg = $("msg");
  const kode = new URLSearchParams(location.search).get("kode");

  const gagal = pesan => {
    $("judul").innerHTML = "Tautan<br>tidak berlaku"; $("ket").textContent = "";
    $("isi").textContent = pesan; $("gagal").hidden = false; form.hidden = true;
  };
  if (!kode) return gagal("Tautan tidak lengkap. Buka tautan langsung dari email reset password.");
  try {
    if (!(await PC.api("/api/reset-password/cek?kode=" + encodeURIComponent(kode))).valid) return gagal("Tautan sudah kedaluwarsa atau sudah dipakai. Minta tautan baru.");
  } catch { return gagal("Tidak bisa memeriksa tautan. Coba lagi sebentar lagi."); }
  form.hidden = false;

  // tombol lihat/sembunyikan password
  form.querySelectorAll("input[type=password]").forEach(inp => {
    const w = document.createElement("div"); w.className = "pw"; inp.replaceWith(w);
    const b = document.createElement("button"); b.type = "button"; b.textContent = "Lihat"; b.setAttribute("aria-label", "Lihat atau sembunyikan password");
    b.onclick = () => { const show = inp.type === "password"; inp.type = show ? "text" : "password"; b.textContent = show ? "Tutup" : "Lihat"; };
    w.append(inp, b);
  });

  const RULES = [["8+ karakter", p => p.length >= 8], ["Huruf besar", p => /[A-Z]/.test(p)], ["Huruf kecil", p => /[a-z]/.test(p)], ["Angka", p => /\d/.test(p)]];
  const rules = $("rules"); rules.innerHTML = RULES.map(([t]) => `<span>${t}</span>`).join("");
  form.elements.password.addEventListener("input", e => RULES.forEach(([, f], i) => rules.children[i].classList.toggle("ok", f(e.target.value))));

  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const p = form.elements.password.value;
    if (!RULES.every(([, f]) => f(p))) { msg.textContent = "Password minimal 8 karakter dan harus gabungan huruf besar, huruf kecil, dan angka"; return; }
    if (p !== form.elements.password2.value) { msg.textContent = "Konfirmasi password tidak sama"; return; }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true; msg.textContent = "";
    try {
      await PC.post("/api/reset-password", { kode, password: p });
      PC.toast("Password berhasil diubah. Silakan masuk.");
      setTimeout(() => PC.go("/masuk"), 1200);
    } catch (e) { msg.textContent = e.message; btn.disabled = false; }
  });
})();
