# AI Virtual Mouse — Premium Gesture Control

Proyek **AI Virtual Mouse** menggantikan kursor fisik dan trackpad dengan kontrol gestur tangan yang canggih menggunakan Webcam. Dibangun dengan Python, OpenCV, Mediapipe, dan PyAutoGUI untuk navigasi Windows yang mulus dan intuitif.

---

## Quick Start — Cara Penggunaan

Gunakan gestur tangan berikut di depan kamera untuk mengontrol komputer Anda:

### Navigasi Kursor & Klik
| Aksi | Gestur Tangan |
|---|---|
| **Gerak Kursor** | Angkat **Satu Jari Telunjuk** (posisi tegak/lurus). |
| **Klik Kiri** | **Opsi 1:** Tekuk telunjuk ke depan **ATAU** **Opsi 2:** Rapatkan jempol + telunjuk. |
| **Double Klik** | Lakukan gestur **Klik Kiri** dua kali dengan cepat. |
| **Scroll** | Angkat **Telunjuk + Tengah** (posisi peace). Gerakkan tangan naik/turun. |
| **Drag & Drop** | Genggam tangan Anda menjadi **Kepalan**. |
| **Batal / Idle** | Buka **seluruh telapak tangan** lebar-lebar untuk jeda. |

### Shortcut Navigasi (Navigasi Trackpad Windows)
*   **3 Jari (Telunjuk, Tengah, Manis):**
    *   **Swipe Atas:** Task View (Win + Tab)
    *   **Swipe Bawah:** Show Desktop (Win + D)
    *   **Swipe Kiri/Kanan:** Ganti Aplikasi (Alt + Tab)
*   **4 Jari (Tanpa Jempol):**
    *   **Swipe Kiri/Kanan:** Pindah Desktop Virtual
    *   **Swipe Atas/Bawah:** Maximize / Minimize Window
*   **Fitur Spesial:**
    *   **Volume Control:** Angkat **Jempol + Kelingking**, gerakkan naik/turun.
    *   **Screenshot:** Angkat hanya **Jari Kelingking** saja (Win + Shift + S).

---

## Arsitektur Proyek

```
Computer vision/
├── main.py                    # Entry point & UI Overlay
├── hand_tracking_module.py    # Mediapipe Tasks API Wrapper
├── gesture_controller.py      # Logika Mapping Gesture → OS
├── utils.py                   # Smoothing & Coordinate Mapping
├── requirements.txt           # Dependensi Proyek
└── hand_landmarker.task       # Model AI Mediapipe
```

---

## Instalasi & Persiapan

1. **Install Python 3.10+**
2. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Download Model:** Pastikan file `hand_landmarker.task` berada di folder utama.
4. **Jalankan Aplikasi:**
   ```bash
   python main.py
   ```

---

## Roadmap Pengembangan

- [x] Phase 1: Migrasi ke Mediapipe Tasks API terbaru.
- [x] Phase 2: Implementasi Gesture Stabilization (anti-getar).
- [x] Phase 3: Shortcut Navigasi 3 & 4 Jari.
- [x] Phase 4: Kontrol Volume & Screenshot.
- [x] Phase 5: UI Overlay & HUD yang user-friendly di layar kamera.
- [ ] Phase 6: Konfigurasi via file JSON/YAML untuk custom gesture.

---

## Tips & Fail-Safe

1.  **Fail-Safe:** Jika kursor sulit dikontrol, segera gerakkan mouse fisik ke **POJOK LAYAR** mana pun untuk menghentikan program darurat.
2.  **Pencahayaan:** Pastikan cahaya cukup mengenai tangan Anda agar deteksi Mediapipe akurat.
3.  **Resolusi:** Aplikasi ini mendukung resolusi kamera hingga **1920x1080** untuk tracking yang lebih presisi.
4.  **Interactive HUD:** Gunakan panduan gestur yang muncul di layar saat posisi tangan Idle atau Unknown.

---
Selamat bernavigasi dengan tangan kosong!
"# LeafyEyes" 
