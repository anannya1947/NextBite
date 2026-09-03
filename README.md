# NextBite — AI Meal Recommendation Assistant

**Live Demo:** https://nextbite-frontend-1059896982978.us-central1.run.app
**Backend API (Swagger docs):** https://nextbite-backend-1059896982978.us-central1.run.app/docs
**Repo:** https://github.com/anannya1947/NextBite

NextBite is an AI-powered nutrition assistant that grounds meal recommendations in a
user's **real fitness data** (Fitbit sensor history) and **real nutrition facts** (USDA
FoodData Central), instead of letting an LLM hallucinate calories and macros. It computes
a personalized TDEE, generates a 14-day meal plan, and answers "is this food okay?"
questions with a non-judgmental, budget-aware tone.

## Architecture

```
┌─────────────────┐        REST/JSON        ┌──────────────────────┐
│  Next.js 16      │ ─────────────────────▶ │  FastAPI Backend      │
│  (Cloud Run)     │ ◀───────────────────── │  (Cloud Run)           │
│  Dashboard /     │                         │                       │
│  Meal Plan /     │                         │  ┌─────────────────┐ │
│  Food Q&A        │                         │  │ Orchestrator     │ │
└─────────────────┘                         │  │ ├─ Health Analyzer│ │
                                              │  │ ├─ Nutrition RAG  │ │
                                              │  │ ├─ Meal Planner   │ │
                                              │  │ └─ Food Q&A       │ │
                                              │  └─────────────────┘ │
                                              └──────────┬────────────┘
                                                          │
                          ┌───────────────────────────────┼───────────────────────┐
                          ▼                                ▼                       ▼
                 ┌─────────────────┐          ┌─────────────────────┐   ┌───────────────────┐
                 │  BigQuery         │          │  Firestore (Native)  │   │  Gemini API         │
                 │  fitness_activity │          │  users/{uid}          │   │  (meal generation +  │
                 │  fitness_sleep    │          │   ├─ health_profile   │   │   food Q&A reasoning) │
                 │  fitness_heartrate│          │   ├─ meal_plans       │   └───────────────────┘
                 │  daily_metrics(view)│        │   └─ qa_history       │
                 │  usda_foods (12.3k) │        └─────────────────────┘
                 └─────────────────┘
```

## What's deployed on GCP

| Resource | Value |
|---|---|
| Project | `nextbite-demo` |
| Firestore (Native mode) | `nextbite-demo` / `(default)` database, `us-central1` |
| BigQuery dataset | `nextbite` — `fitness_activity`, `fitness_sleep`, `fitness_heartrate`, `daily_metrics` (view), `usda_foods` |
| Secret Manager | `GEMINI_API_KEY` secret, fetched at runtime by the backend |
| Cloud Run | `nextbite-backend`, `nextbite-frontend` (both `us-central1`) |
| Firebase project | `nextbite-demo-737c0` (Auth ready, Google Sign-In not yet wired into UI) |

### Data loaded
- **Fitbit** (Kaggle `arashnic/fitbit`): 940 daily activity records, 410 sleep records,
  334 aggregated heart-rate-days → joined into a `daily_metrics` BigQuery view.
- **USDA FoodData Central** (Foundation + SR Legacy): 12,341 whole foods with
  calories/protein/fat/carbs/fiber/sugar/sodium, used as grounding data for the
  Nutrition RAG agent (BigQuery `LIKE` search with a curated in-memory fallback).

## Backend (`backend/`) — FastAPI + agent-style Python services

- `app/agents/health_analyzer.py` — Mifflin-St Jeor BMR, activity-level classification
  from BigQuery fitness data, TDEE, and goal-adjusted macro targets.
- `app/agents/nutrition_rag.py` — grounds food facts in BigQuery `usda_foods`, with a
  curated fallback table so the app never hallucinates macros.
- `app/agents/meal_planner.py` — Gemini-generated 14-day meal plan (JSON mode) with an
  automatic deterministic template fallback if Gemini is unavailable/rate-limited.
- `app/agents/food_qa.py` — the "is this food okay?" agent. Never gives a blunt yes/no;
  contextualizes against the user's remaining daily budget and suggests realistic
  alternatives. Falls back to a rule-based grounded response engine if Gemini errors.
- `app/agents/orchestrator.py` — routes requests, manages Firestore-backed user/session
  state.
- `app/tools/bigquery_tools.py`, `app/tools/firestore_tools.py` — parameterized queries
  (SQL-injection safe) and Firestore CRUD, both with graceful in-memory/no-op fallbacks
  when GCP credentials aren't available (keeps local dev friction-free).
- `app/auth.py` — Firebase ID token verification, with an `X-Dev-User-Id` dev-mode
  bypass (see **Security note** below).
- `app/etl/load_fitbit.py`, `app/etl/load_usda.py` — one-shot ETL scripts, CSV → BigQuery.
- 7/7 backend tests passing (`pytest tests/ -v`), covering BMR math, TDEE/macros,
  nutrition RAG lookups, Food Q&A tone/grounding, and the meal-plan API route.

## Frontend (`frontend/`) — Next.js 16 (App Router) + Tailwind CSS 4

- **`/` Dashboard** — live fitness stat cards (steps, calories, sleep, resting HR) and a
  14-day activity trend chart (Recharts), sourced from BigQuery via the backend.
- **`/plan` Meal Plan** — 14-day tab/grid view, macro badges per meal, one-click
  regenerate.
- **`/voice` Ask About Food** — chat-style Food Q&A with quick-suggestion chips, a mic
  button (Web Speech API voice input where supported), and grounded, empathetic
  responses with nutrition facts + alternatives.
- Dark glassmorphism theme (emerald/teal), fully responsive.

## Deployment

Both services are deployed as containers on **Cloud Run**:
- `backend/Dockerfile` — `python:3.11-slim`, installs `requirements.txt`, runs `uvicorn`.
- `frontend/Dockerfile` — multi-stage Node 20 build → Next.js `standalone` runtime image.
  `NEXT_PUBLIC_API_URL` is baked in at build time via `frontend/cloudbuild.yaml`
  (Docker `--build-arg`, since Next.js inlines `NEXT_PUBLIC_*` vars at build time).

```bash
# Backend
cd backend
gcloud run deploy nextbite-backend --source . --region us-central1 --allow-unauthenticated

# Frontend (build with the backend URL baked in, then deploy the built image)
cd frontend
gcloud builds submit --config=cloudbuild.yaml --substitutions=_API_URL=<backend-url>
gcloud run deploy nextbite-frontend --image <image-built-above> --region us-central1 --allow-unauthenticated
```

## Security note (hackathon trade-off)

The backend's `nextbite-backend` Cloud Run service is running with `ENVIRONMENT=development`,
which enables an `X-Dev-User-Id` header bypass for authentication — this let us ship a
working end-to-end demo without wiring Firebase Google Sign-In into the frontend UI in
the time available. **The real Firebase Auth verification path is fully implemented**
(`app/auth.py` verifies Firebase ID tokens via `firebase-admin`); wiring up Google
Sign-In in the frontend and flipping `ENVIRONMENT=production` is the main remaining
step before this could be used with real user accounts.

## Known follow-ups
- **Gemini billing**: the AI Studio API key's prepaid credits are currently depleted
  (`429 RESOURCE_EXHAUSTED`), so live meal-plan/Q&A calls fall back to the deterministic
  template and rule-based engines. Top up billing at https://ai.studio/projects to
  restore live Gemini generation — no code changes needed, the app auto-detects Gemini
  availability per request.
- Wire real Firebase Google Sign-In in the frontend (`AuthProvider`), flip backend to
  `ENVIRONMENT=production`.
- Gemini Live API voice (true streaming audio) — currently the voice page uses the
  browser's Web Speech API for speech-to-text and calls the same grounded `/api/voice/ask`
  endpoint; `app/routers/voice.py` has a `/token` stub ready for a full Live API relay.

## Local development

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m app.etl.load_fitbit --data-dir ../data/fitbit
python -m app.etl.load_usda --data-dir ../data/usda
python ../infra/seed_firestore.py
uvicorn app.main:app --reload --port 8080

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:3000, expects backend on :8080
```

## Verification performed
- `pytest backend/tests/ -v` → 7/7 passed.
- ETL scripts run against real Kaggle Fitbit + USDA FoodData Central CSVs, verified row
  counts land in BigQuery (940/410/334/12,341 rows).
- Firestore seeded and read back correctly (`demo-user-001` health profile: BMR 1698,
  TDEE 2929).
- `npm run build` (Next.js) compiles cleanly, 0 TypeScript errors.
- Live smoke tests against deployed Cloud Run URLs: `/api/health`, `/api/fitness/summary`,
  `/api/health/profile`, `/api/plan/latest`, `/api/voice/ask` all return 200 with real
  BigQuery/Firestore-backed data; CORS preflight from the frontend origin verified.
