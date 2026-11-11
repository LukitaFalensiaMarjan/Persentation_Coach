/* Lupa password: minta tautan reset lewat email (jawaban server selalu sama agar email terdaftar tidak bocor) */
(async function () {
  if (await PC.renderNav(location.pathname)) return PC.go("/");
  const form = document.getElementById("form"), msg = document.getElementById("msg");

  const kirim = email => PC.post("/api/lupa-password", { email });

  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const email = form.elements.email.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { msg.textContent = "Format email tidak valid"; return; }
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true; msg.textContent = "";
    try { await kirim(email); } catch (e) { msg.textContent = e.message; btn.disabled = false; return; }
    selesai(email);
  });

  function selesai(email) {
    form.replaceChildren();
    const h = document.createElement("h2"); h.className = "card-title"; h.textContent = "Cek emailmu";
    const p = document.createElement("p"); p.className = "note";
    const b = document.createElement("b"); b.textContent = email;
    p.append("Jika ", b, " terdaftar, kami baru saja mengirim tautan untuk membuat password baru. Tautan berlaku 1 jam. Cek juga folder spam.");
    const ulang = document.createElement("button"); ulang.type = "button"; ulang.className = "btn ghost";
    let t, n = 60;
    const hitung = () => {
      clearInterval(t); ulang.disabled = true; n = 60; ulang.textContent = `Kirim ulang dalam ${n} dtk`;
      t = setInterval(() => { ulang.textContent = `Kirim ulang dalam ${--n} dtk`; if (n <= 0) { clearInterval(t); ulang.textContent = "Kirim ulang tautan"; ulang.disabled = false; } }, 1000);
    };
    const s = document.createElement("p"); s.className = "hint"; s.style.margin = "10px 0 0";
    ulang.onclick = async () => {
      try { await kirim(email); s.className = "hint ok"; s.textContent = "Tautan dikirim ulang."; } catch (e) { s.className = "hint bad"; s.textContent = e.message; }
      hitung();
    };
    hitung();
    const alt = document.createElement("p"); alt.className = "alt"; alt.innerHTML = `<a href="/lupa-password">Salah email?</a> &nbsp;·&nbsp; <a href="/masuk">Kembali masuk</a>`;
    form.append(h, p, ulang, s, alt);
  }
})();
