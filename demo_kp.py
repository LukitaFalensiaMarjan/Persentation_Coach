"""
demo_kp.py
Demo real-time memakai classifier KEYPOINT + aturan geometri.
Urutan keputusan:
  1. aturan  : membelakangi -> tangan_terlipat -> menunjuk_slide   (geometri tubuh)
  2. gerak   : gestur_aktif jika tangan di depan badan dan bergerak cepat
  3. model   : kelas lainnya (Random Forest dari keypoint)

Pemakaian:
  python demo_kp.py --kp models\\kp_rf.joblib --cam 1
  python demo_kp.py --kp models\\kp_rf.joblib --cam 1 --cls models\\gesture_best.pt
tombol:  q = keluar,  s = screenshot,  d = tampilkan/sembunyikan angka debug
"""
import argparse
import os
import time
from collections import Counter, deque
from pathlib import Path

import cv2
import joblib
from ultralytics import YOLO

from kp_features import features, keypoints_of, largest_person, rule_label

BACKEND = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY


class MotionMeter:
    """Mengukur kecepatan gerak pergelangan tangan (satuan: panjang badan per detik),
    relatif terhadap bahu, sehingga orang yang berjalan tidak dihitung sebagai gestur.
    Anti-getar: posisi tangan dihaluskan (EMA), getaran kecil di bawah `deadband` diabaikan,
    dan hanya tangan dengan confidence tinggi yang dihitung."""

    def __init__(self, seconds=1.0, alpha=0.5, deadband=0.03, min_conf=0.65):
        self.seconds, self.alpha, self.deadband, self.min_conf = seconds, alpha, deadband, min_conf
        self.buf = deque()
        self.smooth = {}

    def reset(self):
        self.buf.clear()
        self.smooth.clear()

    def update(self, xy, conf):
        now = time.time()
        L_SH, R_SH, L_WR, R_WR, L_HIP, R_HIP = 5, 6, 9, 10, 11, 12
        mc = self.min_conf
        if not (conf[L_SH] >= mc and conf[R_SH] >= mc):
            self.reset()
            return 0.0, False
        mid = (xy[L_SH] + xy[R_SH]) / 2
        if conf[L_HIP] >= mc and conf[R_HIP] >= mc:
            hip_y = (xy[L_HIP, 1] + xy[R_HIP, 1]) / 2
            scale = abs(hip_y - mid[1])
        else:
            hip_y = None
            scale = abs(xy[L_SH, 0] - xy[R_SH, 0]) * 1.5
        if scale < 1e-3:
            return 0.0, False
        wr = {}
        in_front = False
        for w in (L_WR, R_WR):
            if conf[w] >= mc:
                p = (xy[w] - mid) / scale
                prev = self.smooth.get(w)
                p = p if prev is None else self.alpha * p + (1 - self.alpha) * prev
                self.smooth[w] = p
                wr[w] = p
                # tangan di depan badan: antara bahu dan sedikit di bawah pinggul
                if xy[w, 1] > mid[1] - 0.2 * scale and (hip_y is None or xy[w, 1] < hip_y + 0.15 * scale):
                    in_front = True
            else:
                self.smooth.pop(w, None)   # tangan hilang/tertutup -> jangan dihitung bergerak
        self.buf.append((now, wr))
        while self.buf and now - self.buf[0][0] > self.seconds:
            self.buf.popleft()
        dist = 0.0
        items = list(self.buf)
        for (_, a), (_, b) in zip(items, items[1:]):
            for w in (L_WR, R_WR):
                if w in a and w in b:
                    step = float(((b[w] - a[w]) ** 2).sum() ** 0.5)
                    if step > self.deadband:
                        dist += step
        span = items[-1][0] - items[0][0] if len(items) > 1 else 0.0
        speed = dist / span if span > 0.3 else 0.0
        return speed, in_front


def pad_square(img):
    h, w = img.shape[:2]
    s = max(h, w)
    top, left = (s - h) // 2, (s - w) // 2
    return cv2.copyMakeBorder(img, top, s - h - top, left, s - w - left,
                              cv2.BORDER_CONSTANT, value=(0, 0, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kp", required=True, help="model keypoint, mis. models\\kp_rf.joblib")
    ap.add_argument("--cls", default="", help="(opsional) model gambar YOLO-cls untuk pembanding")
    ap.add_argument("--pose", default="yolo11n-pose.pt")
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--window", type=int, default=15, help="jumlah frame untuk voting")
    ap.add_argument("--min-conf", type=float, default=0.45, help="di bawah ini tebakan model dianggap ragu")
    ap.add_argument("--pad", type=float, default=0.10)
    # ambang aturan (atur sambil melihat angka debug, tekan d)
    ap.add_argument("--face-t", type=float, default=0.35, help="wajah < ini -> membelakangi")
    ap.add_argument("--facing-t", type=float, default=-0.15, help="arah < ini -> membelakangi")
    ap.add_argument("--fold-t", type=float, default=0.45, help="lipat < ini -> tangan_terlipat")
    ap.add_argument("--arm-t", type=float, default=0.8, help="lengan > ini -> menunjuk_slide")
    ap.add_argument("--move-t", type=float, default=1.0,
                    help="gerak tangan > ini (panjang badan/detik) -> gestur_aktif")
    ap.add_argument("--static-t", type=float, default=0.5,
                    help="jika model yakin >= ini pada tangan_tersembunyi, gerak diabaikan")
    ap.add_argument("--no-rules", action="store_true", help="matikan aturan (model saja)")
    args = ap.parse_args()

    bundle = joblib.load(args.kp)
    rf, classes = bundle["model"], bundle["classes"]
    pose = YOLO(args.pose)
    clf = YOLO(args.cls) if args.cls else None
    history = deque(maxlen=args.window)
    motion = MotionMeter(seconds=1.0)
    show_debug = True

    cap = cv2.VideoCapture(args.cam, BACKEND)
    if not cap.isOpened():
        raise SystemExit(f"Kamera index {args.cam} tidak bisa dibuka. Jalankan cek_kamera.py dulu.")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    Path("screenshots").mkdir(exist_ok=True)

    prev, fps = time.time(), 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Gagal membaca frame dari kamera.")
            break

        r = pose(frame, conf=0.5, verbose=False)[0]
        i = largest_person(r)
        main_text, sub_text, dbg_text = "tidak ada orang", "", ""

        if i is not None:
            xy, kconf = keypoints_of(r, i)
            name, conf, source = None, 0.0, ""

            # 1) aturan geometri
            rule, info = (None, {}) if args.no_rules else rule_label(
                xy, kconf, args.face_t, args.facing_t, args.arm_t, args.fold_t)
            speed, in_front = motion.update(xy, kconf)
            info["gerak"] = speed

            # 3) tebakan model
            m_name, m_conf = None, 0.0
            f = features(xy, kconf)
            if f is not None:
                proba = rf.predict_proba([f])[0]
                k = int(proba.argmax())
                m_name, m_conf = classes[k], float(proba[k])
            hidden_lock = m_name == "tangan_tersembunyi" and m_conf >= args.static_t

            # 2) gestur_aktif dari gerak tangan
            if (not args.no_rules and rule is None and in_front
                    and speed > args.move_t and not hidden_lock):
                rule = "gestur_aktif"
            dbg_text = "  ".join(f"{k}={v:.2f}" for k, v in info.items())

            if rule:
                name, conf, source = rule, 1.0, "aturan"
            elif m_name:
                name, conf, source = m_name, m_conf, "model"

            if name and conf >= args.min_conf:
                history.append(name)
            if history:
                main_text = Counter(history).most_common(1)[0][0]
            else:
                main_text = "ragu..." if name else "bahu tidak terlihat"
            if name:
                sub_text = f"{source}: {name} ({conf:.2f})"
                if source == "aturan" and m_name:
                    sub_text += f"  [model: {m_name} {m_conf:.2f}]"

            if clf is not None:
                x1, y1, x2, y2 = r.boxes.xyxy[i].cpu().numpy()
                w, h = x2 - x1, y2 - y1
                H, W = frame.shape[:2]
                crop = frame[max(0, int(y1 - args.pad * h)):min(H, int(y2 + args.pad * h)),
                             max(0, int(x1 - args.pad * w)):min(W, int(x2 + args.pad * w))]
                if crop.size:
                    c = clf(pad_square(crop), verbose=False)[0]
                    sub_text += f"  |  gambar: {c.names[c.probs.top1]} ({float(c.probs.top1conf):.2f})"

            frame = r.plot(boxes=True, labels=False)

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6))
        prev = now

        bar_h = 125 if show_debug else 75
        cv2.rectangle(frame, (0, 0), (frame.shape[1], bar_h), (0, 0, 0), -1)
        cv2.putText(frame, main_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(frame, f"{sub_text}   FPS {fps:.1f}", (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        if show_debug:
            cv2.putText(frame, f"debug: {dbg_text}", (15, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
            cv2.putText(frame, f"ambang: wajah<{args.face_t} arah<{args.facing_t} lipat<{args.fold_t} "
                               f"lengan>{args.arm_t} gerak>{args.move_t} sembunyi>={args.static_t}",
                        (15, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
        cv2.imshow("Persentation Coach - keypoint (q keluar, s screenshot, d debug)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("d"):
            show_debug = not show_debug
        if key == ord("s"):
            fn = f"screenshots/kp_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(fn, frame)
            print("Tersimpan:", fn)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
