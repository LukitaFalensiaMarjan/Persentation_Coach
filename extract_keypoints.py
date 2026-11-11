"""
extract_keypoints.py
Menjalankan YOLO11-pose pada semua gambar dataset dan menyimpan fitur keypoint-nya.

Struktur dataset (format Roboflow / split_dataset.py):
  gesture_rf/train/<kelas>/*.jpg
  gesture_rf/val/<kelas>/*.jpg     (atau valid/)
  gesture_rf/test/<kelas>/*.jpg

Pemakaian:
  python extract_keypoints.py --data gesture_rf --out kp_data.npz
"""
import argparse
import time
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from kp_features import features_from_result

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder dataset berisi train/ val/ test/")
    ap.add_argument("--out", default="kp_data.npz")
    ap.add_argument("--pose", default="yolo11n-pose.pt")
    ap.add_argument("--imgsz", type=int, default=416, help="ukuran input pose (lebih kecil = lebih cepat)")
    args = ap.parse_args()

    data = Path(args.data)
    classes = sorted(d.name for d in (data / "train").iterdir() if d.is_dir())
    print("Kelas:", classes)
    pose = YOLO(args.pose)

    saved = {}
    for split in ("train", "val", "valid", "test"):
        sdir = data / split
        if not sdir.is_dir():
            continue
        key = "val" if split == "valid" else split
        X, y = [], []
        files = [(p, ci) for ci, c in enumerate(classes) if (sdir / c).is_dir()
                 for p in sorted((sdir / c).iterdir()) if p.suffix.lower() in IMG_EXT]
        skipped = 0
        t0 = time.time()
        for n, (p, ci) in enumerate(files, 1):
            r = pose(str(p), imgsz=args.imgsz, conf=0.3, verbose=False)[0]
            f = features_from_result(r)
            if f is None:
                skipped += 1
            else:
                X.append(f)
                y.append(ci)
            if n % 200 == 0 or n == len(files):
                print(f"  {key}: {n}/{len(files)}  ({time.time() - t0:.0f} dtk)")
        saved[f"X_{key}"] = np.array(X, dtype=np.float32)
        saved[f"y_{key}"] = np.array(y, dtype=np.int64)
        print(f"{key}: {len(X)} gambar dipakai, {skipped} dilewati (orang/bahu tidak terdeteksi)")

    np.savez_compressed(args.out, classes=np.array(classes), **saved)
    print("\nFitur tersimpan di:", Path(args.out).resolve())


if __name__ == "__main__":
    main()
