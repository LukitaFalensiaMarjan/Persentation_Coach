"""Laporan PDF satu halaman (A4) dari hasil latihan + profil user. Memakai matplotlib (sudah terpasang), tanpa file perantara.
Tidak ada frame video di laporan, jadi tidak ada wajah presenter yang perlu di-blur; hanya foto profil milik user sendiri."""
import io
import textwrap
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle
from PIL import Image

from .engine import NAMA

INK, SOFT, GOLD, BG = "#161616", "#6b6862", "#e9b75f", "#f4f3f0"
ASPEK = {"orientasi": "Orientasi ke audiens", "gestur": "Gestur", "postur": "Postur kepala", "gerak": "Pergerakan"}
BURUK = {"menunduk", "membelakangi", "tangan_terlipat", "tangan_tersembunyi"}
UPLOADS = Path(__file__).resolve().parent.parent / "data" / "uploads"


def _mmss(s):
    return f"{int(s // 60)}:{int(round(s % 60)):02d}"


def _verdict(t):
    return "Sangat baik" if t >= 80 else "Baik" if t >= 65 else "Cukup" if t >= 50 else "Perlu banyak latihan"


def buat_pdf(user: dict, h: dict, fmt: str = "pdf") -> bytes:  # fmt="png" hanya untuk pratinjau saat pengembangan
    fig = Figure(figsize=(8.27, 11.69), facecolor=BG)
    # kop
    fig.patches.append(Rectangle((0, 0.915), 1, 0.085, transform=fig.transFigure, color="#1b1a19"))
    fig.text(0.06, 0.962, "PERSENTATION COACH", color="white", fontsize=15, fontweight="bold", va="center")
    fig.text(0.06, 0.935, "Laporan latihan presentasi", color=GOLD, fontsize=9.5, va="center")
    fig.text(0.94, 0.95, str(h["dibuat"])[:16] + " UTC", color="#bdb9b0", fontsize=8.5, ha="right", va="center")

    # profil
    foto_x = 0.06
    if user.get("foto") and (UPLOADS / user["foto"]).exists():
        try:
            im = Image.open(UPLOADS / user["foto"]).convert("RGB")
            s = min(im.size); im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((160, 160))
            ax = fig.add_axes([0.06, 0.815, 0.09, 0.063]); ax.imshow(im); ax.axis("off")
            ax.add_patch(Circle((80, 80), 80, transform=ax.transData, fill=False)); foto_x = 0.17
        except OSError:
            pass
    fig.text(foto_x, 0.866, user.get("nama") or user["username"], fontsize=15, fontweight="bold", color=INK)
    info = [f"@{user['username']}"] + [v for v in (user.get("email"), user.get("hp"), user.get("alamat")) if v]
    fig.text(foto_x, 0.845, "  ·  ".join(info)[:110], fontsize=8.5, color=SOFT)
    fig.text(foto_x, 0.828, f"Durasi {_mmss(h['durasi_aktual'])} dari target {_mmss(h.get('durasi_target', h['durasi_aktual']))}", fontsize=8.5, color=SOFT)

    # skor total
    ax = fig.add_axes([0.06, 0.64, 0.24, 0.15]); ax.axis("off"); ax.set_xlim(-1.2, 1.2); ax.set_ylim(-1.2, 1.2); ax.set_aspect("equal")
    t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(t), np.sin(t), color="#d8d6d0", lw=9)
    arc = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi * h["total"] / 100, 200)
    ax.plot(np.cos(arc), np.sin(arc), color=GOLD, lw=9, solid_capstyle="round")
    ax.text(0, 0.05, str(h["total"]), ha="center", va="center", fontsize=34, fontweight="bold", color=INK)
    ax.text(0, -0.5, "dari 100", ha="center", fontsize=8, color=SOFT)
    fig.text(0.18, 0.628, _verdict(h["total"]).upper(), ha="center", fontsize=9, fontweight="bold", color=INK)

    # skor per aspek
    ax = fig.add_axes([0.46, 0.65, 0.48, 0.13]); ax.set_facecolor(BG)
    keys = list(h["skor"]); vals = [h["skor"][k] for k in keys]
    ax.barh(range(len(keys)), [100] * len(keys), color="#e3e1db", height=0.5)
    ax.barh(range(len(keys)), vals, color=GOLD, height=0.5)
    ax.set_yticks(range(len(keys)), [ASPEK[k] for k in keys], fontsize=9, color=INK)
    for i, v in enumerate(vals):
        ax.text(101, i, str(v), va="center", fontsize=9, color=INK)
    ax.invert_yaxis(); ax.set_xlim(0, 112); ax.set_xticks([]); [s.set_visible(False) for s in ax.spines.values()]; ax.tick_params(length=0)
    fig.text(0.46, 0.79, "SKOR PER ASPEK", fontsize=8.5, color=SOFT, fontweight="bold")

    # proporsi gestur
    props = sorted(((k, v) for k, v in h["proporsi"].items() if v > 0), key=lambda x: x[1])
    ax = fig.add_axes([0.20, 0.42, 0.34, 0.17]); ax.set_facecolor(BG)
    ax.barh([NAMA[k] for k, _ in props], [v for _, v in props], color=["#55534f" if k in BURUK else GOLD for k, _ in props], height=0.6)
    for i, (_, v) in enumerate(props):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, max(v for _, v in props) * 1.2 if props else 100); ax.set_xticks([]); ax.tick_params(labelsize=8, length=0)
    [s.set_visible(False) for s in ax.spines.values()]
    fig.text(0.06, 0.60, "PROPORSI GESTUR", fontsize=8.5, color=SOFT, fontweight="bold")

    # heatmap posisi
    ax = fig.add_axes([0.62, 0.42, 0.32, 0.17])
    ax.imshow(np.array(h["heatmap"]), cmap=LinearSegmentedColormap.from_list("g", [BG, GOLD, "#6b4a10"]), aspect="auto")
    ax.set_xticks([]); ax.set_yticks([]); [s.set_edgecolor("#d8d6d0") for s in ax.spines.values()]
    fig.text(0.62, 0.60, "POSISI BERDIRI (TAMPAK KAMERA)", fontsize=8.5, color=SOFT, fontweight="bold")

    # timeline
    fig.text(0.06, 0.385, "MOMEN YANG PERLU DIPERBAIKI", fontsize=8.5, color=SOFT, fontweight="bold")
    rows = [f"{_mmss(a)} – {_mmss(b)}   {NAMA.get(l, l)}" for a, b, l in h["timeline"][:9]] or ["Tidak ada momen yang perlu diperbaiki. Bagus!"]
    fig.text(0.06, 0.37, "\n".join(rows), fontsize=9, color=INK, va="top", linespacing=1.7, family="monospace" if h["timeline"] else None)

    # saran
    fig.text(0.06, 0.25, "3 SARAN PERBAIKAN UTAMA", fontsize=8.5, color=SOFT, fontweight="bold")
    y = 0.235
    for i, s in enumerate(h["saran"][:3], 1):
        wrapped = textwrap.fill(s, 100)
        fig.text(0.06, y, f"{i}.", fontsize=10, fontweight="bold", color=GOLD, va="top")
        fig.text(0.09, y, wrapped, fontsize=9.5, color=INK, va="top", linespacing=1.5)
        y -= 0.014 * (wrapped.count("\n") + 1) + 0.03

    fig.text(0.06, 0.03, "Video tidak disimpan; laporan hanya memuat metrik dan timeline hasil analisis keypoint tubuh.", fontsize=7.5, color=SOFT)
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, facecolor=BG, dpi=90)
    return buf.getvalue()
