"""Server web Persentation Coach: auth, profil, halaman statis. Jalankan: python -m uvicorn web.main:app --reload"""
import asyncio, hashlib, hmac, json, os, re, secrets, sqlite3, urllib.parse, urllib.request
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data"
UPLOADS = DATA / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
load_dotenv(ROOT.parent / ".env")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
COOKIE = "pc_session"
SESSION_DAYS = 14

app = FastAPI(title="Persentation Coach")


# ---------- database ----------
def db():
    con = sqlite3.connect(DATA / "app.db")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE,
      password_hash TEXT, google_sub TEXT UNIQUE, nama TEXT NOT NULL DEFAULT '',
      hp TEXT NOT NULL DEFAULT '', alamat TEXT NOT NULL DEFAULT '', foto TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sessions(
      token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS latihan(
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      dibuat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, total INTEGER NOT NULL, hasil TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS chat(
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      peran TEXT NOT NULL, isi TEXT NOT NULL, dibuat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS telegram_tautan(
      kode TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      dibuat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    kolom = [r[1] for r in con.execute("PRAGMA table_info(users)")]
    if "telegram_chat_id" not in kolom:
        con.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT")
    if "email_verified" not in kolom:  # akun lama dianggap sudah terverifikasi (default 1); pendaftaran baru diset 0 saat insert
        con.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")
    con.execute("CREATE TABLE IF NOT EXISTS verifikasi(kode TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "dibuat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")  # kode disimpan sebagai hash sha256
    con.execute("CREATE TABLE IF NOT EXISTS reset_password(kode TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "dibuat TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    con.commit(); con.close()


init_db()


# ---------- password & sesi ----------
def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + h.hex()


def check_pw(pw: str, stored: str | None) -> bool:
    if not stored:
        return False
    salt, h = stored.split("$")
    cand = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(cand.hex(), h)


def new_session(res: Response, user_id: int):
    token = secrets.token_urlsafe(32)
    con = db()
    con.execute("DELETE FROM sessions WHERE created_at < datetime('now', ?)", (f"-{SESSION_DAYS} days",))
    con.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, user_id))
    con.commit(); con.close()
    res.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_DAYS * 86400)


def public(u: sqlite3.Row) -> dict:
    return {k: u[k] for k in ("id", "username", "email", "nama", "hp", "alamat", "foto")} | {"punya_password": bool(u["password_hash"])}


def user_by_token(token: str | None):
    if not token:
        return None
    con = db()
    u = con.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.created_at >= datetime('now', ?)",
        (token, f"-{SESSION_DAYS} days")).fetchone()
    con.close()
    return u


def current_user(pc_session: str | None = Cookie(None)):
    u = user_by_token(pc_session)
    if not u:
        raise HTTPException(401, "Belum masuk atau sesi berakhir")
    return u


# ---------- validasi ----------
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_username(v: str) -> str:
    v = v.strip()
    if v != v.lower():
        raise HTTPException(422, "Username harus huruf kecil semua")
    if not USERNAME_RE.match(v):
        raise HTTPException(422, "Username 3-20 karakter: huruf kecil, angka, garis bawah")
    return v


def cek_password(pw: str):
    if len(pw) < 8 or not (re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw) and re.search(r"\d", pw)):
        raise HTTPException(422, "Password minimal 8 karakter dan harus gabungan huruf besar, huruf kecil, dan angka")


class Daftar(BaseModel):
    nama: str
    username: str
    email: str
    password: str


class Masuk(BaseModel):
    username: str
    password: str


class GoogleIn(BaseModel):
    credential: str


# ---------- API auth ----------
@app.get("/api/config")
def config():
    return {"google_client_id": GOOGLE_CLIENT_ID}


@app.post("/api/daftar")
def daftar(d: Daftar, res: Response):
    username = clean_username(d.username)
    nama, email = d.nama.strip(), d.email.strip().lower()
    if not nama or len(nama) > 80:
        raise HTTPException(422, "Nama wajib diisi (maks 80 karakter)")
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Format email tidak valid")
    cek_password(d.password)
    con = db()
    try:
        # pendaftaran yang tidak diverifikasi lebih dari 10 menit boleh ditimpa (mis. salah ketik email)
        con.execute("DELETE FROM users WHERE email_verified=0 AND (username=? OR email=?) AND created_at < datetime('now','-10 minutes')", (username, email))
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise HTTPException(409, "Username sudah dipakai, pilih yang lain")
        if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "Email sudah terdaftar")
        cur = con.execute("INSERT INTO users(username,email,password_hash,nama,email_verified) VALUES(?,?,?,?,0)",
                          (username, email, hash_pw(d.password), nama))
        con.commit()
    except sqlite3.IntegrityError:  # balapan dua pendaftaran bersamaan
        raise HTTPException(409, "Username atau email sudah terdaftar")
    finally:
        con.close()
    # belum masuk: akun baru aktif setelah email diverifikasi lewat tautan yang dikirim
    return {"ok": True, "perlu_verifikasi": True, "email": email, "terkirim": kirim_verifikasi(cur.lastrowid, email, nama)}


def kirim_verifikasi(uid: int, email: str, nama: str) -> bool:
    from . import surel
    kode = secrets.token_urlsafe(32)
    con = db()
    con.execute("DELETE FROM verifikasi WHERE user_id=? OR dibuat < datetime('now','-1 day')", (uid,))
    con.execute("INSERT INTO verifikasi(kode,user_id) VALUES(?,?)", (hashlib.sha256(kode.encode()).hexdigest(), uid))
    con.commit(); con.close()
    return surel.kirim(email, nama, f"{os.getenv('BASE_URL', 'http://localhost:8000').rstrip('/')}/verifikasi?kode={kode}")


class KodeIn(BaseModel):
    kode: str


class EmailIn(BaseModel):
    email: str = ""
    username: str = ""


@app.post("/api/verifikasi")
def verifikasi(d: KodeIn, res: Response):
    h = hashlib.sha256(d.kode.encode()).hexdigest()
    con = db()
    r = con.execute("SELECT user_id FROM verifikasi WHERE kode=? AND dibuat >= datetime('now','-1 day')", (h,)).fetchone()
    if not r:
        con.close()
        raise HTTPException(400, "Tautan verifikasi tidak valid atau sudah kedaluwarsa")
    con.execute("UPDATE users SET email_verified=1 WHERE id=?", (r["user_id"],))
    con.execute("DELETE FROM verifikasi WHERE user_id=?", (r["user_id"],))
    con.commit(); con.close()
    new_session(res, r["user_id"])  # langsung masuk setelah verifikasi
    return {"ok": True}


@app.post("/api/verifikasi/ulang")
def verifikasi_ulang(d: EmailIn):
    email, uname = d.email.strip().lower(), d.username.strip()
    con = db()
    u = con.execute("SELECT id,nama,email FROM users WHERE ((email=? AND ?!='') OR (username=? AND ?!='')) AND email_verified=0", (email, email, uname, uname)).fetchone()
    baru = u and con.execute("SELECT 1 FROM verifikasi WHERE user_id=? AND dibuat >= datetime('now','-60 seconds')", (u["id"],)).fetchone()
    con.close()
    if baru:
        raise HTTPException(429, "Tunggu satu menit sebelum meminta email lagi")
    terkirim = kirim_verifikasi(u["id"], u["email"], u["nama"]) if u else True  # jawaban sama untuk email yang tidak terdaftar
    return {"ok": True, "terkirim": terkirim}


# ---------- lupa & reset password ----------
class LupaIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    kode: str
    password: str


@app.post("/api/lupa-password")
def lupa_password(d: LupaIn):
    """Jawaban selalu sama agar tidak membocorkan email mana yang terdaftar. Maks satu email per 60 detik per akun."""
    from . import surel
    email = d.email.strip().lower()
    con = db()
    u = con.execute("SELECT id,nama,email FROM users WHERE email=?", (email,)).fetchone()
    baru = u and con.execute("SELECT 1 FROM reset_password WHERE user_id=? AND dibuat >= datetime('now','-60 seconds')", (u["id"],)).fetchone()
    kirim = bool(u and not baru)
    if kirim:
        kode = secrets.token_urlsafe(32)
        con.execute("DELETE FROM reset_password WHERE user_id=? OR dibuat < datetime('now','-1 day')", (u["id"],))
        con.execute("INSERT INTO reset_password(kode,user_id) VALUES(?,?)", (hashlib.sha256(kode.encode()).hexdigest(), u["id"]))
        con.commit()
    con.close()
    if kirim:
        surel.kirim_reset(u["email"], u["nama"] or u["email"], f"{os.getenv('BASE_URL', 'http://localhost:8000').rstrip('/')}/reset-password?kode={kode}")
    return {"ok": True}


@app.get("/api/reset-password/cek")
def reset_cek(kode: str):
    con = db()
    r = con.execute("SELECT 1 FROM reset_password WHERE kode=? AND dibuat >= datetime('now','-1 hour')", (hashlib.sha256(kode.encode()).hexdigest(),)).fetchone()
    con.close()
    return {"valid": bool(r)}


@app.post("/api/reset-password")
def reset_password(d: ResetIn):
    cek_password(d.password)
    con = db()
    r = con.execute("SELECT user_id FROM reset_password WHERE kode=? AND dibuat >= datetime('now','-1 hour')", (hashlib.sha256(d.kode.encode()).hexdigest(),)).fetchone()
    if not r:
        con.close()
        raise HTTPException(400, "Tautan reset tidak valid atau sudah kedaluwarsa")
    uid = r["user_id"]
    con.execute("UPDATE users SET password_hash=?, email_verified=1 WHERE id=?", (hash_pw(d.password), uid))  # lewat email = pemilik email terbukti
    con.execute("DELETE FROM reset_password WHERE user_id=?", (uid,))
    con.execute("DELETE FROM sessions WHERE user_id=?", (uid,))  # keluarkan dari semua perangkat
    con.commit(); con.close()
    return {"ok": True}


@app.get("/api/username/{nama}")
def username_tersedia(nama: str):
    con = db()
    ada = con.execute("SELECT 1 FROM users WHERE username=?", (nama,)).fetchone()
    con.close()
    return {"tersedia": bool(USERNAME_RE.match(nama)) and not ada}


@app.post("/api/masuk")
def masuk(d: Masuk, res: Response):
    con = db()
    u = con.execute("SELECT * FROM users WHERE username=?", (d.username.strip().lower(),)).fetchone()
    con.close()
    # hash dummy agar waktu respons tidak membocorkan keberadaan username
    ok = check_pw(d.password, u["password_hash"] if u else hash_pw("dummy"))
    if not (u and ok):
        raise HTTPException(401, "Username atau password salah")
    if not u["email_verified"]:
        raise HTTPException(403, "Email belum diverifikasi. Cek kotak masuk emailmu, atau kirim ulang tautan verifikasi.")
    new_session(res, u["id"])
    return {"ok": True}


@app.post("/api/google")
def google(d: GoogleIn, res: Response):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Login Google belum dikonfigurasi (GOOGLE_CLIENT_ID kosong)")
    try:
        url = "https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(d.credential)
        info = json.load(urllib.request.urlopen(url, timeout=10))
    except Exception:
        raise HTTPException(401, "Token Google tidak valid")
    if info.get("aud") != GOOGLE_CLIENT_ID or info.get("email_verified") not in ("true", True):
        raise HTTPException(401, "Token Google tidak valid")
    sub, email = info["sub"], info["email"].lower()
    con = db()
    u = con.execute("SELECT * FROM users WHERE google_sub=?", (sub,)).fetchone()
    if not u:
        u = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u:  # akun email yang sama: tautkan Google
            con.execute("UPDATE users SET google_sub=?, email_verified=1 WHERE id=?", (sub, u["id"]))  # email sudah diverifikasi Google
        else:
            base = re.sub(r"[^a-z0-9_]", "", email.split("@")[0].lower())[:14] or "user"
            username = base
            while con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                username = f"{base}{secrets.randbelow(10**5)}"
            con.execute("INSERT INTO users(username,email,google_sub,nama) VALUES(?,?,?,?)",
                        (username, email, sub, info.get("name", "")))
        con.commit()
        u = con.execute("SELECT * FROM users WHERE google_sub=?", (sub,)).fetchone()
    con.close()
    new_session(res, u["id"])
    return {"ok": True}


@app.post("/api/keluar")
def keluar(res: Response, pc_session: str | None = Cookie(None)):
    if pc_session:
        con = db(); con.execute("DELETE FROM sessions WHERE token=?", (pc_session,)); con.commit(); con.close()
    res.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/saya")
def saya(u=Depends(current_user)):
    return public(u)


# ---------- profil ----------
MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"RIFF": "webp"}


@app.put("/api/profil")
async def ubah_profil(nama: str = Form(...), username: str = Form(...), email: str = Form(""),
                      hp: str = Form(""), alamat: str = Form(""), foto: UploadFile | None = File(None),
                      u=Depends(current_user)):
    username = clean_username(username)
    nama, email, hp, alamat = nama.strip(), email.strip().lower(), hp.strip(), alamat.strip()
    if not nama or len(nama) > 80:
        raise HTTPException(422, "Nama wajib diisi (maks 80 karakter)")
    if email and not EMAIL_RE.match(email):
        raise HTTPException(422, "Format email tidak valid")
    if hp and not re.match(r"^[0-9+\-\s]{6,20}$", hp):
        raise HTTPException(422, "Nomor HP tidak valid")
    if len(alamat) > 300:
        raise HTTPException(422, "Alamat maks 300 karakter")
    con = db()
    pakai = con.execute("SELECT 1 FROM users WHERE username=? AND id!=?", (username, u["id"])).fetchone()
    con.close()
    if pakai:
        raise HTTPException(409, "Username sudah dipakai, pilih yang lain")
    fname = u["foto"]
    if foto and foto.filename:
        raw = await foto.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise HTTPException(422, "Foto maks 2 MB")
        ext = next((e for m, e in MAGIC.items() if raw.startswith(m)), None)
        if not ext or (ext == "webp" and raw[8:12] != b"WEBP"):
            raise HTTPException(422, "Foto harus JPG, PNG, atau WEBP")
        fname = f"{secrets.token_hex(12)}.{ext}"
        (UPLOADS / fname).write_bytes(raw)
        if u["foto"]:
            (UPLOADS / u["foto"]).unlink(missing_ok=True)
    con = db()
    try:
        con.execute("UPDATE users SET nama=?,username=?,email=?,hp=?,alamat=?,foto=? WHERE id=?",
                    (nama, username, u["email"] or email or None, hp, alamat, fname, u["id"]))  # email terverifikasi tidak bisa diganti dari sini
        con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username atau email sudah dipakai")
    finally:
        con.close()
    return {"ok": True}


# ---------- latihan ----------
def ambil_latihan(uid: int, lid: int) -> dict:
    con = db()
    r = con.execute("SELECT * FROM latihan WHERE id=? AND user_id=?", (lid, uid)).fetchone()
    con.close()
    if not r:
        raise HTTPException(404, "Sesi latihan tidak ditemukan")
    return {"id": r["id"], "dibuat": r["dibuat"], "total": r["total"], **json.loads(r["hasil"])}


@app.get("/api/latihan")
def riwayat(u=Depends(current_user)):
    con = db()
    rows = con.execute("SELECT id,dibuat,total,hasil FROM latihan WHERE user_id=? ORDER BY id DESC LIMIT 100", (u["id"],)).fetchall()
    con.close()
    out = []
    for r in rows:
        h = json.loads(r["hasil"])
        out.append({"id": r["id"], "dibuat": r["dibuat"], "total": r["total"], "durasi": h["durasi_aktual"], "skor": h["skor"]})
    return out


@app.get("/api/latihan/{lid}")
def detail_latihan(lid: int, u=Depends(current_user)):
    return ambil_latihan(u["id"], lid)


@app.websocket("/ws/latihan")
async def ws_latihan(ws: WebSocket):
    """Klien kirim {"type":"mulai","durasi":detik}, lalu frame JPEG (biner) satu per satu setelah menerima balasan sebelumnya,
    dan {"type":"selesai"}. Server membalas label + keypoint per frame dan hasil akhir."""
    origin = ws.headers.get("origin", "")
    if origin and urllib.parse.urlparse(origin).netloc != ws.headers.get("host", ""):
        await ws.close(code=1008); return
    u = user_by_token(ws.cookies.get(COOKIE))
    await ws.accept()
    if not u:
        await ws.send_json({"type": "error", "pesan": "Belum masuk"}); await ws.close(); return
    sesi = None
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes") is not None:
                if sesi:
                    try:
                        out = await asyncio.to_thread(sesi.frame, msg["bytes"])
                    except ValueError:
                        out = {"label": "tidak_terlihat", "kp": [], "dbg": {}, "peringatan": None}
                    await ws.send_json({"type": "frame", **out})
            elif msg.get("text"):
                d = json.loads(msg["text"])
                if d.get("type") == "mulai":
                    from . import engine
                    sesi = engine.Sesi(max(10, min(1800, int(d.get("durasi", 60)))))
                    await asyncio.to_thread(engine.models)  # muat model sekali, lalu beri tahu klien
                    await ws.send_json({"type": "siap"})
                elif d.get("type") == "selesai" and sesi:
                    durasi, s, sesi = sesi.durasi, sesi, None
                    try:
                        hasil = s.selesai()
                    except ValueError as e:
                        await ws.send_json({"type": "error", "pesan": str(e)}); continue
                    hasil["durasi_target"] = durasi
                    con = db()
                    cur = con.execute("INSERT INTO latihan(user_id,total,hasil) VALUES(?,?,?)", (u["id"], hasil["total"], json.dumps(hasil)))
                    con.commit(); lid = cur.lastrowid; con.close()
                    await ws.send_json({"type": "hasil", "hasil": ambil_latihan(u["id"], lid)})
    except WebSocketDisconnect:
        pass


@app.get("/api/latihan/{lid}/pdf")
def pdf_latihan(lid: int, u=Depends(current_user)):
    from . import laporan
    data = laporan.buat_pdf(dict(u), ambil_latihan(u["id"], lid))
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="laporan_latihan_{lid}.pdf"'})


# ---------- telegram ----------
@app.on_event("startup")
def start_bot():
    from . import tele
    tele.mulai()


@app.get("/api/telegram/status")
def tg_status(u=Depends(current_user)):
    from . import tele
    return {"dikonfigurasi": tele.aktif(), "terhubung": bool(u["telegram_chat_id"])}


@app.get("/api/telegram/tautan")
def tg_tautan(u=Depends(current_user)):
    from . import tele
    if not tele.aktif():
        raise HTTPException(503, "Bot Telegram belum dikonfigurasi (isi TELEGRAM_BOT_TOKEN di file .env)")
    try:
        bot = tele.username_bot()
    except Exception:
        raise HTTPException(502, "Tidak bisa menghubungi Telegram. Periksa token bot dan koneksi internet.")
    kode = secrets.token_urlsafe(9)
    con = db()
    con.execute("DELETE FROM telegram_tautan WHERE user_id=? OR dibuat < datetime('now','-30 minutes')", (u["id"],))
    con.execute("INSERT INTO telegram_tautan(kode,user_id) VALUES(?,?)", (kode, u["id"]))
    con.commit(); con.close()
    return {"url": f"https://t.me/{bot}?start={kode}", "kode": kode}


@app.post("/api/telegram/putus")
def tg_putus(u=Depends(current_user)):
    con = db(); con.execute("UPDATE users SET telegram_chat_id=NULL WHERE id=?", (u["id"],)); con.commit(); con.close()
    return {"ok": True}


@app.post("/api/latihan/{lid}/telegram")
def kirim_telegram(lid: int, u=Depends(current_user)):
    from . import laporan, tele
    if not tele.aktif():
        raise HTTPException(503, "Bot Telegram belum dikonfigurasi (isi TELEGRAM_BOT_TOKEN di file .env)")
    h = ambil_latihan(u["id"], lid)
    if not u["telegram_chat_id"]:
        raise HTTPException(409, "Akun Telegram belum terhubung")
    try:
        tele.kirim(u["telegram_chat_id"], tele.ringkasan(h))
        tele.kirim_dokumen(u["telegram_chat_id"], laporan.buat_pdf(dict(u), h), f"laporan_latihan_{lid}.pdf", f"Laporan latihan: skor {h['total']}/100")
    except Exception:
        raise HTTPException(502, "Gagal mengirim ke Telegram. Pastikan kamu belum memblokir bot.")
    return {"ok": True}


# ---------- chatbot ----------
def _sesi_terbaru(uid: int, n: int = 5) -> list:
    con = db()
    rows = con.execute("SELECT hasil, total FROM latihan WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, n)).fetchall()
    con.close()
    return [{**json.loads(r["hasil"]), "total": r["total"]} for r in rows]


class ChatIn(BaseModel):
    pesan: str


@app.get("/api/chat")
def chat_riwayat(u=Depends(current_user)):
    con = db()
    rows = con.execute("SELECT peran,isi FROM chat WHERE user_id=? ORDER BY id DESC LIMIT 50", (u["id"],)).fetchall()
    con.close()
    from . import chat
    return {"pesan": [{"peran": r["peran"], "isi": r["isi"]} for r in reversed(rows)], "llm": chat.llm_tersedia()}


@app.post("/api/chat")
def chat_kirim(d: ChatIn, u=Depends(current_user)):
    from . import chat
    con = db()
    terpakai = con.execute("SELECT COUNT(*) FROM chat WHERE user_id=? AND peran='user' AND dibuat >= datetime('now','-1 day')", (u["id"],)).fetchone()[0]
    hist = [(r["peran"], r["isi"]) for r in reversed(con.execute("SELECT peran,isi FROM chat WHERE user_id=? ORDER BY id DESC LIMIT 6", (u["id"],)).fetchall())]
    aksi = None
    if terpakai < chat.BATAS_HARIAN and len(d.pesan.strip()) <= chat.MAKS_PANJANG and chat.niat_telegram(d.pesan):
        from . import tele  # bantuan hubungkan Telegram: jawaban tetap, popup menampilkan QR bila perlu
        jawab, simpan = chat.jawab_telegram(bool(u["telegram_chat_id"]), tele.aktif()), True
        aksi = "telegram" if tele.aktif() and not u["telegram_chat_id"] else None
    else:
        jawab, simpan = chat.proses(u["nama"], d.pesan, _sesi_terbaru(u["id"]), hist, terpakai)
    if simpan:
        con.execute("INSERT INTO chat(user_id,peran,isi) VALUES(?,?,?)", (u["id"], "user", d.pesan.strip()))
        con.execute("INSERT INTO chat(user_id,peran,isi) VALUES(?,?,?)", (u["id"], "bot", jawab))
        con.commit()
    con.close()
    return {"jawab": jawab, "aksi": aksi, "sisa": max(0, chat.BATAS_HARIAN - terpakai - (1 if simpan else 0))}


@app.delete("/api/chat")
def chat_hapus(u=Depends(current_user)):
    con = db(); con.execute("DELETE FROM chat WHERE user_id=?", (u["id"],)); con.commit(); con.close()
    return {"ok": True}


# ---------- halaman ----------
@app.middleware("http")
async def pakai_localhost(request, call_next):
    """Uvicorn mencetak http://127.0.0.1:8000, tetapi login Google dan izin kamera didaftarkan untuk 'localhost'; alihkan agar tidak origin_mismatch."""
    if request.headers.get("host", "").startswith("127.0.0.1"):
        return RedirectResponse(str(request.url).replace("127.0.0.1", "localhost", 1), status_code=307)
    return await call_next(request)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "static" / "img" / "logo-120.png", media_type="image/png")


PAGES = {"/": "index.html", "/masuk": "masuk.html", "/daftar": "daftar.html", "/profil": "profil.html",
         "/latihan": "latihan.html", "/riwayat": "riwayat.html", "/verifikasi": "verifikasi.html",
         "/lupa-password": "lupa.html", "/reset-password": "reset.html"}
for route, fn in PAGES.items():
    app.add_api_route(route, (lambda f=fn: FileResponse(ROOT / "static" / f)), include_in_schema=False)
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
