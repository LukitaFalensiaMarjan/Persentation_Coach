"""
train_kp.py
Melatih classifier gestur dari fitur keypoint (Random Forest). Training hanya beberapa detik di CPU.

Pemakaian:
  pip install scikit-learn
  python train_kp.py --data kp_data.npz
Hasil: models/kp_rf.joblib  +  models/kp_confusion_matrix.png
"""
import argparse
from pathlib import Path

import joblib
import matplotlib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def evaluate(model, X, y, classes, title):
    pred = model.predict(X)
    print(f"\n=== {title}: akurasi {accuracy_score(y, pred):.3f}  ({len(y)} gambar) ===")
    print(classification_report(y, pred, labels=range(len(classes)),
                                target_names=classes, digits=3, zero_division=0))
    return pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="kp_data.npz")
    ap.add_argument("--out", default="models/kp_rf.joblib")
    ap.add_argument("--trees", type=int, default=300)
    args = ap.parse_args()

    d = np.load(args.data, allow_pickle=False)
    classes = [str(c) for c in d["classes"]]
    X_tr, y_tr = d["X_train"], d["y_train"]
    print("Kelas:", classes)
    print("Jumlah train per kelas:", dict(zip(classes, np.bincount(y_tr, minlength=len(classes)))))

    model = RandomForestClassifier(n_estimators=args.trees, class_weight="balanced",
                                   min_samples_leaf=2, n_jobs=-1, random_state=42)
    model.fit(X_tr, y_tr)

    last_split, last_pred = None, None
    for split in ("val", "test"):
        if f"X_{split}" in d and len(d[f"y_{split}"]):
            last_pred = evaluate(model, d[f"X_{split}"], d[f"y_{split}"], classes, split.upper())
            last_split = split

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "classes": classes}, args.out)
    print("Model tersimpan:", args.out)

    if last_split:
        fig, ax = plt.subplots(figsize=(8, 7))
        ConfusionMatrixDisplay.from_predictions(
            d[f"y_{last_split}"], last_pred, labels=range(len(classes)),
            display_labels=classes, xticks_rotation=45, ax=ax, colorbar=False)
        ax.set_title(f"Confusion matrix keypoint RF ({last_split})")
        fig.tight_layout()
        png = Path(args.out).parent / "kp_confusion_matrix.png"
        fig.savefig(png, dpi=120)
        print("Confusion matrix:", png)


if __name__ == "__main__":
    main()
