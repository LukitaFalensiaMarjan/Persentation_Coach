"""Pengiriman email lewat SMTP (stdlib): verifikasi email dan reset password.
Isi .env: SMTP_HOST, SMTP_PORT (587 STARTTLS / 465 SSL), SMTP_USER, SMTP_PASSWORD, SMTP_FROM (opsional),
BASE_URL (alamat aplikasi untuk tautan, default http://localhost:8000).
Tanpa SMTP, tautan hanya dicetak di konsol server (mode pengembangan) dan fungsi kirim mengembalikan False."""
import html
import os
import smtplib
import ssl
from email.message import EmailMessage


def dikonfigurasi() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def _kirim(ke: str, subjek: str, nama: str, kalimat: str, tombol: str, tautan: str, penutup: str) -> bool:
    if not dikonfigurasi():
        print(f"[surel] SMTP belum dikonfigurasi. Tautan ({subjek}) untuk {ke}: {tautan}")
        return False
    pesan = EmailMessage()
    pesan["Subject"] = subjek
    pesan["From"] = os.getenv("SMTP_FROM") or os.environ["SMTP_USER"]
    pesan["To"] = ke
    pesan.set_content(f"Halo {nama},\n\n{kalimat}\n\n{tautan}\n\n{penutup}")
    n, t = html.escape(nama), html.escape(tautan, quote=True)
    pesan.add_alternative(f"""<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#161616">
<h2 style="font-weight:500;letter-spacing:.04em">PERSENTATION COACH</h2>
<p>Halo {n},</p><p>{html.escape(kalimat)}</p>
<p><a href="{t}" style="display:inline-block;background:#050505;color:#fff;text-decoration:none;padding:12px 26px;border-radius:999px">{html.escape(tombol)}</a></p>
<p style="font-size:12px;color:#6b6862">Atau salin tautan ini ke browser:<br>{t}</p>
<p style="font-size:12px;color:#6b6862">{html.escape(penutup)}</p></div>""", subtype="html")
    host, port = os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=20) as s:
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]); s.send_message(pesan)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]); s.send_message(pesan)
        return True
    except Exception as e:  # kegagalan kirim tidak boleh membuat permintaan error; user bisa mencoba lagi
        print(f"[surel] gagal mengirim ke {ke}: {e}. Tautan: {tautan}")
        return False


def kirim(ke: str, nama: str, tautan: str) -> bool:
    """Email verifikasi pendaftaran (berlaku 24 jam)."""
    return _kirim(ke, "Verifikasi email Persentation Coach", nama,
                  "Terima kasih sudah mendaftar di Persentation Coach. Tekan tombol di bawah untuk memverifikasi emailmu (berlaku 24 jam).",
                  "Verifikasi email", tautan, "Jika kamu tidak merasa mendaftar, abaikan email ini.")


def kirim_reset(ke: str, nama: str, tautan: str) -> bool:
    """Email reset password (berlaku 1 jam)."""
    return _kirim(ke, "Reset password Persentation Coach", nama,
                  "Kami menerima permintaan untuk mengatur ulang password akunmu. Tekan tombol di bawah untuk membuat password baru (berlaku 1 jam).",
                  "Atur ulang password", tautan, "Jika kamu tidak memintanya, abaikan email ini; password lamamu tetap aman.")
