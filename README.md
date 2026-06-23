# 🎬 Pictory AI Clone — Flask + Gemini

Text-to-video AI website (Pictory.ai jaisa). Pure Python (Flask). Full admin panel jisme aap **sab kuchh** control kar sakte ho.

---

## ✨ Features

- ✅ User signup / login
- ✅ Text → AI Video generation (Gemini script + images + gTTS narration + moviepy stitching)
- ✅ Credit system per user
- ✅ **Admin panel** with full control:
  - Users: ban/unban, make/remove admin, add credits, delete
  - AI settings: model, system prompt, voice lang, scene duration, resolution
  - Branding: site name, tagline, logo emoji, primary color
  - Feature toggles: signup on/off, video gen on/off, free credits, prompt limit

**Admin login (auto-created on first run):**
- Email: `irkanmalik244255@gmail.com`
- Password: `admin@786`

---

## 🚀 Quick Start (Local)

### 1. Requirements
- Python 3.10+
- **FFmpeg** (moviepy needs it)
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Mac: `brew install ffmpeg`
  - Windows: download from https://ffmpeg.org/download.html and add to PATH

### 2. Install
```bash
cd pictory-clone
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Get Gemini API key (free)
- Go to: https://aistudio.google.com/apikey
- Create API key
- Copy `.env.example` → `.env` and paste your key:
```bash
cp .env.example .env
nano .env   # set GEMINI_API_KEY=...
```

### 4. Run
```bash
python app.py
```
Open: http://localhost:5000

Admin login se `/admin` jao → sab settings change kar sakte ho.

---

## 🌐 Deploy to a Server (VPS)

### Option A: Simple (with gunicorn + nginx)
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```
Then point nginx to `localhost:5000`.

### Option B: Railway / Render (free tier)
1. Push code to GitHub
2. New project → connect repo
3. Add env vars: `GEMINI_API_KEY`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
4. Start command: `gunicorn app:app`
5. Add a build pack/Dockerfile that installs ffmpeg

### Option C: Docker
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```
```bash
docker build -t pictory-clone .
docker run -p 5000:5000 --env-file .env pictory-clone
```

---

## 📁 Project Structure
```
pictory-clone/
├── app.py              # Flask routes (user + admin)
├── models.py           # DB models + settings system
├── video_gen.py        # Gemini + gTTS + moviepy pipeline
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html, index.html, login.html, signup.html, dashboard.html
│   └── admin/dashboard.html, settings.html
├── static/css/style.css
├── generated_videos/   # output mp4s
└── instance/app.db     # SQLite (auto-created)
```

---

## ⚙️ Admin Panel — kya kya control hai?

`/admin/settings` page se:

| Section | Controls |
|---|---|
| **Branding** | Site name, tagline, logo emoji, primary color |
| **AI Config** | Gemini model, image model, system prompt, voice language, scene duration, resolution |
| **Features** | Signup on/off, video gen on/off, free credits, max prompt length |

`/admin` dashboard se:
- Stats (users, videos, processing, failed)
- User management (ban, admin role, credits, delete)
- Video moderation (delete any video)

---

## 🐛 Troubleshooting

- **"GEMINI_API_KEY missing"** → set it in `.env`
- **Video generation fails** → check ffmpeg installed: `ffmpeg -version`
- **Gemini image gen fails** → free tier may not include image gen; fallback shows styled text card automatically. Use `gemini-2.0-flash-exp` or upgrade model in admin settings.
- **gTTS error** → needs internet (uses Google translate TTS)

---

## 📝 Notes

- Videos generate **in background thread** — dashboard auto-refreshes every 15s
- SQLite is fine for small/medium use; switch to Postgres for production by changing `SQLALCHEMY_DATABASE_URI`
- Change `SECRET_KEY` in `.env` before going live
- All admin settings save instantly to DB — no restart needed
