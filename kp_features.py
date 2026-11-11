"""
kp_features.py
Mengubah 17 keypoint YOLO-pose menjadi fitur angka yang TIDAK bergantung pada
latar belakang, warna baju, pencahayaan, posisi, atau jarak orang ke kamera,
plus aturan geometri untuk kelas yang sulit dipelajari model.

Fitur (52 angka):
  - 17 keypoint (x, y) relatif terhadap titik tengah bahu, dibagi panjang badan
  - 17 confidence keypoint (mis. hidung tidak terlihat saat membelakangi)
  - 1 fitur arah badan: posisi bahu kiri vs bahu kanan
"""
import numpy as np

# index keypoint COCO
NOSE, L_EYE, R_EYE, L_EAR, R_EAR = 0, 1, 2, 3, 4
L_SH, R_SH, L_EL, R_EL, L_WR, R_WR = 5, 6, 7, 8, 9, 10
L_HIP, R_HIP = 11, 12

N_FEATURES = 17 * 2 + 17 + 1


def body_scale(xy, vis):
    """Panjang badan (bahu-pinggul) dalam piksel; cadangan: lebar bahu x 1.5."""
    scale = 0.0
    if vis[L_SH] and vis[R_SH] and vis[L_HIP] and vis[R_HIP]:
        scale = float(np.linalg.norm((xy[L_SH] + xy[R_SH]) / 2 - (xy[L_HIP] + xy[R_HIP]) / 2))
    elif vis[L_SH] and vis[L_HIP]:
        scale = float(np.linalg.norm(xy[L_SH] - xy[L_HIP]))
    elif vis[R_SH] and vis[R_HIP]:
        scale = float(np.linalg.norm(xy[R_SH] - xy[R_HIP]))
    if scale < 1e-3 and vis[L_SH] and vis[R_SH]:
        scale = float(np.linalg.norm(xy[L_SH] - xy[R_SH])) * 1.5
    return scale


def features(xy, conf, min_conf=0.3):
    """xy: (17,2) piksel, conf: (17,). Mengembalikan array (52,) atau None jika bahu tidak terlihat."""
    xy = np.asarray(xy, dtype=np.float32)
    conf = np.asarray(conf, dtype=np.float32)
    vis = conf >= min_conf
    if not (vis[L_SH] and vis[R_SH]):
        return None

    mid_sh = (xy[L_SH] + xy[R_SH]) / 2
    scale = 0.0
    if vis[L_HIP] and vis[R_HIP]:
        mid_hip = (xy[L_HIP] + xy[R_HIP]) / 2
        scale = float(np.linalg.norm(mid_sh - mid_hip))
    if scale < 1e-3:
        scale = max(float(np.linalg.norm(xy[L_SH] - xy[R_SH])) * 1.5, 1e-3)

    rel = (xy - mid_sh) / scale
    rel[~vis] = 0.0
    facing = (xy[L_SH, 0] - xy[R_SH, 0]) / scale              # >0 menghadap, <0 membelakangi
    return np.concatenate([rel.flatten(), conf, [facing]]).astype(np.float32)


def fold_info(xy, conf, min_conf=0.3):
    """Ukuran untuk tangan terlipat.
    lipat : jarak terjauh pergelangan tangan ke siku SEBERANGNYA / panjang badan (kecil = terlipat)
    silang: 1.0 jika kedua pergelangan tangan menyilang melewati garis tengah badan, di area dada
    Mengembalikan dict (bisa kosong jika keypoint kurang)."""
    xy = np.asarray(xy, dtype=np.float32)
    conf = np.asarray(conf, dtype=np.float32)
    vis = conf >= min_conf
    out = {}
    if not (vis[L_SH] and vis[R_SH] and vis[L_WR] and vis[R_WR]):
        return out
    scale = body_scale(xy, vis)
    if scale < 1e-3:
        return out

    if vis[L_EL] and vis[R_EL]:
        d1 = np.linalg.norm(xy[L_WR] - xy[R_EL])
        d2 = np.linalg.norm(xy[R_WR] - xy[L_EL])
        out["lipat"] = float(max(d1, d2) / scale)

    mid_x = (xy[L_SH, 0] + xy[R_SH, 0]) / 2
    side = 1.0 if xy[L_SH, 0] > xy[R_SH, 0] else -1.0          # sisi bahu kiri di gambar
    sh_y = (xy[L_SH, 1] + xy[R_SH, 1]) / 2
    chest = all(sh_y < xy[w, 1] < sh_y + 0.85 * scale for w in (L_WR, R_WR))
    crossed = ((xy[L_WR, 0] - mid_x) * side < 0) and ((xy[R_WR, 0] - mid_x) * side > 0)
    out["silang"] = 1.0 if (crossed and chest) else 0.0
    return out


def rule_label(xy, conf, face_t=0.35, facing_t=-0.15, arm_t=0.8, fold_t=0.45, min_conf=0.5):
    """Aturan geometri, dicek berurutan. Mengembalikan (label atau None, info debug).

      membelakangi    : wajah tidak terlihat padahal bahu terlihat, ATAU urutan bahu terbalik
      tangan_terlipat : pergelangan dekat siku seberang (lipat < fold_t),
                        ATAU tangan menyilang di dada dan lipat < 1.6 x fold_t
      menunjuk_slide  : pergelangan tangan jauh ke samping dari bahunya (> arm_t) di atas pinggul
    """
    xy = np.asarray(xy, dtype=np.float32)
    conf = np.asarray(conf, dtype=np.float32)
    vis = conf >= min_conf
    info = {"wajah": float(max(conf[NOSE], conf[L_EYE], conf[R_EYE]))}

    if not (vis[L_SH] or vis[R_SH]):
        return None, info
    scale = body_scale(xy, vis)
    if scale < 1e-3:
        return None, info

    # 1) membelakangi
    facing = None
    if vis[L_SH] and vis[R_SH]:
        facing = float((xy[L_SH, 0] - xy[R_SH, 0]) / scale)
        info["arah"] = facing
    if info["wajah"] < face_t or (facing is not None and facing < facing_t):
        return "membelakangi", info

    # 2) tangan_terlipat (memakai confidence lebih longgar: tangan sering tertutup lengan)
    fi = fold_info(xy, conf, min_conf=0.3)
    info.update(fi)
    lipat = fi.get("lipat")
    if lipat is not None and (lipat < fold_t or (fi.get("silang") and lipat < 1.6 * fold_t)):
        return "tangan_terlipat", info

    # 3) menunjuk_slide
    hip_y = None
    if vis[L_HIP] or vis[R_HIP]:
        hip_y = float(np.mean([xy[i, 1] for i in (L_HIP, R_HIP) if vis[i]]))
    best = 0.0
    for sh, wr in ((L_SH, L_WR), (R_SH, R_WR)):
        if vis[sh] and vis[wr]:
            ext = abs(float(xy[wr, 0] - xy[sh, 0])) / scale
            if hip_y is None or xy[wr, 1] < hip_y:
                best = max(best, ext)
    info["lengan"] = best
    if best > arm_t:
        return "menunjuk_slide", info

    return None, info


def keypoints_of(result, i):
    kp = result.keypoints
    xy = kp.xy[i].cpu().numpy()
    conf = kp.conf[i].cpu().numpy() if kp.conf is not None else np.ones(17, np.float32)
    return xy, conf


def largest_person(result):
    """Index orang dengan kotak terbesar dari hasil YOLO, atau None."""
    if result.boxes is None or len(result.boxes) == 0 or result.keypoints is None:
        return None
    xyxy = result.boxes.xyxy.cpu().numpy()
    areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
    return int(areas.argmax())


def features_from_result(result, min_conf=0.3):
    """Fitur dari hasil YOLO-pose (orang terbesar). None jika tidak ada orang / bahu tidak terlihat."""
    i = largest_person(result)
    if i is None:
        return None
    xy, conf = keypoints_of(result, i)
    return features(xy, conf, min_conf)
