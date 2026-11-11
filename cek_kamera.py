"""
cek_kamera.py
Mencari nomor (index) kamera yang tersedia, termasuk webcam eksternal USB.
Tekan tombol apa saja untuk lanjut ke kamera berikutnya, q untuk berhenti.
"""
import os

import cv2

BACKEND = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY


def main(max_index=6):
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, BACKEND)
        if not cap.isOpened():
            cap.release()
            continue
        ok, frame = cap.read()
        if not ok:
            cap.release()
            continue
        h, w = frame.shape[:2]
        found.append(i)
        print(f"Kamera index {i}: OK  ({w}x{h})")
        key = 255
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cv2.putText(frame, f"index {i} - tekan tombol apa saja (q = berhenti)", (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Cek kamera", frame)
            key = cv2.waitKey(1) & 0xFF
            if key != 255:
                break
        cap.release()
        if key == ord("q"):
            break
    cv2.destroyAllWindows()
    if found:
        print("\nKamera ditemukan di index:", found)
        print("Biasanya 0 = kamera bawaan laptop, 1 = webcam eksternal.")
    else:
        print("Tidak ada kamera terdeteksi. Cek kabel USB / izin kamera di Windows Settings.")


if __name__ == "__main__":
    main()