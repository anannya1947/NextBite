# NextBite: AI Meal Recommendation Assistant — Implementation Plan

## Current State

The workspace is empty and the machine has **no development tools installed** — no Python, Node.js, gcloud CLI, or Docker. We need to bootstrap everything from scratch.

## User Setup Required (Manual Steps)

> [!IMPORTANT]
> The following steps **must be done by you** before I can start building. They require interactive browser sign-ins, license agreements, or downloads that I cannot automate.

### Step 1: Install Core Development Tools

Run these in an **elevated PowerShell** (Run as Administrator):

```powershell
# Install Chocolatey (package manager)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python 3.11+, Node.js 20 LTS, Git (if not present)
choco install python311 nodejs-lts git -y

# Refresh PATH
refreshenv
```

### Step 2: Install Google Cloud SDK

```powershell
# Download and install gcloud CLI
choco install gcloudsdk -y
refreshenv
```

Then authenticate (these open a browser):
```powershell
gcloud auth login
gcloud auth application-default login
```

### Step 3: GCP Project Setup

```powershell
# Create project (or use existing one)
gcloud projects create nextbite-demo --name="NextBite Demo"
gcloud config set project nextbite-demo

# Link billing (interactive — must be done in Cloud Console)
# Go to: https://console.cloud.google.com/billing/linkedaccount?project=nextbite-demo

# Enable required APIs
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com firestore.googleapis.com run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com identitytoolkit.googleapis.com

# Create Firestore database (Native mode)
gcloud firestore databases create --location=us-central1
```

### Step 4: Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **"Create API Key"**
3. Copy the key — you'll give it to me to store in Secret Manager

### Step 5: Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add Project"** → select your existing `nextbite-demo` GCP project
3. Enable **Authentication** → Sign-in method → **Google** → Enable
4. Note your Firebase config (apiKey, authDomain, projectId)

### Step 6: Download Datasets

1. **Kaggle FitBit data**: Go to [kaggle.com/datasets/arashnic/fitbit](https://www.kaggle.com/datasets/arashnic/fitbit), download and extract to `c:\Users\Administrator\Documents\nextbite\data\fitbit\`
   - We need: `dailyActivity_merged.csv`, `sleepDay_merged.csv`, `heartrate_seconds_merged.csv`

2. **USDA FoodData Central**: Go to [fdc.nal.usda.gov/download-datasets](https://fdc.nal.usda.gov/download-datasets), download:
   - "FoodData Central Foundation Foods CSV"
   - "FoodData Central SR Legacy CSV"
   - Extract to `c:\Users\Administrator\Documents\nextbite\data\usda\`

### Step 7: Install Docker Desktop (for Cloud Run deployment later)

Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) and install. Required for containerized deployment in Phase 4.

---

## What I Will Build (Phased Approach)

Once the setup above is complete, I'll implement everything in these phases:

---

### Phase 1: Project Scaffolding & Local Backend (Days 1-2)

#### Project Structure
```
nextbite/
├── backend/                    # FastAPI + ADK agents
│   ├── pyproject.toml          # Python dependencies (uv/pip)
│   ├── app/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Settings & env vars
│   │   ├── auth.py             # Firebase Auth middleware
│   │   ├── routers/
│   │   │   ├── health.py       # Health check endpoints
│   │   │   ├── plan.py         # Meal plan endpoints
│   │   │   ├── fitness.py      # Fitness data endpoints
│   │   │   └── voice.py        # Voice/WebSocket relay
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py # Root ADK agent
│   │   │   ├── health_analyzer.py
│   │   │   ├── nutrition_rag.py
│   │   │   ├── meal_planner.py
│   │   │   └── food_qa.py
│   │   ├── tools/
│   │   │   ├── bigquery_tools.py   # BQ query functions
│   │   │   ├── firestore_tools.py  # Firestore CRUD
│   │   │   └── nutrition_lookup.py # USDA food search
│   │   ├── models/
│   │   │   ├── user.py         # User profile Pydantic models
│   │   │   ├── meal_plan.py    # Meal plan models
│   │   │   └── fitness.py      # Fitness data models
│   │   └── etl/
│   │       ├── load_fitbit.py  # Kaggle CSV → BigQuery
│   │       └── load_usda.py    # USDA CSV → BigQuery
│   ├── Dockerfile
│   └── .env.example
├── frontend/                   # Next.js web app
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx        # Landing/Dashboard
│   │   │   ├── plan/
│   │   │   │   └── page.tsx    # Meal plan view
│   │   │   └── voice/
│   │   │       └── page.tsx    # Voice Q&A interface
│   │   ├── components/
│   │   │   ├── AuthProvider.tsx
│   │   │   ├── Navbar.tsx
│   │   │   ├── FitnessCard.tsx
│   │   │   ├── MealPlanGrid.tsx
│   │   │   ├── VoiceButton.tsx
│   │   │   └── NutritionChart.tsx
│   │   ├── lib/
│   │   │   ├── firebase.ts
│   │   │   ├── api.ts
│   │   │   └── gemini-live.ts  # Live API WebSocket client
│   │   └── styles/
│   │       └── globals.css
│   ├── Dockerfile
│   └── next.config.js
├── data/                       # Raw datasets (gitignored)
│   ├── fitbit/
│   └── usda/
├── infra/                      # Deployment configs
│   ├── cloudbuild.yaml
│   ├── k8s/                    # GKE manifests (learning exercise)
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── seed_firestore.py       # Demo user profile seed script
├── docs/
│   ├── architecture.md
│   └── setup.md
├── .gitignore
├── README.md
└── docker-compose.yaml         # Local dev with all services
```

#### [NEW] `backend/pyproject.toml`
Python project config with dependencies: `fastapi`, `uvicorn`, `google-adk`, `google-cloud-bigquery`, `google-cloud-firestore`, `firebase-admin`, `pydantic`, `python-dotenv`.

#### [NEW] `backend/app/main.py`
FastAPI application with CORS, Firebase Auth middleware, and route registration.

#### [NEW] `backend/app/config.py`
Centralized settings using Pydantic BaseSettings, loading from env vars: `GCP_PROJECT_ID`, `GEMINI_API_KEY`, `BIGQUERY_DATASET`, `FIRESTORE_DATABASE`.

#### [NEW] `backend/app/auth.py`
Firebase Auth token verification middleware — validates `Authorization: Bearer <idToken>` headers. Includes a bypass mode for local development.

---

### Phase 2: Data Ingestion — ETL Scripts (Days 2-3)

#### [NEW] `backend/app/etl/load_fitbit.py`
- Reads `dailyActivity_merged.csv`, `sleepDay_merged.csv`, `heartrate_seconds_merged.csv`
- Aggregates heartrate_seconds to daily avg/resting HR per user
- Joins activity + sleep + HR into a unified `daily_metrics` table
- Loads into BigQuery `nextbite.fitness_raw.daily_activity`, `nextbite.fitness_raw.sleep_day`, `nextbite.fitness_raw.heartrate_daily`
- Creates a `nextbite.fitness.daily_metrics` view joining all three

#### [NEW] `backend/app/etl/load_usda.py`
- Reads USDA FoodData Central CSVs (`food.csv`, `food_nutrient.csv`, `nutrient.csv`)
- Joins into flat table: `fdc_id`, `description`, `calories`, `protein_g`, `fat_g`, `carbs_g`, `fiber_g`, `sugar_g`, `sodium_mg`
- Loads into BigQuery `nextbite.nutrition.usda_foods`

#### [NEW] `infra/seed_firestore.py`
Seeds demo user profile into Firestore:
```json
{
  "uid": "demo-user-001",
  "name": "Alex Demo",
  "age": 30,
  "weight_kg": 75,
  "height_cm": 175,
  "sex": "male",
  "goal": "maintain",
  "dietary_restrictions": ["none"],
  "fitness_user_id": "1503960366",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Phase 3: ADK Agents (Days 3-6)

#### [NEW] `backend/app/agents/health_analyzer.py`
- ADK `LlmAgent` with tools to query BigQuery `daily_metrics`
- Computes: TDEE (Mifflin-St Jeor), activity level classification, 7-day trend summary
- Outputs structured `HealthProfile` (JSON) saved to Firestore `users/{uid}/health_profile/latest`

#### [NEW] `backend/app/agents/nutrition_rag.py`
- ADK `LlmAgent` exposed as a **tool** to other agents
- Queries BigQuery `usda_foods` table via keyword/semantic search on food description
- Returns structured nutrition facts (calories, protein, fat, carbs, etc.)
- Prevents LLM hallucination of nutrition data

#### [NEW] `backend/app/agents/meal_planner.py`
- ADK `LlmAgent` that takes a `HealthProfile` + calls `NutritionRAGAgent` as tool
- Generates 14-day meal plan as structured JSON:
  ```json
  { "days": [{ "day": 1, "meals": [{ "type": "breakfast", "dish": "...", "calories": 400, "protein_g": 25, "fat_g": 12, "carbs_g": 50 }] }] }
  ```
- Writes result to Firestore `users/{uid}/meal_plans/{planId}`

#### [NEW] `backend/app/agents/food_qa.py`
- ADK `LlmAgent` for the "is this food okay?" voice interaction
- System prompt encodes the non-judgmental, contextual response style:
  - Never blunt yes/no — always contextualizes relative to remaining daily budget
  - Explains trade-offs relative to goal
  - Suggests 1-2 realistic alternatives or adjustments
  - Affirms specifically when food is a good fit
- Uses `NutritionRAGAgent` as tool for grounded macro data
- Reads user's current health profile + meal plan from Firestore

#### [NEW] `backend/app/agents/orchestrator.py`
- Root ADK agent that routes requests to sub-agents
- Manages conversation state and agent transfer
- Exposes a unified interface for the FastAPI endpoints

#### [NEW] `backend/app/tools/bigquery_tools.py`
ADK tool functions: `query_daily_metrics(user_id, start_date, end_date)`, `search_usda_foods(query, limit)`, `get_user_fitness_summary(user_id)`.

#### [NEW] `backend/app/tools/firestore_tools.py`
ADK tool functions: `get_user_profile(uid)`, `save_health_profile(uid, profile)`, `save_meal_plan(uid, plan)`, `get_active_meal_plan(uid)`, `log_chat_message(uid, session_id, message)`.

---

### Phase 4: API Routes (Days 5-7)

#### [NEW] `backend/app/routers/plan.py`
- `POST /api/plan/generate` — triggers Meal Plan Generator Agent
- `GET /api/plan/latest` — retrieves active meal plan from Firestore
- `PUT /api/plan/{planId}/regenerate` — regenerate with adjustments

#### [NEW] `backend/app/routers/fitness.py`
- `GET /api/fitness/summary` — recent fitness stats (steps, HR, sleep, calories)
- `GET /api/fitness/trends` — 30-day trend data for charts

#### [NEW] `backend/app/routers/voice.py`
- `POST /api/voice/token` — mints an ephemeral Gemini Live API token
- `WebSocket /api/voice/relay` — relays voice Q&A through Food Q&A Agent

#### [NEW] `backend/app/routers/health.py`
- `GET /api/health` — health check
- `GET /api/health/analyze` — trigger Health Analyzer Agent

---

### Phase 5: Frontend (Days 6-10)

#### [NEW] Next.js App with App Router
A stunning, modern single-page app with:

1. **Landing/Dashboard** (`page.tsx`):
   - Google Sign-In button (or demo mode bypass)
   - Fitness summary cards (steps, calories, sleep, heart rate) with animated counters
   - Weekly activity trend chart (line/bar chart)
   - Quick action buttons: "Generate Meal Plan", "Ask About Food"

2. **Meal Plan View** (`plan/page.tsx`):
   - 14-day grid/calendar layout
   - Each day shows breakfast/lunch/dinner/snack with dish name + macro badges
   - Daily total macros bar chart
   - "Regenerate" button per day or full plan
   - Glassmorphism cards with smooth transitions

3. **Voice Q&A** (`voice/page.tsx`):
   - Full-screen immersive voice interface
   - Animated mic button with pulsing ring when listening
   - Real-time audio waveform visualization
   - Text transcript of conversation
   - Gemini Live API WebSocket integration (client-to-server audio stream)

4. **Design System**:
   - Dark mode by default with gradient accents (emerald/teal health theme)
   - Inter font from Google Fonts
   - Glassmorphism cards, smooth micro-animations
   - Responsive — works on tablet/mobile for demo flexibility

---

### Phase 6: Deployment (Days 9-11)

#### [NEW] `backend/Dockerfile`
Multi-stage build: Python 3.11-slim, install deps, copy app, run uvicorn.

#### [NEW] `frontend/Dockerfile`
Multi-stage build: Node 20 build stage → nginx serve stage.

#### [NEW] `docker-compose.yaml`
Local development with backend + frontend + emulators.

#### [NEW] `infra/cloudbuild.yaml`
Cloud Build config to build + deploy both services to Cloud Run.

#### [NEW] `infra/k8s/` (Learning Exercise)
Kubernetes manifests for deploying the ETL job to GKE Autopilot as a CronJob.

---

### Phase 7: Analytics & Polish (Days 11-14)

- Looker Studio dashboard connected to BigQuery (manual setup, I'll provide the queries)
- README with architecture diagram, setup guide, and requirements mapping
- Demo script/narrative document

---

## Open Questions

> [!IMPORTANT]
> **1. GCP Project ID**: Do you already have a GCP project, or should I use `nextbite-demo` as the project ID? Also, do you have the $300 free trial active?

> [!IMPORTANT]
> **2. Gemini API Key**: Do you already have a Gemini API key from AI Studio, or do you need to create one? Which Gemini model do you prefer — `gemini-2.5-flash` (cheaper, faster) or `gemini-2.5-pro` (smarter)?

> [!IMPORTANT]
> **3. Datasets**: Have you already downloaded the Kaggle FitBit dataset and USDA FoodData Central, or should I provide download links and wait for you to get them?

> [!WARNING]
> **4. Tool Installation**: Since nothing is installed on this machine (no Python, Node.js, gcloud), I can automate the installations using `choco` or direct downloads, but **some steps require interactive browser sign-in** (gcloud auth, Firebase console). Should I proceed with automated tool installation first, and pause at the interactive steps?

> [!NOTE]
> **5. Start Point**: Given the blank slate, would you prefer I start by:
> - **(a)** Installing all tools first, then building code
> - **(b)** Building all the code locally first (you install tools in parallel), then we integrate
> - **(c)** Something else?

---

## Verification Plan

### Automated Tests
```bash
# Backend unit tests
cd backend && python -m pytest tests/ -v

# ETL verification
python -m app.etl.load_fitbit --dry-run  # Verify CSV parsing
python -m app.etl.load_usda --dry-run    # Verify USDA parsing

# Agent tests via ADK
adk run backend/app/agents/ --test

# Frontend build check
cd frontend && npm run build
```

### Manual Verification
- **BigQuery**: Row counts match source CSVs; spot-check `daily_metrics` and `usda_foods`
- **Agents**: Test each agent individually via `adk web` before wiring into FastAPI
- **End-to-end**: Sign in → view dashboard → generate 14-day plan → verify Firestore write → check macro totals vs TDEE
- **Voice**: Ask 3-5 food questions covering clearly-fine, borderline, and clearly-bad cases; confirm reasoning cites remaining macros/goal
- **Cloud Run**: Services deploy and respond; Firebase Auth blocks unauthenticated requests
- **Budget**: Check spend against $300 credit after each phase

### Demo Test Script
| Test Case | Expected Behavior |
|---|---|
| "I'm having a salad with grilled chicken" | Affirm positively, cite protein + low cal fit |
| "Is pizza okay for lunch?" | Contextualize (~800kcal impact), suggest lighter dinner |
| "Can I have a milkshake?" | Show calorie/sugar impact, suggest protein shake alternative |
| "I want oatmeal for breakfast" | Strong affirm — fiber, complex carbs, fits perfectly |
| "What about a triple cheeseburger?" | Show it exceeds most of daily fat/cal budget, suggest single patty swap |
