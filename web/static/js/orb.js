/* Logo monogram "PC" 3D berwarna emas (Three.js r128). initOrb(canvas, lite) -> { setPose(k) } */
function initOrb(canvas, lite) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: !lite });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, lite ? 1 : 1.75));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.z = 4.2;
  const group = new THREE.Group();
  scene.add(group);

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const key = new THREE.DirectionalLight(0xfff1d0, 1.15); key.position.set(3, 4, 5); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.45); fill.position.set(-4, -2, 3); scene.add(fill);
  const warm = new THREE.PointLight(0xffc15a, 1.6, 12); warm.position.set(-2, -2, 2.5); scene.add(warm);

  // huruf P dan C dari tabung; ujung dibulatkan dengan bola
  const mat = new THREE.MeshStandardMaterial({ color: 0x1c1c1e, metalness: 0.35, roughness: 0.38 });
  let R = 0.075;
  const logo = new THREE.Group();
  class Arc extends THREE.Curve {
    constructor(cx, cy, r, a0, a1) { super(); Object.assign(this, { cx, cy, r, a0, a1 }); }
    getPoint(t, o = new THREE.Vector3()) { const a = this.a0 + (this.a1 - this.a0) * t; return o.set(this.cx + this.r * Math.cos(a), this.cy + this.r * Math.sin(a), 0); }
  }
  const tube = c => logo.add(new THREE.Mesh(new THREE.TubeGeometry(c, 72, R, 24, false), mat));
  const cap = (x, y) => { const m = new THREE.Mesh(new THREE.SphereGeometry(R, 24, 16), mat); m.position.set(x, y, 0); logo.add(m); };
  const V = (x, y) => new THREE.Vector3(x, y, 0);

  // setiap huruf digambar dengan dua garis sejajar (garis luar + garis dalam), P bersarang di dalam C
  R = 0.035;
  const D = 0.2, PI = Math.PI;
  const line = (x1, y1, x2, y2) => { tube(new THREE.LineCurve3(V(x1, y1), V(x2, y2))); cap(x1, y1); cap(x2, y2); };
  const arc = (x, y, r, a0, a1) => {
    tube(new Arc(x, y, r, a0, a1));
    cap(x + r * Math.cos(a0), y + r * Math.sin(a0)); cap(x + r * Math.cos(a1), y + r * Math.sin(a1));
  };
  // huruf C: dua busur sepusat
  const cx = 0.2, cr = 1.15, a0 = 0.75;
  arc(cx, 0, cr, a0, 2 * PI - a0);
  arc(cx, 0, cr - D, a0, 2 * PI - a0);
  for (const s of [1, -1]) line(cx + cr * Math.cos(a0), s * cr * Math.sin(a0), cx + (cr - D) * Math.cos(a0), s * (cr - D) * Math.sin(a0)); // tutup ujung C
  // huruf P di dalam C: pita batang + pita perut; dua garis = dua tepi pita
  const xo = -0.42, xs = xo + D, yt = 0.7, ro = 0.42, yc = yt - ro, yb = -0.65;
  line(xo, yb, xo, yt); line(xo, yt, xs, yt); line(xo, yb, xs, yb);   // tepi kiri, atas, bawah batang
  line(xs, yb, xs, yc - ro);                                           // tepi kanan batang
  arc(xs, yc, ro, PI / 2, -PI / 2);                                    // tepi luar perut
  arc(xs, yc, ro - D, PI / 2, -PI / 2);                                // tepi dalam perut
  line(xs, yc - (ro - D), xs, yc + (ro - D));                          // sisi lubang P

  // presenter di dalam C: kepala, badan, kaki, lengan yang menunjuk ke audiens
  const fx = 0.62;
  arc(fx, 0.42, 0.15, 0, 2 * PI);
  line(fx, 0.27, fx, -0.25);
  line(fx, -0.25, fx - 0.18, -0.62);
  line(fx, -0.25, fx + 0.18, -0.62);
  line(fx, 0.1, fx + 0.38, 0.28);
  line(fx, 0.1, fx - 0.22, -0.08);
  logo.position.x = -0.05; // pusatkan
  group.add(logo);

  // percikan emas di sekitar logo
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  [[0, "rgba(255,244,210,1)"], [0.3, "rgba(255,190,90,.8)"], [1, "rgba(255,150,40,0)"]].forEach(([o, col]) => gr.addColorStop(o, col));
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const sp = [];
  for (let i = 0; i < (lite ? 20 : 45); i++) {
    const a = Math.random() * 6.28, r = 1.6 + Math.random() * 1.1;
    sp.push(Math.cos(a) * r * 1.2, Math.sin(a) * r * 0.8, (Math.random() - 0.5) * 1.5);
  }
  const sg = new THREE.BufferGeometry(); sg.setAttribute("position", new THREE.Float32BufferAttribute(sp, 3));
  const sparks = new THREE.Points(sg, new THREE.PointsMaterial({ map: new THREE.CanvasTexture(c), size: 0.09, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  sparks.visible = false; // logo gelap: tanpa percikan emas
  group.add(sparks);

  // titik hitam melayang di sekitar logo (dua ukuran), bergerak naik-turun dengan fase berbeda
  const dc = document.createElement("canvas"); dc.width = dc.height = 64;
  const dg = dc.getContext("2d"); dg.fillStyle = "#151517"; dg.beginPath(); dg.arc(32, 32, 26, 0, 6.2832); dg.fill();
  const dotTex = new THREE.CanvasTexture(dc);
  // titik emas: bola kecil berkilau (terang di pojok kiri-atas, gelap di tepi)
  const gc = document.createElement("canvas"); gc.width = gc.height = 64;
  const gg = gc.getContext("2d"), grd = gg.createRadialGradient(24, 22, 2, 32, 32, 27);
  [[0, "#fff6d6"], [0.45, "#e9b75f"], [1, "#a97a2a"]].forEach(([o, c]) => grd.addColorStop(o, c));
  gg.fillStyle = grd; gg.beginPath(); gg.arc(32, 32, 27, 0, 6.2832); gg.fill();
  const goldTex = new THREE.CanvasTexture(gc);
  // cahaya lembut: lingkaran emas transparan untuk halo titik emas dan latar logo
  const hc = document.createElement("canvas"); hc.width = hc.height = 128;
  const hg = hc.getContext("2d"), hgr = hg.createRadialGradient(64, 64, 0, 64, 64, 64);
  [[0, "rgba(255,214,120,.9)"], [0.3, "rgba(255,196,90,.4)"], [1, "rgba(255,180,70,0)"]].forEach(([o, c]) => hgr.addColorStop(o, c));
  hg.fillStyle = hgr; hg.fillRect(0, 0, 128, 128);
  const glowTex = new THREE.CanvasTexture(hc), glowMats = [];
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, opacity: 0.4 }));
  halo.scale.setScalar(5.2); halo.position.z = -0.8; group.add(halo);
  const floaters = [[lite ? 18 : 34, 0.07, dotTex], [lite ? 24 : 50, 0.035, dotTex], [lite ? 12 : 22, 0.075, goldTex], [lite ? 14 : 30, 0.04, goldTex]].map(([n, size, tex]) => {
    const base = [], phase = [];
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.2832, r = 1.5 + Math.random() * 1.4;
      base.push(Math.cos(a) * r * 1.25, Math.sin(a) * r * 0.85, (Math.random() - 0.5) * 2); phase.push(Math.random() * 6.2832);
    }
    const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(base.slice(), 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ map: tex, size, transparent: true, depthWrite: false, alphaTest: 0.05 }));
    group.add(pts);
    if (tex === goldTex) { // halo cahaya di belakang tiap titik emas, berbagi posisi yang sama
      const gl = new THREE.Points(geo, new THREE.PointsMaterial({ map: glowTex, size: size * 5, transparent: true, depthWrite: false, opacity: 0.7 }));
      group.add(gl); glowMats.push(gl.material);
    }
    return { pts, base, phase };
  });

  // pose per seksi landing
  const POSES = [{ x: 0, y: -0.8, s: 0.5 }, { x: 0.9, y: 0, s: 0.8 }, { x: 0, y: 0, s: 0.8 }, { x: 0, y: 0, s: 0.8 }, { x: 0.9, y: 0, s: 0.85 }];
  let aspect = 1, curK = 0, pose = POSES[0];
  const apply = immediate => {
    const isMobile = aspect < 0.95 || (window.innerWidth && window.innerWidth <= 820);
    let to, sc;
    if (isMobile) {
      const w = canvas.clientWidth || window.innerWidth || 390;
      const mScale = Math.min(0.28, Math.max(0.20, 0.26 * (w / 380)));
      if (curK === 0) {
        // Halaman 1 (Hero): posisi seimbang di bawah tombol aksi
        to = { x: 0, y: -0.46 };
        sc = mScale;
      } else if (curK === 1) {
        // Halaman 2 (Tentang): diangkat ke tengah area terbuka (y = -0.32) agar tidak terlalu bawah
        to = { x: 0, y: -0.32 };
        sc = mScale;
      } else if (curK === 4) {
        // Halaman 5 (Ajakan/CTA): diangkat pas di bawah tombol (y = -0.42)
        to = { x: 0, y: -0.42 };
        sc = mScale;
      } else {
        to = { x: 0, y: 0 };
        sc = mScale;
      }
    } else {
      const fit = Math.min(1, aspect / 1.5);
      to = { x: pose.x, y: pose.y };
      sc = pose.s * fit;
    }
    if (immediate || !window.gsap) { group.position.set(to.x, to.y, 0); group.scale.setScalar(sc); return; }
    gsap.to(group.position, { ...to, duration: 1.3, ease: "power3.inOut" });
    gsap.to(group.scale, { x: sc, y: sc, z: sc, duration: 1.3, ease: "power3.inOut" });
  };
  const resize = () => {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    aspect = w / h; camera.aspect = aspect; camera.updateProjectionMatrix();
    apply(true);
  };
  window.addEventListener("resize", resize);
  resize();

  const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
  window.addEventListener("pointermove", e => { mouse.tx = e.clientX / innerWidth - 0.5; mouse.ty = e.clientY / innerHeight - 0.5; });
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clock = new THREE.Clock();
  (function loop() {
    requestAnimationFrame(loop);
    if (document.hidden) return;
    const t = clock.getElapsedTime();
    mouse.x += (mouse.tx - mouse.x) * 0.05; mouse.y += (mouse.ty - mouse.y) * 0.05;
    group.rotation.y = (still ? 0 : Math.sin(t * 0.6) * 0.4) + mouse.x * 0.6; // ayun pelan agar huruf tetap terbaca
    group.rotation.x = mouse.y * 0.35;
    floaters.forEach(({ pts, base, phase }) => {
      const p = pts.geometry.attributes.position;
      for (let i = 0; i < phase.length; i++) {
        p.setXYZ(i, base[i * 3] + Math.sin(t * 0.35 + phase[i]) * 0.12, base[i * 3 + 1] + Math.sin(t * 0.5 + phase[i] * 1.7) * 0.22, base[i * 3 + 2]);
      }
      p.needsUpdate = true;
    });
    glowMats.forEach((m, i) => (m.opacity = 0.55 + 0.35 * Math.sin(t * 1.4 + i * 1.9)));      // titik emas berkedip
    halo.material.opacity = 0.34 + 0.1 * Math.sin(t * 0.9);                                  // halo logo berdenyut
    warm.position.set(Math.cos(t * 0.6) * 3, Math.sin(t * 0.4) * 2, 2.5);                    // sorot cahaya menyapu logo
    sparks.rotation.z = t * 0.05;
    sparks.material.opacity = 0.7 + Math.sin(t * 2) * 0.3;
    renderer.render(scene, camera);
  })();

  return {
    setPose: k => {
      curK = typeof k === "number" ? k : 0;
      pose = POSES[curK] || POSES[0];
      apply(false);
    }
  };
}
