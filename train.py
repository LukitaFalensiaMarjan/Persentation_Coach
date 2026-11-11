"""
train.py
Melatih model klasifikasi gestur (YOLO11-cls) lalu menguji di data test.
Otomatis memakai GPU NVIDIA kalau ada, kalau tidak memakai CPU.

Contoh:
  python train.py --data ..\\gesture_rf
  python train.py --data ..\\gesture_rf --epochs 50 --batch 16
Hasil model terbaik disalin ke:  models\\gesture_best.pt
"""
import argparse
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder dataset (berisi train/ val/ test/)")
    ap.add_argument("--model", default="yolo11n-cls.pt", help="model awal (n=paling ringan)")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--patience", type=int, default=10, help="berhenti jika tidak membaik N epoch")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--name", default="gesture")
    args = ap.parse_args()

    data = Path(args.data)
    # export Roboflow memakai nama "valid"; Ultralytics/skrip ini memakai "val"
    if not (data / "val").is_dir() and (data / "valid").is_dir():
        (data / "valid").rename(data / "val")
        print("Folder 'valid' (format Roboflow) diganti nama menjadi 'val'.")
    for split in ("train", "val"):
        if not (data / split).is_dir():
            raise SystemExit(f"Folder {data / split} tidak ditemukan.")

    if torch.cuda.is_available():
        device = 0
        print("GPU terdeteksi:", torch.cuda.get_device_name(0))
    else:
        device = "cpu"
        print("GPU NVIDIA tidak terdeteksi -> training memakai CPU (lebih lama).")

    model = YOLO(args.model)
    model.train(
        data=str(data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        patience=args.patience,
        workers=args.workers,
        project="runs/classify",
        name=args.name,
        fliplr=0.5,   # flip kiri-kanan: arti gestur tidak berubah
        plots=True,
    )

    best_path = Path(model.trainer.best)
    print("\nModel terbaik:", best_path)

    if (data / "test").is_dir():
        best = YOLO(str(best_path))
        m = best.val(data=str(data), split="test", imgsz=args.imgsz, device=device, plots=True)
        print(f"\nAkurasi data TEST  top-1: {m.top1:.3f}   top-5: {m.top5:.3f}")

    Path("models").mkdir(exist_ok=True)
    shutil.copy2(best_path, "models/gesture_best.pt")
    print("Disalin ke: models/gesture_best.pt")
    print("Lihat grafik & confusion matrix di folder:", best_path.parent.parent)


if __name__ == "__main__":  # wajib di Windows agar multiprocessing aman
    main()