# 🛡 ISARM — Intelligent Scene Analysis & Real-Time Security Monitoring

> *Because your webcam deserves better than just sitting there collecting dust.*

---

## What is this?

ISARM is a **real-time AI surveillance desktop app** that watches your camera feed, detects objects using computer vision, compares scenes to spot what changed, and then explains it to you in plain English — like having a calm, highly intelligent security guard who never needs a coffee break.

Point it at a room. Walk away. Come back. It'll tell you exactly what moved, what appeared, and what went missing. And if someone shows up when they shouldn't? It fires a threat alert faster than you can say "who left the window open."

No cloud. No subscriptions. No sending your footage to some server in another country. Everything runs **100% on your own machine.**

---

## What it actually does

- **Live camera feed** with real-time YOLOv8 object detection — bounding boxes, confidence scores, target count, the works
- **Scene comparison** — upload or capture two images and get an AI-written diff in plain English
- **Threat alert system** — animated banner slides in when something suspicious is detected, with an on/off toggle so you're not being screamed at during testing
- **Security modes** — Static (flag anything), Dynamic (chill mode), Away (scream if a person appears)
- **Local LLM explanations** — Mistral 7B running via Ollama writes a natural sentence like *"The bag that was on the desk is no longer visible, and an unknown person has entered the frame"*
- **Tactical HUD interface** — because if you're building a surveillance system, it might as well look like one

---

## Tech stack (the honest version)

| What | How |
|---|---|
| Desktop UI | PyQt5 — native windows, custom QPainter rendering |
| Object detection | Ultralytics YOLOv8n — pre-trained on 80 COCO classes |
| Camera + image ops | OpenCV (cv2) |
| Local AI explanations | Mistral 7B-Instruct via Ollama |
| LLM transport | Python `requests` — plain HTTP to localhost |
| Language | Python 3.x |
| Database | None. RAM only. Live fast, forget things. |

---

## Prerequisites — read this before you do anything else

You need four things installed on your machine before this app will work:

### 1. Python 3.8 or higher
Check with:
```bash
python --version
```
If you don't have it, grab it from [python.org](https://python.org).

### 2. Ollama (the local LLM server)
This is what runs the AI explanation engine on your own computer.

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download the installer from [ollama.com](https://ollama.com/download).

After installing, pull the Mistral model (this downloads ~4GB, get a snack):
```bash
ollama pull mistral:7b-instruct
```

Start the Ollama server (leave this running in the background):
```bash
ollama serve
```

### 3. A working webcam
Built-in laptop camera works fine. USB webcam works fine. Your phone propped up against a book technically also works but we're not judging.

### 4. Git
```bash
git --version
```
If not installed: [git-scm.com](https://git-scm.com).

---

## Installation

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/intelligent-scene-analysis-and-real-time-security-monitoring.git
cd intelligent-scene-analysis-and-real-time-security-monitoring
```

### Step 2 — Create a virtual environment (strongly recommended)
```bash
# Create it
python -m venv venv

# Activate it — macOS / Linux
source venv/bin/activate

# Activate it — Windows
venv\Scripts\activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

This installs PyQt5, OpenCV, Ultralytics, and requests. The first time you run the app, YOLOv8 will automatically download `yolov8n.pt` (~6MB) if it doesn't find it. You can also download it manually:

```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Step 4 — Make sure Ollama is running
In a separate terminal:
```bash
ollama serve
```
You should see something like `Listening on 127.0.0.1:11434`. Keep that terminal open.

### Step 5 — Run the app
```bash
python main.py
```

The window opens. You're in.

---

## How to use it

### Live Monitoring mode
1. Select **Live Feed** in the top navigation
2. Choose your **Security Protocol** from the sidebar (Static / Dynamic / Away)
3. Press **▶ START** in the bottom bar — the camera feed activates
4. Press **⊙ CAPTURE REF** to snapshot the current scene as your reference
5. Move something around, then press **⬡ COMPARE FRAME**
6. The AI panel writes an explanation of what changed

### Scene Comparison mode
1. Click **Scene Comparison** in the top navigation
2. Press **↑ UPLOAD REFERENCE** — pick your "before" image
3. Press **↑ UPLOAD IMAGE** — pick your "after" image
4. Press **⬡ COMPARE IMAGES**
5. Read the AI explanation at the bottom

### Threat Alerts
- The **THREAT ALERTS** toggle in the sidebar turns the alert banner on or off
- In **Away** mode, any detected person triggers a red banner + top bar flash
- The banner tells you what was detected, confidence level, and what to do
- Dismiss it with the ✕ button when you've acknowledged the threat

---

## Project structure

```
isarm/
│
├── main.py              # The entire app — UI, logic, components, event handling
├── ai_explainer.py      # Builds the prompt and calls Ollama to get an explanation
├── scene_compare.py     # Runs YOLO on two images and diffs the detected objects
├── requirements.txt     # Python dependencies
├── .gitignore           # Keeps the repo clean
└── README.md            # You are here
```

---

## Troubleshooting

**Camera not working / "NO SIGNAL"**
Make sure no other app is using your camera. On macOS, check System Preferences → Privacy → Camera.

**"AI error: Connection refused"**
Ollama isn't running. Open a new terminal and run `ollama serve`.

**"AI error: model not found"**
You haven't pulled the model yet. Run `ollama pull mistral:7b-instruct`.

**The app opens but looks wrong / fonts missing**
Install Space Grotesk on your system from [fonts.google.com/specimen/Space+Grotesk](https://fonts.google.com/specimen/Space+Grotesk). The app falls back to Arial if it's not found, which still works but looks less tactical.

**PyQt5 install fails on macOS Sonoma**
Try: `pip install PyQt5 --config-settings --confirm-license= --verbose`

**YOLOv8 is slow on my machine**
You're running CPU inference. This is normal on machines without an NVIDIA GPU. The nano model (`yolov8n.pt`) is already the fastest option. Detection still works — it's just a few hundred milliseconds slower per frame.

---

## Security mode — what actually happens

| Mode | Behaviour |
|---|---|
| **Static** | Any object change triggers a warning — ideal for guarding a fixed scene |
| **Dynamic** | Changes are noted but not alarmed — good for active environments |
| **Away** | Only fires an alert if a **person** is detected — perfect for unattended monitoring |

---

## Built with

- [PyQt5](https://pypi.org/project/PyQt5/) — Qt5 bindings for Python
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — state-of-the-art object detection
- [OpenCV](https://opencv.org/) — computer vision and camera handling
- [Ollama](https://ollama.com/) — run large language models locally
- [Mistral 7B](https://mistral.ai/) — the brain behind the natural language explanations

---

## License

MIT. Do what you want with it. Just don't use it for anything that would make a reasonable person uncomfortable.

---

## Author

Built as a computer vision + AI integration project demonstrating real-time object detection, scene analysis, local LLM inference, and custom desktop UI design.

*If this helped you, a ⭐ on the repo would be greatly appreciated and will fuel further late-night coding sessions.*
