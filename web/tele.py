"""Bot Telegram: tautan akun lewat deep link, kirim PDF, perintah /laporan /riwayat /progres /latihan, dan konsultasi chatbot.
Memakai Bot API lewat HTTP (stdlib) dengan long polling di thread latar; aktif hanya bila TELEGRAM_BOT_TOKEN diisi."""
import json
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid

TOKEN = lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
_username = None

FOKUS = {
    "orientasi": "Fokus latihan: orientasi. Latih presentasi 2 menit dengan badan selalu menghadap audiens; lirik slide hanya dari samping.",
    "gestur": "Fokus latihan: gestur. Selipkan 3 gerakan tangan terbuka pada poin utama, dan jangan melipat tangan.",
    "postur": "Fokus latihan: postur kepala. Hafalkan 3 poin utama, lalu bicara dengan kepala tegak tanpa melihat catatan.",
    "gerak": "Fokus latihan: pergerakan. Berdiri stabil, lalu melangkah sedikit saat berpindah poin.",
}


PANDUAN = ("Perintah yang bisa kamu pakai:\n"
           "/laporan - kirim PDF laporan sesi latihan terakhir\n"
           "/riwayat - daftar 5 sesi latihan terakhir\n"
           "/progres - bandingkan skor sesi terbaru dengan sebelumnya\n"
           "/latihan - satu fokus latihan dari skor terlemahmu\n"
           "/bantuan - tampilkan panduan ini lagi\n\n"
           "Pesan biasa, misalnya \"kenapa skor gestur saya rendah?\", akan dijawab chatbot berdasarkan data latihanmu. "
           "Chatbot hanya membahas topik presentasi.")
PERINTAH_MENU = [("laporan", "Kirim PDF laporan sesi terakhir"), ("riwayat", "Daftar sesi latihan terakhir"), ("progres", "Bandingkan skor antar-sesi"),
                 ("latihan", "Fokus latihan dari skor terlemah"), ("bantuan", "Panduan penggunaan bot")]


def aktif() -> bool:
    return bool(TOKEN())


def api(metode: str, data: dict | None = None, timeout: int = 40):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN()}/{metode}", json.dumps(data or {}).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))["result"]


def username_bot() -> str:
    global _username
    if _username is None:
        _username = api("getMe")["username"]
    return _username


def kirim(chat_id, teks: str):
    api("sendMessage", {"chat_id": chat_id, "text": teks[:4000]})


ASPEK = {"orientasi": "Orientasi ke audiens", "gestur": "Gestur", "postur": "Postur kepala", "gerak": "Pergerakan"}


def ringkasan(h: dict) -> str:
    """Teks hasil latihan untuk dikirim sebagai chat sebelum file PDF."""
    baris = [f"Hasil latihan #{h['id']} ({str(h['dibuat'])[:16]} UTC)", f"Skor total: {h['total']}/100", ""]
    baris += [f"• {ASPEK[k]}: {v}" for k, v in h["skor"].items()]
    baris += ["", "Saran:"] + [f"{i}. {s}" for i, s in enumerate(h["saran"][:3], 1)]
    return "\n".join(baris)


def kirim_dokumen(chat_id, isi: bytes, nama_file: str, caption: str = ""):
    b = uuid.uuid4().hex
    bagian = b"".join([
        f'--{b}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode(),
        f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{nama_file}"\r\nContent-Type: application/pdf\r\n\r\n'.encode(), isi, f"\r\n--{b}--\r\n".encode()])
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN()}/sendDocument", bagian, {"Content-Type": f"multipart/form-data; boundary={b}"})
    urllib.request.urlopen(req, timeout=60).read()


# ---------- perintah bot (akses data lewat modul main, di-import saat dipakai agar tidak sirkular) ----------
def _user(M, chat_id):
    con = M.db(); u = con.execute("SELECT * FROM users WHERE telegram_chat_id=?", (str(chat_id),)).fetchone(); con.close(); return u


def _sesi(M, uid, n=5):
    con = M.db(); rows = con.execute("SELECT id,dibuat,total,hasil FROM latihan WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, n)).fetchall(); con.close()
    return [{"id": r["id"], "dibuat": r["dibuat"], "total": r["total"], **json.loads(r["hasil"])} for r in rows]


def tangani(pesan: dict):
    from . import main as M, chat as C, laporan
    chat_id, teks = pesan["chat"]["id"], (pesan.get("text") or "").strip()
    if not teks:
        return
    if teks.startswith("/start"):
        kode = teks.split(maxsplit=1)[1] if " " in teks else ""
        con = M.db()
        r = con.execute("SELECT user_id FROM telegram_tautan WHERE kode=? AND dibuat >= datetime('now','-30 minutes')", (kode,)).fetchone() if kode else None
        if r:
            con.execute("UPDATE users SET telegram_chat_id=NULL WHERE telegram_chat_id=?", (str(chat_id),))
            con.execute("UPDATE users SET telegram_chat_id=? WHERE id=?", (str(chat_id), r["user_id"]))
            con.execute("DELETE FROM telegram_tautan WHERE kode=?", (kode,)); con.commit(); con.close()
            return kirim(chat_id, "Akunmu berhasil terhubung ke Persentation Coach!\n\n" + PANDUAN)
        con.close()
        if _user(M, chat_id):  # sudah terhubung, tekan Start lagi: tampilkan panduan
            return kirim(chat_id, "Halo lagi! Akunmu sudah terhubung.\n\n" + PANDUAN)
        return kirim(chat_id, "Halo! Untuk menghubungkan akun, buka aplikasi Persentation Coach, masuk ke Profil lalu tekan \"Hubungkan Telegram\", "
                              "dan pindai QR-nya. Kamu juga bisa minta chatbot di aplikasi: \"bantu hubungkan Telegram\".")
    u = _user(M, chat_id)
    if not u:
        return kirim(chat_id, "Akunmu belum terhubung. Buka aplikasi, masuk ke Profil lalu tekan \"Hubungkan Telegram\" dan pindai QR-nya.")
    sesi = _sesi(M, u["id"])
    cmd = teks.split()[0].split("@")[0].lower()
    if cmd in ("/bantuan", "/help"):
        kirim(chat_id, PANDUAN)
    elif cmd == "/laporan":
        if not sesi:
            return kirim(chat_id, "Belum ada sesi latihan.")
        kirim_dokumen(chat_id, laporan.buat_pdf(dict(u), sesi[0]), f"laporan_{sesi[0]['id']}.pdf", f"Skor {sesi[0]['total']}/100")
    elif cmd == "/riwayat":
        kirim(chat_id, "\n".join(f"#{s['id']}  {s['dibuat'][:16]}  skor {s['total']}" for s in sesi) or "Belum ada sesi latihan.")
    elif cmd == "/progres":
        if len(sesi) < 2:
            return kirim(chat_id, "Butuh minimal 2 sesi untuk membandingkan progres.")
        baris = [f"Skor terbaru {sesi[0]['total']} dibanding sesi sebelumnya {sesi[1]['total']} ({sesi[0]['total'] - sesi[1]['total']:+d})."]
        baris += [f"- {k}: {sesi[0]['skor'][k]} ({sesi[0]['skor'][k] - sesi[1]['skor'][k]:+d})" for k in sesi[0]["skor"]]
        kirim(chat_id, "\n".join(baris))
    elif cmd == "/latihan":
        if not sesi:
            return kirim(chat_id, "Selesaikan satu sesi dulu, nanti aku beri fokus latihan dari skor terlemahmu.")
        kirim(chat_id, FOKUS[min(sesi[0]["skor"], key=sesi[0]["skor"].get)])
    else:
        con = M.db()
        terpakai = con.execute("SELECT COUNT(*) FROM chat WHERE user_id=? AND peran='user' AND dibuat >= datetime('now','-1 day')", (u["id"],)).fetchone()[0]
        hist = [(("user" if r["peran"] == "user" else "bot"), r["isi"]) for r in reversed(con.execute("SELECT peran,isi FROM chat WHERE user_id=? ORDER BY id DESC LIMIT 6", (u["id"],)).fetchall())]
        jwb, simpan = C.proses(u["nama"], teks, sesi, hist, terpakai)
        if simpan:
            con.execute("INSERT INTO chat(user_id,peran,isi) VALUES(?,?,?)", (u["id"], "user", teks)); con.execute("INSERT INTO chat(user_id,peran,isi) VALUES(?,?,?)", (u["id"], "bot", jwb)); con.commit()
        con.close(); kirim(chat_id, jwb)


def polling():
    try:  # menu perintah (tombol "/" di Telegram); di thread latar agar start server tidak menunggu jaringan
        api("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in PERINTAH_MENU]})
    except Exception as e:
        print("setMyCommands gagal:", e)
    offset = 0
    while True:
        try:
            for up in api("getUpdates", {"offset": offset, "timeout": 25}, timeout=40):
                offset = up["update_id"] + 1
                if "message" in up:
                    try:
                        tangani(up["message"])
                    except Exception as e:  # satu pesan gagal tidak boleh mematikan bot
                        print("bot error:", e)
        except Exception as e:
            print("polling error:", e); time.sleep(5)


def mulai():
    if aktif():
        threading.Thread(target=polling, daemon=True, name="telegram-bot").start()
