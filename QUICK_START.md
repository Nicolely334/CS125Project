# Quick Start Guide

## Install Dependencies

### Backend
```bash
py -m pip install -r requirements.txt
```

**If that fails, try:**
```bash
python -m pip install -r requirements.txt
```

**If Supabase install fails (needs C++), use older version:**
```bash
py -m pip install "supabase<2.10.0" fastapi uvicorn[standard] python-dotenv pydantic-settings requests
```

### Frontend
```bash
cd frontend
npm install
```

---

## Run Application

### Terminal 1 - Backend
```bash
py -m uvicorn app.main:app --reload --port 8000
```

**Alternative:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

---

## URLs
- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:5173

---

## Environment Variables

**Single `.env` file in project root:**
```
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LASTFM_API_KEY=your-lastfm-key

# Supabase (only need these 2 - backend reads from VITE_ vars too)
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-publishable-key
```

**Where to find these in Supabase:**
1. Go to your Supabase project dashboard
2. Settings → API → "Publishable and secret API keys" tab
3. Copy "Project URL" → `VITE_SUPABASE_URL`
4. Copy "Publishable key" (starts with `sb_publishable_...`) → `VITE_SUPABASE_ANON_KEY`

**Note:** The publishable key is safe to expose in frontend code. RLS policies protect your data.

**If you see "Legacy anon, service_role API keys" tab:** You can use the legacy "anon public" key instead - both work the same way.
