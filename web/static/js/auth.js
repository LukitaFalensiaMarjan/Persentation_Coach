/* Halaman masuk & daftar */
(async function () {
  if (await PC.renderNav(location.pathname)) return PC.go("/");
  const form = document.getElementById("form"), msg = document.getElementById("msg");
  const isDaftar = location.pathname === "/daftar";

  // tombol lihat/sembunyikan password
  form.querySelectorAll("input[type=password]").forEach(inp => {
    const w = document.createElement("div"); w.className = "pw"; inp.replaceWith(w);
    const b = document.createElement("button"); b.type = "button"; b.textContent = "Lihat"; b.setAttribute("aria-label", "Lihat atau sembunyikan password");
    b.onclick = () => { const show = inp.type === "password"; inp.type = show ? "text" : "password"; b.textContent = show ? "Tutup" : "Lihat"; };
    w.append(inp, b);
  });

  // username selalu huruf kecil; di halaman daftar cek ketersediaan + aturan password langsung saat mengetik
  const uname = form.elements.username;
  uname.addEventListener("input", () => { uname.value = uname.value.toLowerCase().replace(/[^a-z0-9_]/g, ""); });
  const PW_RULES = [["8+ karakter", p => p.length >= 8], ["Huruf besar", p => /[A-Z]/.test(p)], ["Huruf kecil", p => /[a-z]/.test(p)], ["Angka", p => /\d/.test(p)]];
  const pwOk = p => PW_RULES.every(([, f]) => f(p));
  if (isDaftar) {
    const hint = document.createElement("p"); hint.className = "hint"; form.elements.username.closest(".row2").after(hint);
    const rules = document.createElement("div"); rules.className = "rules"; form.elements.password.closest(".row2").after(rules);
    rules.innerHTML = PW_RULES.map(([t]) => `<span>${t}</span>`).join("");
    form.elements.password.addEventListener("input", e => PW_RULES.forEach(([, f], i) => rules.children[i].classList.toggle("ok", f(e.target.value))));
    let t, seq = 0;
    uname.addEventListener("input", () => {
      clearTimeout(t); hint.textContent = ""; hint.className = "hint";
      if (uname.value.length < 3) return;
      const mine = ++seq;
      t = setTimeout(async () => {
        try {
          const r = await PC.api("/api/username/" + encodeURIComponent(uname.value));
          if (mine !== seq) return;
          hint.textContent = r.tersedia ? "Username tersedia" : "Username sudah dipakai";
          hint.className = "hint " + (r.tersedia ? "ok" : "bad");
        } catch { /* cek ketersediaan opsional; server tetap memvalidasi saat daftar */ }
      }, 350);
    });
  }

  const fail = e => { msg.className = "msg"; msg.textContent = e.message; };
  const done = () => PC.go("/");

  form.addEventListener("submit", async ev => {
    ev.preventDefault();
    const d = Object.fromEntries(new FormData(form));
    if (isDaftar && !pwOk(d.password)) return fail(new Error("Password minimal 8 karakter dan harus gabungan huruf besar, huruf kecil, dan angka"));
    if (isDaftar && d.password !== d.password2) return fail(new Error("Konfirmasi password tidak sama"));
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true; msg.textContent = "";
    try {
      const r = await PC.post(isDaftar ? "/api/daftar" : "/api/masuk",
        isDaftar ? { nama: d.nama, username: d.username, email: d.email, password: d.password } : { username: d.username, password: d.password });
      if (r && r.perlu_verifikasi) return tampilVerifikasi(r);
      done();
    } catch (e) {
      fail(e); btn.disabled = false;
      // jika terkena batas percobaan login (429), kunci tombol dan tampilkan hitung mundur
      if (!isDaftar && e.status === 429) {
        btn.disabled = true;
        const m = e.message.match(/(\d+)\s*detik/);
        let sisa = m ? parseInt(m[1], 10) : 60;
        const teksAsli = btn.textContent;
        clearInterval(btn._t);
        btn.textContent = `Terkunci (${sisa}s)`;
        btn._t = setInterval(() => {
          sisa--;
          if (sisa > 0) {
            btn.textContent = `Terkunci (${sisa}s)`;
          } else {
            clearInterval(btn._t);
            btn.disabled = false;
            btn.textContent = teksAsli;
          }
        }, 1000);
      }
      // akun ada tapi email belum diverifikasi: satu tombol kirim ulang saja (jeda 60 dtk-nya tetap berjalan walau tombol Masuk ditekan lagi)
      if (!isDaftar && e.status === 403) {
        ulangData.username = d.username;
        if (!ulang) { ulang = tombolUlang(ulangData); msg.after(ulang); }
      } else if (ulang) { ulang.remove(); ulang = null; }
    }
  });
  let ulang = null; const ulangData = {};

  // tombol kirim ulang email verifikasi (jeda 60 detik sesuai batas server)
  function tombolUlang(payload, awal = false) {
    const b = document.createElement("button"); b.type = "button"; b.className = "btn ghost"; b.textContent = "Kirim ulang email verifikasi";
    const s = document.createElement("p"); s.className = "hint"; s.style.margin = "10px 0 0";
    let t;
    const hitung = n => {  // jeda 60 detik sesuai batas server, ditampilkan di tombol
      clearInterval(t); b.disabled = true; b.textContent = `Kirim ulang dalam ${n} dtk`;
      t = setInterval(() => { b.textContent = `Kirim ulang dalam ${--n} dtk`; if (n <= 0) { clearInterval(t); b.textContent = "Kirim ulang email verifikasi"; b.disabled = false; } }, 1000);
    };
    b.onclick = async () => {
      b.disabled = true; s.className = "hint"; s.textContent = "Mengirim…";
      try {
        const r = await PC.post("/api/verifikasi/ulang", payload);
        s.className = "hint " + (r.terkirim ? "ok" : "bad");
        s.textContent = r.terkirim ? "Email verifikasi dikirim ulang. Cek kotak masuk dan folder spam." : "Email gagal dikirim. Periksa pengaturan SMTP di server (detail ada di konsol server).";
        hitung(60);
      } catch (e) {
        s.className = "hint bad"; s.textContent = e.message;
        e.status === 429 ? hitung(60) : (b.disabled = false);
      }
    };
    if (awal) hitung(60);  // email pertama baru dikirim: tombol aktif lagi setelah 60 detik
    const w = document.createElement("div"); w.append(b, s);
    return w;
  }
  function tampilVerifikasi(r) {
    form.replaceChildren();
    const h = document.createElement("h2"); h.className = "card-title"; h.textContent = "Cek emailmu";
    const p = document.createElement("p"); p.className = "note";
    const b = document.createElement("b"); b.textContent = r.email;
    p.append(r.terkirim ? "Kami mengirim tautan verifikasi ke " : "Akun dibuat, tetapi email belum bisa dikirim (SMTP server belum dikonfigurasi; tautan dicetak di konsol server). Tujuan: ", b,
      ". Buka tautan itu (berlaku 24 jam) untuk mengaktifkan akunmu. Cek juga folder spam.");
    const alt = document.createElement("p"); alt.className = "alt";
    alt.innerHTML = `<a href="/daftar">Salah email? Daftar ulang</a> &nbsp;·&nbsp; <a href="/masuk">Masuk</a>`;
    form.append(h, p, tombolUlang({ email: r.email }, true), alt);
  }

  // login Google (Google Identity Services)
  const holder = document.getElementById("gbtn");
  const { google_client_id: cid } = await PC.api("/api/config");
  if (!cid) {
    const G = `<svg viewBox="0 0 48 48" width="18" height="18" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>`;
    holder.innerHTML = `<button type="button" class="gbtn-fallback">${G}<span>${isDaftar ? "Daftar dengan Google" : "Masuk dengan Google"}</span></button>`;
    holder.firstChild.onclick = () => fail(new Error("Login Google belum dikonfigurasi (isi GOOGLE_CLIENT_ID di file .env)"));
    return;
  }
  const s = document.createElement("script");
  s.src = "https://accounts.google.com/gsi/client"; s.async = true;
  s.onload = () => {
    google.accounts.id.initialize({ client_id: cid, callback: r => PC.post("/api/google", { credential: r.credential }).then(done).catch(fail) });
    google.accounts.id.renderButton(holder, { theme: "outline", size: "large", shape: "pill", width: Math.min(holder.clientWidth || 380, 400), text: isDaftar ? "signup_with" : "signin_with" });
  };
  document.head.append(s);
})();
