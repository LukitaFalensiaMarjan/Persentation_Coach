/* Halaman latihan: kamera -> frame JPEG ke server (WebSocket) -> label + keypoint -> overlay -> hasil */
(async function () {
  const me = await PC.renderNav("/latihan");
  if (!me) return (location.href = "/masuk");
  const $ = id => document.getElementById(id);
  const cam = $("cam"), ov = $("ov"), octx = ov.getContext("2d");
  const NAMA = { netral: "Netral", gestur_aktif: "Gestur aktif", menunjuk_slide: "Menunjuk slide", menunduk: "Menunduk", membelakangi: "Membelakangi", tangan_terlipat: "Tangan terlipat", tangan_tersembunyi: "Tangan tersembunyi", tidak_terlihat: "Tidak terlihat" };
  const BURUK = new Set(["menunduk", "membelakangi", "tangan_terlipat", "tangan_tersembunyi", "tidak_terlihat"]);
  const EDGES = [[5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [0, 1], [0, 2], [1, 3], [2, 4]];
  const mmss = s => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  let stream = null, ws = null, running = false, durasi = 60, tStart = 0, timerH = 0, fps = 0, lastT = 0, showDbg = false;

  // ---------- kamera ----------
  const ambil = id => navigator.mediaDevices.getUserMedia({ audio: false, video: { width: { ideal: 1280 }, height: { ideal: 720 }, ...(id ? { deviceId: { exact: id } } : {}) } });
  async function bukaStream(id) {
    try { return await ambil(id); }
    catch (e) {  // kamera tidak mendukung batasan resolusi: coba tanpa batasan
      if (e.name !== "OverconstrainedError" && e.name !== "TypeError") throw e;
      return await navigator.mediaDevices.getUserMedia({ audio: false, video: id ? { deviceId: { exact: id } } : true });
    }
  }
  const daftarKamera = async () => (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === "videoinput");
  const isiPilihan = (devs, cur) => {
    $("camSel").innerHTML = devs.map((d, i) => `<option value="${d.deviceId}" ${d.deviceId === cur ? "selected" : ""}>${(d.label || "Kamera " + (i + 1)).replace(/[<>&]/g, "")}</option>`).join("") || "<option>Tidak ada kamera</option>";
  };

  async function openCam(deviceId) {
    stream && stream.getTracks().forEach(t => t.stop());
    stream = null;
    $("cover").hidden = false; $("cover").textContent = "Menyalakan kamera…";
    let devs = [];
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw Object.assign(new Error("tidak ada mediaDevices"), { name: "NoMediaDevices" });
      try {
        stream = await bukaStream(deviceId);
      } catch (e) {
        // kamera terpilih sedang dipakai/rusak: otomatis coba kamera lain (mis. webcam eksternal vs bawaan laptop)
        if (e.name !== "NotReadableError" && e.name !== "AbortError") throw e;
        devs = await daftarKamera();
        const coba = devs.filter(d => d.deviceId && d.deviceId !== deviceId);
        for (const d of coba) { try { stream = await bukaStream(d.deviceId); break; } catch { /* lanjut ke kamera berikutnya */ } }
        if (!stream) throw Object.assign(e, { jumlah: devs.length });
      }
    } catch (e) {
      console.warn("Kamera gagal dibuka:", e.name, e.message);
      try { devs = devs.length ? devs : await daftarKamera(); isiPilihan(devs, deviceId); } catch { /* daftar kamera opsional */ }
      const PESAN = {
        NoMediaDevices: "Browser tidak mengizinkan kamera di alamat ini. Buka lewat http://localhost:8000 (bukan alamat IP) atau lewat HTTPS.",
        NotAllowedError: "Akses kamera ditolak. Klik ikon kamera atau gembok di sebelah alamat browser, pilih Izinkan, lalu tekan Coba lagi. Di Windows, cek juga Pengaturan > Privasi & keamanan > Kamera.",
        SecurityError: "Akses kamera diblokir oleh browser. Pastikan alamat memakai localhost atau HTTPS, lalu tekan Coba lagi.",
        NotFoundError: "Tidak ada kamera yang terdeteksi. Sambungkan webcam, lalu tekan Coba lagi.",
        NotReadableError: `Kamera tidak bisa dipakai (${devs.length} kamera terdeteksi, semuanya gagal). Kemungkinan dipakai aplikasi lain (Zoom, Teams, atau program Python yang masih membuka webcam) atau tab browser lain. Tutup semuanya, lalu tekan Coba lagi. Kamera lain bisa dipilih di kotak Kamera.`,
        AbortError: "Kamera sedang dipakai aplikasi lain. Tutup aplikasi itu, lalu tekan Coba lagi.",
      };
      const c = $("cover"); c.replaceChildren();
      const p = document.createElement("div"); p.textContent = PESAN[e.name] || `Kamera gagal dibuka (${e.name}).`;
      const b = document.createElement("button"); b.className = "btn ghost light"; b.style.marginTop = "14px"; b.textContent = "Coba lagi"; b.onclick = () => openCam($("camSel").value || deviceId);
      const w = document.createElement("div"); w.append(p, b); c.append(w);
      $("startBtn").disabled = true; return;
    }
    cam.srcObject = stream;
    try { await cam.play(); } catch (e) { console.warn("video.play gagal", e); }
    $("stage").style.aspectRatio = `${cam.videoWidth || 16} / ${cam.videoHeight || 9}`;
    $("cover").hidden = true; $("startBtn").disabled = false;
    isiPilihan(await daftarKamera(), stream.getVideoTracks()[0].getSettings().deviceId);
    sizeOverlay();
  }
  function sizeOverlay() { const r = devicePixelRatio || 1; ov.width = cam.clientWidth * r; ov.height = cam.clientHeight * r; }
  new ResizeObserver(sizeOverlay).observe($("stage"));
  $("camSel").onchange = e => !running && openCam(e.target.value);

  // ---------- pilihan durasi ----------
  $("durs").onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    durasi = +b.dataset.s; $("durCustom").value = "";
    $("durs").querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
  };
  $("durCustom").oninput = e => {
    const m = Math.max(1, Math.min(30, Math.floor(+e.target.value || 0)));
    if (e.target.value) { durasi = m * 60; $("durs").querySelectorAll("button").forEach(x => x.classList.remove("on")); }
  };

  // ---------- gambar overlay ----------
  function draw(kp) {
    const w = ov.width, h = ov.height;
    octx.clearRect(0, 0, w, h);
    if (!kp.length) return;
    octx.lineWidth = Math.max(2, w / 320); octx.lineCap = "round";
    octx.strokeStyle = "rgba(233,183,95,.95)";
    for (const [a, b] of EDGES) {
      if (kp[a][2] < 0.3 || kp[b][2] < 0.3) continue;
      octx.beginPath(); octx.moveTo(kp[a][0] * w, kp[a][1] * h); octx.lineTo(kp[b][0] * w, kp[b][1] * h); octx.stroke();
    }
    for (const [x, y, c] of kp) {
      if (c < 0.3) continue;
      octx.beginPath(); octx.arc(x * w, y * h, Math.max(3, w / 190), 0, 6.2832);
      octx.fillStyle = "#fff"; octx.fill(); octx.strokeStyle = "#1b1a19"; octx.lineWidth = 1.5; octx.stroke();
    }
  }

  // ---------- jalankan sesi ----------
  const cap = document.createElement("canvas"), cctx = cap.getContext("2d");
  function sendFrame() {
    if (!running || ws.readyState !== 1) return;
    if (!cam.videoWidth) return void setTimeout(sendFrame, 50);
    cap.width = 480; cap.height = Math.round(480 * cam.videoHeight / cam.videoWidth);
    cctx.drawImage(cam, 0, 0, cap.width, cap.height);
    cap.toBlob(b => b && running && ws.readyState === 1 && ws.send(b), "image/jpeg", 0.75);
  }
  function setUi(on) {
    $("setupBox").hidden = on; $("runBox").hidden = !on; $("hud").hidden = !on;
    document.body.classList.toggle("running", on);
  }
  function reset() {
    running = false; clearInterval(timerH); setUi(false); octx.clearRect(0, 0, ov.width, ov.height);
    $("alert").classList.remove("show"); $("cover").hidden = true; $("startBtn").disabled = false;
    ws && ws.readyState <= 1 && ws.close(); ws = null;
  }
  function start() {
    $("startBtn").disabled = true; $("cover").hidden = false; $("cover").textContent = "Memuat model deteksi… (pertama kali bisa beberapa detik)";
    ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/latihan`);
    ws.onopen = () => ws.send(JSON.stringify({ type: "mulai", durasi }));
    ws.onclose = () => { if (running) { PC.toast("Koneksi ke server terputus"); reset(); } };
    ws.onmessage = ev => {
      const d = JSON.parse(ev.data);
      if (d.type === "siap") {
        running = true; setUi(true); $("cover").hidden = true; tStart = performance.now();
        timerH = setInterval(tick, 200); tick(); sendFrame();
      } else if (d.type === "frame") {
        onFrame(d); sendFrame();
      } else if (d.type === "hasil") {
        reset(); HasilModal.show(d.hasil);
      } else if (d.type === "error") {
        PC.toast(d.pesan); reset();
      }
    };
  }
  function tick() {
    const left = durasi - (performance.now() - tStart) / 1000;
    $("timer").textContent = mmss(Math.max(0, left));
    if (left <= 0) stop();
  }
  function stop() {
    if (!running) return;
    running = false; clearInterval(timerH); octx.clearRect(0, 0, ov.width, ov.height);
    $("alert").classList.remove("show"); $("hud").hidden = true; $("runBox").hidden = true;
    $("cover").hidden = false; $("cover").textContent = "Menghitung hasil…";
    ws.send(JSON.stringify({ type: "selesai" }));
  }
  function onFrame(d) {
    draw(d.kp);
    const bad = BURUK.has(d.label);
    $("lbl").classList.toggle("warn", bad); $("lblT").textContent = NAMA[d.label] || d.label;
    const now = performance.now(); fps = 0.85 * fps + 0.15 * (1000 / Math.max(now - lastT, 1)); lastT = now;
    $("fps").textContent = `${fps.toFixed(0)} FPS`;
    const a = $("alert"); if (d.peringatan) a.textContent = d.peringatan; a.classList.toggle("show", !!d.peringatan);
    $("dbg").textContent = Object.entries(d.dbg || {}).map(([k, v]) => `${k}=${v}`).join("  ") + (d.sumber ? `  [${d.sumber} ${d.conf}]` : "");
  }

  $("startBtn").onclick = start;
  $("stopBtn").onclick = stop;
  $("dbgBtn").onclick = () => { showDbg = !showDbg; $("dbg").classList.toggle("on", showDbg); $("dbgBtn").textContent = showDbg ? "Sembunyikan angka debug" : "Tampilkan angka debug"; };
  addEventListener("beforeunload", e => { if (running) { e.preventDefault(); e.returnValue = ""; } });
  openCam();
})();
