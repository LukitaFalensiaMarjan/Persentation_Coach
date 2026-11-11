"""Mesin analisis latihan: YOLO11-pose + aturan geometri + gerak tangan + Random Forest (sama dengan demo_kp.py),
agregasi per sesi, skor 0-100 per aspek, dan saran. Video tidak disimpan: hanya angka."""
import threading
import time
from collections import Counter, deque
from pathlib import Path

import cv2
import joblib
import numpy as np
from ultralytics import YOLO

from demo_kp import MotionMeter
from kp_features import features, keypoints_of, largest_person, rule_label

ROOT = Path(__file__).resolve().parent.parent
TH = dict(face_t=0.35, facing_t=-0.15, arm_t=0.8, fold_t=0.45, move_t=1.0, static_t=0.5, min_conf=0.45)
WINDOW = 15
GRID = (16, 9)  # kolom x baris untuk heatmap posisi berdiri
LABELS = ["netral", "gestur_aktif", "menunjuk_slide", "menunduk", "membelakangi", "tangan_terlipat", "tangan_tersembunyi"]
NAMA = {"netral": "Netral", "gestur_aktif": "Gestur aktif", "menunjuk_slide": "Menunjuk slide", "menunduk": "Menunduk",
        "membelakangi": "Membelakangi", "tangan_terlipat": "Tangan terlipat", "tangan_tersembunyi": "Tangan tersembunyi"}
# batas peringatan langsung di layar: label -> (detik berturut-turut, pesan)
PERINGATAN = {"membelakangi": (3, "Kamu membelakangi audiens. Hadapkan badan ke depan."),
              "menunduk": (5, "Kamu menunduk terlalu lama. Angkat kepala."),
              "tangan_terlipat": (10, "Tangan terlipat terlalu lama. Buka tanganmu.")}
BOBOT = {"orientasi": 0.30, "gestur": 0.30, "postur": 0.25, "gerak": 0.15}  # belum dikalibrasi dengan penilai manusia

_load_lock, _infer_lock, _models = threading.Lock(), threading.Lock(), None


def models():
    global _models
    with _load_lock:
        if _models is None:
            bundle = joblib.load(ROOT / "models" / "kp_rf.joblib")
            _models = (YOLO(str(ROOT / "yolo11n-pose.pt")), bundle["model"], bundle["classes"])
    return _models


class Sesi:
    def __init__(self, durasi: int):
        self.durasi = durasi
        self.t0 = self.last = None
        self.history = deque(maxlen=WINDOW)
        self.motion = MotionMeter(seconds=1.0)
        self.waktu = Counter()
        self.timeline = []          # [mulai, selesai, label]
        self.run = None             # (label, mulai)
        self.hips, self.speeds = [], []

    def _tutup_run(self, t):
        if self.run and t - self.run[1] > 0:
            self.timeline.append([round(self.run[1], 1), round(t, 1), self.run[0]])

    def frame(self, jpeg: bytes) -> dict:
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("frame tidak valid")
        H, W = img.shape[:2]
        pose, rf, classes = models()
        with _infer_lock:
            r = pose(img, conf=0.5, verbose=False, imgsz=480)[0]
        now = time.time()
        if self.t0 is None:
            self.t0 = now
        dt = min(now - self.last, 0.6) if self.last else 0.0
        self.last = now
        elapsed = now - self.t0

        out = {"label": "tidak_terlihat", "conf": 0.0, "sumber": "", "kp": [], "dbg": {}, "peringatan": None, "t": round(elapsed, 1)}
        i = largest_person(r)
        if i is not None:
            xy, kc = keypoints_of(r, i)
            rule, info = rule_label(xy, kc, TH["face_t"], TH["facing_t"], TH["arm_t"], TH["fold_t"])
            speed, in_front = self.motion.update(xy, kc)
            info["gerak"] = speed
            m_name, m_conf = None, 0.0
            f = features(xy, kc)
            if f is not None:
                proba = rf.predict_proba([f])[0]
                k = int(proba.argmax())
                m_name, m_conf = classes[k], float(proba[k])
            hidden_lock = m_name == "tangan_tersembunyi" and m_conf >= TH["static_t"]
            if rule is None and in_front and speed > TH["move_t"] and not hidden_lock:
                rule = "gestur_aktif"
            name, conf, src = (rule, 1.0, "aturan") if rule else ((m_name, m_conf, "model") if m_name else (None, 0.0, ""))
            if name and conf >= TH["min_conf"]:
                self.history.append(name)
            if self.history:
                out["label"] = Counter(self.history).most_common(1)[0][0]
            out.update(conf=round(conf, 2), sumber=src, dbg={k: round(float(v), 2) for k, v in info.items()},
                       kp=[[round(float(x) / W, 4), round(float(y) / H, 4), round(float(c), 2)] for (x, y), c in zip(xy, kc)])
            self.speeds.append(speed)
            hip_ok = kc[11] >= 0.5 and kc[12] >= 0.5
            mid = (xy[11] + xy[12]) / 2 if hip_ok else (xy[5] + xy[6]) / 2
            self.hips.append((float(mid[0]) / W, float(mid[1]) / H))
        else:
            self.history.clear()
            self.motion.reset()

        label = out["label"]
        self.waktu[label] += dt
        if not self.run or self.run[0] != label:
            self._tutup_run(elapsed)
            self.run = (label, elapsed)
        batas = PERINGATAN.get(label)
        if batas and elapsed - self.run[1] >= batas[0]:
            out["peringatan"] = batas[1]
        return out

    def selesai(self) -> dict:
        elapsed = (self.last - self.t0) if self.t0 else 0.0
        self._tutup_run(elapsed)
        visible = sum(v for k, v in self.waktu.items() if k in LABELS)
        if visible < 3:
            raise ValueError("Terlalu sedikit data: kamu hampir tidak terdeteksi kamera. Pastikan badan terlihat sampai pinggul.")
        prop = {k: round(100 * self.waktu.get(k, 0) / visible, 1) for k in LABELS}
        xs = [h[0] for h in self.hips]
        std_x = float(np.std(xs)) if xs else 0.0
        grid = np.zeros((GRID[1], GRID[0]), int)
        for x, y in self.hips:
            grid[min(GRID[1] - 1, int(y * GRID[1])), min(GRID[0] - 1, int(x * GRID[0]))] += 1
        skor = hitung_skor(prop, std_x)
        timeline = [s for s in self.timeline if s[2] in LABELS and s[2] != "netral" and s[1] - s[0] >= 3]
        return {"durasi_aktual": round(elapsed), "proporsi": prop, "skor": skor["aspek"], "total": skor["total"],
                "timeline": timeline, "heatmap": grid.tolist(), "gerak_tangan": round(float(np.mean(self.speeds)), 2) if self.speeds else 0.0,
                "geser_posisi": round(std_x, 3), "saran": saran(skor["aspek"], prop, std_x)}


def hitung_skor(prop: dict, std_x: float) -> dict:
    f = {k: v / 100 for k, v in prop.items()}
    aktif = f["gestur_aktif"] + f["menunjuk_slide"]
    tertutup = f["tangan_terlipat"] + f["tangan_tersembunyi"]
    gerak = 50 + 50 * min(1, std_x / 0.04) if std_x <= 0.2 else max(0, 100 - (std_x - 0.2) * 250)
    aspek = {"orientasi": 100 * (1 - min(1, 2.5 * f["membelakangi"])),
             "gestur": 70 * min(1, aktif / 0.25) + 30 * (1 - min(1, tertutup / 0.5)),
             "postur": 100 * (1 - min(1, 2.5 * f["menunduk"])),
             "gerak": gerak}
    aspek = {k: round(max(0, min(100, v))) for k, v in aspek.items()}
    return {"aspek": aspek, "total": round(sum(aspek[k] * w for k, w in BOBOT.items()))}


def saran(aspek: dict, prop: dict, std_x: float) -> list:
    teks = {
        "orientasi": f"Hadapkan badan ke audiens. Kamu membelakangi audiens {prop['membelakangi']:.0f}% waktu; lirik slide dari samping atau taruh layar di depanmu.",
        "gestur": f"Pakai gerak tangan untuk menekankan poin. Tangan terlipat/tersembunyi {prop['tangan_terlipat'] + prop['tangan_tersembunyi']:.0f}% waktu, gestur aktif hanya {prop['gestur_aktif'] + prop['menunjuk_slide']:.0f}%.",
        "postur": f"Angkat kepala. Kamu menunduk {prop['menunduk']:.0f}% waktu; hafalkan poin utama agar tidak membaca catatan terus.",
        "gerak": "Posisi berdirimu terlalu kaku. Bergeserlah sedikit ke kiri/kanan untuk menjangkau seluruh audiens." if std_x < 0.04
        else "Kamu terlalu banyak berpindah posisi. Berdirilah lebih stabil sambil sesekali melangkah.",
    }
    urut = sorted(aspek, key=aspek.get)
    hasil = [teks[k] for k in urut[:3] if aspek[k] < 85]
    umum = ["Pertahankan kontak mata dengan audiens dan atur napas di awal setiap poin.", "Latih bagian pembuka berulang kali; pembuka yang mantap meredakan gugup."]
    return (hasil + umum)[:3]
