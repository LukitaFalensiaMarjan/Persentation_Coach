"""
demo_webcam.py
Uji model klasifikasi gestur secara langsung dari webcam (bawaan atau eksternal).
  1. YOLO11-pose mendeteksi orang + kerangka tubuh
  2. badan orang di-crop, dibuat persegi (tepi hitam), lalu diklasifikasi
  3. label dihaluskan dengan voting beberapa frame terakhir agar tidak berkedip

Pemakaian:
  python demo_webcam.py --cls models\\gesture_best.pt --cam 1
  tombol:  q = keluar,  s = simpan screenshot
"""
import argparse
import os
import time
from collections import Counter, deque
from pathlib import Path

import cv2
from ultralytics import YOLO

BACKEND = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY


def pad_square(img):
    """Tambah tepi hitam agar gambar persegi tanpa memotong badan
    (sama seperti Resize 'Fit (black edges)' di Roboflow)."""
    h, w = img.shape[:2]
    s = max(h, w)
    top, left = (s - h) // 2, (s - w) // 2
    return cv2.copyMakeBorder(img, top, s - h - top, left, s - w - left,
                              cv2.BORDER_CONSTANT, value=(0, 0, 0))


def open_camera(index, width, height):
    cap = cv2.VideoCapture(index, BACKEND)
    if not cap.isOpened():
        raise SystemExit(f"Kamera index {index} tidak bisa dibuka. Jalankan cek_kamera.py dulu.")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # webcam USB lebih lancar
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cls", required=True, help="model klasifikasi, mis. models\\gesture_best.pt")
    ap.add_argument("--pose", default="yolo11n-pose.pt", help="model pose untuk deteksi orang")
    ap.add_argument("--cam", type=int, default=0, help="index kamera (eksternal biasanya 1)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--window", type=int, default=15, help="jumlah frame untuk voting label")
    ap.add_argument("--pad", type=float, default=0.10, help="margin crop, samakan dengan prep_dataset")
    ap.add_argument("--min-conf", type=float, default=0.50, help="di bawah ini label dianggap ragu")
    args = ap.parse_args()

    pose = YOLO(args.pose)
    clf = YOLO(args.cls)
    history = deque(maxlen=args.window)
    cap = open_camera(args.cam, args.width, args.height)
    Path("screenshots").mkdir(exist_ok=True)

    prev = time.time()
    fps = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Gagal membaca frame dari kamera.")
            break

        r = pose(frame, conf=0.5, verbose=False)[0]
        main_text, sub_text = "tidak ada orang", ""

        if len(r.boxes):
            xyxy = r.boxes.xyxy.cpu().numpy()
            areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
            x1, y1, x2, y2 = xyxy[areas.argmax()]
            w, h = x2 - x1, y2 - y1
            H, W = frame.shape[:2]
            crop = frame[max(0, int(y1 - args.pad * h)):min(H, int(y2 + args.pad * h)),
                         max(0, int(x1 - args.pad * w)):min(W, int(x2 + args.pad * w))]

            if crop.size:
                c = clf(pad_square(crop), verbose=False)[0]
                name = c.names[c.probs.top1]
                conf = float(c.probs.top1conf)
                if conf >= args.min_conf:
                    history.append(name)
                if history:
                    main_text = Counter(history).most_common(1)[0][0]
                sub_text = f"frame ini: {name} ({conf:.2f})"

            frame = r.plot(boxes=True, labels=False)

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev, 1e-6))
        prev = now

        cv2.rectangle(frame, (0, 0), (frame.shape[1], 75), (0, 0, 0), -1)
        cv2.putText(frame, main_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(frame, f"{sub_text}   FPS {fps:.1f}", (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        cv2.imshow("Presentation Coach - demo (q keluar, s screenshot)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            fn = f"screenshots/demo_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(fn, frame)
            print("Tersimpan:", fn)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()