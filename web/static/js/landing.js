/* Landing: scroll satu-layar-per-seksi dengan transisi tirai ala referensi */
(async function () {
  const N = 5, DUR = 1.15, EASE = "power3.inOut";
  const $ = id => document.getElementById(id);
  const me = await PC.renderNav();

  let orb = { setPose() {} };
  if (window.THREE) {
    try {
      const lite = (navigator.hardwareConcurrency || 8) <= 4 || location.search.includes("lite");
      orb = initOrb($("orb"), lite);
    } catch (e) { console.warn("WebGL tidak tersedia, bola 3D dilewati", e); }
  }

  // tombol sesuai status login
  if (me) {
    $("startBtn").href = "/latihan";
    $("ctaBtns").innerHTML = `<a class="btn solid" href="/latihan">Mulai latihan</a><a class="btn ghost" href="/profil">Profil saya</a>`;
  }

  const secs = [0, 1, 2, 3, 4].map(i => $("s" + i));
  const reveal = { 0: $("s0"), 2: $("s2"), 3: $("s3") };
  const hideRv = el => gsap.set(el.querySelectorAll(".rv"), { y: 50, autoAlpha: 0 });
  Object.values(reveal).forEach(hideRv);
  gsap.set(["#s1", "#s4"], { y: 40 });
  gsap.set(["#s2", "#s3"], { yPercent: 101, visibility: "visible" }); // posisi awal diatur GSAP, bukan CSS, agar tidak bentrok

  gsap.to(".ico svg", { y: -7, duration: 2.4, yoyo: true, repeat: -1, ease: "sine.inOut", stagger: 0.35 }); // ikon melayang pelan

  let cur = -1, busy = false;

  function layout(k, instant) {
    const d = instant ? 0 : DUR, late = instant ? 0 : 0.4;
    gsap.to($("s0"), { yPercent: k >= 1 ? -101 : 0, duration: d, ease: EASE });
    gsap.to($("s0low"), { autoAlpha: k === 0 ? 1 : 0, y: k === 0 ? 0 : -20, duration: d * 0.6 });
    gsap.to($("s1"), { autoAlpha: k === 1 ? 1 : 0, y: k === 1 ? 0 : (k < 1 ? 40 : -40), duration: d * 0.8, delay: k === 1 ? late : 0 });
    gsap.to($("s2"), { yPercent: k < 2 ? 101 : k === 4 ? -101 : 0, duration: d, ease: EASE });
    gsap.to($("s3"), { yPercent: k < 3 ? 101 : k === 4 ? -101 : 0, duration: d, ease: EASE });
    gsap.to($("s4"), { autoAlpha: k === 4 ? 1 : 0, y: k === 4 ? 0 : 40, duration: d * 0.8, delay: k === 4 ? late : 0 });
    orb.setPose(k);
    secs.forEach((el, i) => el.toggleAttribute("inert", i !== k));

    // isi tiap panel muncul berurutan; reset setelah panel pergi
    Object.entries(reveal).forEach(([i, el]) => {
      const items = el.querySelectorAll(".rv");
      gsap.killTweensOf(items);
      if (+i === k) gsap.to(items, { y: 0, autoAlpha: 1, duration: instant ? 0 : 0.9, stagger: 0.12, delay: instant ? 0 : 0.5, ease: "power3.out" });
      else gsap.set(items, { y: 50, autoAlpha: 0, delay: instant ? 0 : DUR });
    });
  }

  function goTo(k, instant) {
    k = Math.max(0, Math.min(N - 1, k));
    if (k === cur || (busy && !instant)) return;
    cur = k; busy = !instant;
    layout(k, instant);
    $("counter").textContent = `00${k + 1} / 005`;
    PC.setActive(k < 4 ? k : -1);
    history.replaceState(null, "", k ? "#" + k : location.pathname);
    if (!instant) setTimeout(() => (busy = false), DUR * 1000 + 150);
  }

  // input: roda mouse, sentuh, keyboard, klik
  let acc = 0, accT;
  addEventListener("wheel", e => {
    if (e.target.closest && e.target.closest(".chat-pop")) return;  // gulir di dalam popup chat tidak memindah seksi
    e.preventDefault();
    acc += e.deltaY; clearTimeout(accT); accT = setTimeout(() => (acc = 0), 160);
    if (Math.abs(acc) > 40 && !busy) { goTo(cur + Math.sign(acc)); acc = 0; }
  }, { passive: false });
  let ty = 0;
  addEventListener("touchstart", e => (ty = e.touches[0].clientY), { passive: true });
  addEventListener("touchend", e => { const dy = ty - e.changedTouches[0].clientY; if (Math.abs(dy) > 50) goTo(cur + Math.sign(dy)); }, { passive: true });
  addEventListener("keydown", e => {
    if (e.target.closest("input,textarea")) return;
    if (["ArrowDown", "PageDown", " "].includes(e.key)) { e.preventDefault(); goTo(cur + 1); }
    if (["ArrowUp", "PageUp"].includes(e.key)) { e.preventDefault(); goTo(cur - 1); }
  });
  document.querySelectorAll("[data-go]").forEach(b => (b.onclick = () => goTo(+b.dataset.go)));
  $("nav").addEventListener("click", e => { const a = e.target.closest("[data-k]"); if (a) { e.preventDefault(); goTo(+a.dataset.k); } });
  addEventListener("hashchange", () => goTo(+location.hash.slice(1) || 0));
  $("share").onclick = async () => {
    const data = { title: "Persentation Coach", url: location.origin };
    try { navigator.share ? await navigator.share(data) : (await navigator.clipboard.writeText(data.url), PC.toast("Tautan disalin")); } catch { /* dibatalkan */ }
  };

  // mulai
  const start = Math.min(N - 1, Math.max(0, +location.hash.slice(1) || 0));
  goTo(start, true);
  if (start === 0) gsap.to($("s0").querySelectorAll(".rv"), { y: 0, autoAlpha: 1, duration: 1, stagger: 0.12, delay: 0.3, ease: "power3.out" });
})();
