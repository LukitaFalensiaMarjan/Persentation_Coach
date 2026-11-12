# Persentation Coach
*An Automated Presentation Coaching System Based on Pose Keypoints and a Hybrid Machine Learning Approach*

> **Machine Learning Practicum Course Project (M2)**  
> **Politeknik Manufaktur Negeri Bangka Belitung (POLMAN)**

---

## Executive Summary

**Persentation Coach** is an AI-based presentation coaching application (*Computer Vision & Machine Learning*) designed to help students practice public speaking on their own. With nothing more than a laptop camera or a standard USB webcam (no special sensors or IoT devices), the system reads the presenter's 17 body *pose keypoints* in real time using **YOLO11-pose**.

Body language is classified into **7 gesture states** using a **hybrid approach**:
1. **Body Geometry Rules**: detect *facing away from the audience*, *arms crossed*, and *pointing at the slide*.
2. **Hand Motion Meter (`MotionMeter`)**: detects *active gestures* from wrist speed relative to the shoulders, normalized by torso length, with an anti-jitter filter (*EMA & deadband*).
3. **Random Forest Classifier**: classifies *neutral*, *looking down*, and *hands hidden* from 52 normalized keypoint-coordinate features.

Because evaluation relies on normalized body-skeleton proportions (not raw image pixels), the system is **robust to changes in background, clothing color, and room lighting**.

---

## Key Features & Latest Updates

- **Real-Time Camera Analysis**: live detection of the presenter's skeleton (≥ 15 FPS on a standard laptop CPU).
- **Real-Time Alerts**: on-screen warnings when the presenter faces away from the audience (> 3 s), looks down too long (> 5 s), or keeps arms crossed (> 10 s).
- **Login Brute-Force Protection (Rate Limiting) [NEW]**:
  - Up to 5 failed attempts before the account is temporarily locked for 60 seconds (HTTP 429).
  - The web form shows the remaining attempts and a button with a cooldown countdown.
  - Dual protection based on both username and IP address.
- **Responsive Mobile / Small-Screen UI [NEW]**:
  - The **hamburger menu** button is placed neatly at the top right.
  - All navigation is consolidated into an elegant **mobile drawer**.
  - Compatible with smartphone touchscreens (iOS Safari & Android Chrome), with comfortable touch targets and no auto-zoom.
- **Curtain-Unveil Result Pop-up [NEW]**:
  - The practice-result pop-up now uses an upward curtain-opening transition (`clip-path` and `cubic-bezier`) consistent with the chatbot pop-up.
  - Score, charts, and advice appear in a staggered rise.
- **Stage Movement Heatmap**: analyzes the presenter's standing position on stage (hip midpoint).
- **Automatic PDF Report Generator (A4)**: produces a full report sheet with the composite score, the 4-aspect breakdown, an event timeline, gesture proportions, and the 3 main improvement tips.
- **Topic-Restricted Chatbot Consultation**: a companion chatbot grounded in the presenter's own practice data, with strict topic *guardrails* (supports Google Gemini API, local Ollama, or a built-in *rule-based* mode when offline).
- **Telegram Bot Integration**: link your account by scanning a QR code / deep link to receive PDF reports and chat with the bot on your phone.

---

## System Architecture & Hybrid Classification Flow

```
                       Webcam Video Frame
                               │
                       YOLO11-pose (17 Keypoints)
                               │
              ┌────────────────┴────────────────┐
              │                                 │
     [1. Geometry Rules]                [Shoulders visible?]
      • Nose/eyes not visible          ┌────────┴────────┐
        or shoulders flipped?          │ YES             │ NO
        ──► facing away                │                 └──► Ignore
      • Arms crossed over chest        │
        or near opposite elbow?        ▼
        ──► arms_crossed        [2. Motion Meter (MotionMeter)]
      • Wrist far to the side         • Hand speed in front of chest
        above the hips?                 > threshold (move_t)?
        ──► pointing_slide              ──► active_gesture
              │                        │
              └─────────┬──────────────┘
                        │ If none of the rules above match:
                        ▼
                [3. Random Forest (52 Keypoint Features)]
                  • neutral
                  • looking down
                  • hands hidden
                        │
                        ▼
                Smoothing (Vote over the Last 15 Frames)
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
On-screen Alerts & Web Session    SQLite Database & PDF
```

---

## Project Directory Structure

```text
Persentation_Coach/
│
├── web/                     # Fullstack web app (FastAPI + HTML5/CSS/JS)
│   ├── main.py              # Main web server, authentication, rate limiting, WebSocket
│   ├── engine.py            # Pose analysis engine, scoring & session metric calculation
│   ├── laporan.py           # PDF (A4) report generator based on matplotlib
│   ├── chat.py              # Consultation chatbot with layered guardrails
│   ├── tele.py              # Telegram Bot integration (HTTP polling)
│   ├── surel.py             # Email delivery service (SMTP / verification)
│   └── static/              # UI assets (HTML, responsive CSS, JavaScript)
│       ├── css/             # Stylesheets (app.css, latihan.css, chatpop.css, landing.css)
│       ├── js/              # Client scripts (shared.js, auth.js, latihan.js, hasil.js, riwayat.js)
│       └── img/             # App logos and icons
│
├── models/                  # Model weights & machine learning artifacts
│   ├── kp_rf.joblib         # Random Forest model for keypoint features
│   ├── gesture_best.pt      # YOLO11-cls model (cropped-image baseline)
│   └── kp_confusion_matrix.png
│
├── demo_kp.py               # Real-time OpenCV visualization demo
├── demo_webcam.py           # Baseline demo using YOLO11-cls
├── kp_features.py           # 52-feature keypoint geometry extraction module
├── extract_keypoints.py     # Dataset keypoint feature extraction to .npz
├── train_kp.py              # Script to retrain the keypoint Random Forest
├── train.py                 # Script to retrain the YOLO11-cls model
├── cek_kamera.py            # Utility to check camera / webcam indexes
│
├── yolo11n-pose.pt          # Pretrained YOLO11-pose nano weights
├── kp_data.npz              # Extracted keypoint feature data
├── requirements.txt         # Python libraries & dependencies
├── .env.example             # Sample environment variable configuration
├── .env                     # Active local configuration file
├── .gitignore               # Git ignore configuration
├── PRD.md                   # Full Product Requirement Document
└── README.md                # Official documentation for this project
```

---

## System Requirements

1. **Operating System**: Windows 10/11, Linux (Ubuntu/Debian), or macOS.
2. **Python**: version `3.10`, `3.11`, `3.12`, or `3.14`.
3. **Hardware**:
   - Built-in laptop webcam or external USB webcam (minimum 720p @ 30 fps).
   - Modern CPU (YOLO11n pose inference is very light and runs smoothly without a dedicated graphics card).
   - NVIDIA GPU with CUDA (optional, only if you want to retrain deep learning models).

---

## Installation Guide on Another Computer (Step by Step)

This guide is for testers, examiners, or fellow developers who want to install and run the project on a new computer from scratch:

### 1. Download / Copy the Project
Make sure the whole repository folder is copied to the target computer, then open a terminal (PowerShell on Windows, or Bash on Linux/macOS) in the project directory:
```powershell
cd Persentation_Coach
```

### 2. Create and Activate a Virtual Environment
Creating a virtual environment is strongly recommended to keep dependencies isolated:
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Python Dependencies
Run the install command from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

> **Note**: If you use an NVIDIA GPU and want to use CUDA, follow the GPU-specific instructions at [pytorch.org](https://pytorch.org/). By default, CPU mode already delivers ≥ 15 FPS inference.

### 4. Environment Configuration (`.env`)
Copy `.env.example` to `.env`:
- **Windows (PowerShell)**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **Linux / macOS**:
  ```bash
  cp .env.example .env
  ```

> **Standalone / Offline Mode**: The app is designed to **work on its own (offline)** without any API key. The email verification link is printed straight to the terminal console, the SQLite database is created automatically, and the chatbot uses the local rule-based tips knowledge base.

To enable optional integrations, fill in the `.env` file:
```ini
# Google OAuth (Optional, for Google account login)
GOOGLE_CLIENT_ID=

# Telegram Bot Token (Optional, from @BotFather)
TELEGRAM_BOT_TOKEN=

# Smart AI Chatbot (Optional: Google Gemini API or local Ollama)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=
OLLAMA_MODEL=llama3.2
CHAT_BATAS_HARIAN=20

# Email SMTP Configuration (Optional, if empty the link is printed to the console)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
BASE_URL=http://localhost:8000
```

---

## How to Run the Application

### A. Run the Main Web Dashboard (Recommended)
Start the application server with Uvicorn:
```powershell
python -m uvicorn web.main:app --reload --port 8000
```
Open your favorite browser and go to:
**[http://localhost:8000](http://localhost:8000)**

**Testing Flow:**
1. Go to the **Register** page to create a new account. The email verification link appears in the terminal (if SMTP is empty), or the account can log in right away.
2. Open the **Latihan** (Practice) menu.
3. Allow camera access in your browser.
4. Choose a practice duration (e.g. 1 minute), then click **Mulai latihan** (Start practice).
5. Stand in front of the camera and vary your body language (facing away, crossing arms, pointing at the slide, or speaking with active hand gestures).
6. At the end of the session, the result pop-up appears with an upward curtain-opening animation, showing the total score ring, the per-aspect breakdown, and a **Download PDF** button.

---

### B. Run Camera Tests & CLI Demos

#### 1. Check Camera Index
To make sure the built-in camera or USB webcam is detected by OpenCV:
```powershell
python cek_kamera.py
```

#### 2. Live OpenCV Detection Demo (Desktop GUI)
Runs the hybrid keypoint + Random Forest pipeline directly in an OpenCV GUI window:
```powershell
python demo_kp.py --kp models\kp_rf.joblib --cam 0
```
- Use `--cam 1` if you use an external USB camera.
- Press `d` to show/hide the geometry-parameter debug numbers.
- Press `s` to save a screenshot.
- Press `q` to quit.

#### 3. Retrain the Keypoint Model (Optional)
If you add new data to the `gesture_rf` dataset folder:
```powershell
# 1. Extract pose coordinates into a feature array (kp_data.npz)
python extract_keypoints.py --data gesture_rf --out kp_data.npz

# 2. Train the Random Forest model
python train_kp.py --data kp_data.npz
```

---

## Scoring Rubric & Formula

The system produces a composite **0–100** score computed mathematically from 4 body-language aspects:

$$\text{Total Score} = (0.30 \times \text{Orientation}) + (0.30 \times \text{Gesture}) + (0.25 \times \text{Posture}) + (0.15 \times \text{Movement})$$

| Aspect | Weight | Basis of Measurement |
|---|:---:|---|
| **Audience Orientation** | **30%** | Percentage of time the presenter's body and face are turned toward the audience (minus time facing away). |
| **Hand Gestures** | **30%** | Presence of dynamic active hand movement that supports the explanation, while minimizing crossed arms or hands in pockets. |
| **Head Posture** | **25%** | Upright head position (minus the habit of looking down at notes for too long). |
| **Position Movement** | **15%** | Stability of the presenter's movement on stage (via the hip-position heatmap). |

---

## Developers & License

- **Institution**: Politeknik Manufaktur Negeri Bangka Belitung (POLMAN)
- **Course**: Machine Learning Practicum (M2)
- **Year**: 2026
- **License**: *Academic & Educational Purpose*
