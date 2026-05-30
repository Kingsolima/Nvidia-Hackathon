# UrbanForge — Session Context
> Resume from any device. Read this before asking Claude anything.

---

## What this project is

**UrbanForge** — NVIDIA Hackathon 2026 (Toronto track). 6-person team, 36-hour build.

AI-powered urban development intelligence platform: place a proposed building anywhere on a 3D Toronto map, get instant NeMoTron-powered impact analysis (environmental, traffic, economic, infrastructure, housing).

Full blueprint is in `project-blueprint.html` — open it in a browser for the complete spec.

---

## Hardware

- **DGX Spark** is set up and running
- Monitor is connected and up
- Qwen3 is already running (see `~/run_quen3.6.sh` on the Spark)
- Folder structure on Spark: `llama.cpp/`, `unsloth/`, `snap/`, `venv/`, `npm/`, `openclaw/`, `openclaw backup/`, `ssh/`, `run_gemma4.sh`, `run_openclaw.sh`, `run_quen3.6.sh`
- No Docker needed (not a priority for this hackathon)
- OpenClaw / NemoClaw is available — points OpenClaw at local NIM endpoint for team coding assistance

---

## Team roles (from blueprint)

| # | Role | Person | Status |
|---|------|---------|--------|
| 1 | Data Engineer | Omar | Branch: `omar/data` — pipeline done, not merged yet |
| 2 | 3D Rendering / Maps | Rehan (you) | In progress — see below |
| 3 | AI / ML Engineer | TBD | Not started |
| 4 | Backend Engineer | TBD | Skeleton done, has blockers — see `BACKEND_ISSUES.txt` |
| 5 | Frontend / UX | TBD | Not started |
| 6 | Integration Lead | TBD | Not started |

---

## Current codebase state

### Backend (`backend/`) — DONE (skeleton), HAS BLOCKERS
Full FastAPI skeleton was pushed in the last commit. Read `BACKEND_ISSUES.txt` for the
exact list of what's broken. Short version:
- Port conflict: NeMoTron URL defaults to same port as FastAPI
- No `.env` file (only `.env.example`)
- Spatial tables don't exist in Postgres yet (waiting on omar/data merge)
- Impact endpoint is blocking (no streaming/async job pattern)
- Missing: DELETE /building/{id}, startup script

**To wire the model server:** The backend agents use an OpenAI-compatible endpoint.
If Qwen is already serving on a port via llama.cpp, just point `NEMORON_URL` at that
and change the model name string in `backend/agents/impact_agent.py` and
`backend/agents/chat_agent.py`. No new installs needed.

NVIDIA Build cloud fallback: https://build.nvidia.com/models
- Set `NEMORON_URL=https://integrate.api.nvidia.com/v1`
- Add `NGC_API_KEY` to `.env`
- Add `headers={"Authorization": f"Bearer {os.getenv('NGC_API_KEY')}"}` to the httpx calls

### Data (`omar/data` branch) — DONE, NOT MERGED
Complete Toronto Open Data download pipeline:
- `ml/data_pipeline.py` — downloads all datasets to `data/*.parquet`
- `ml/fetch.py` — CKAN API helpers
- `data/data.md` — full dataset guide with bucket breakdown
- `data/coefficients/` — ITE trip rates, StatsCan I-O multipliers CSVs

**Action needed:** Merge `omar/data` into `main`, then write a `load_spatial.py`
that reads the parquets into PostGIS tables.

### Rendering (Role 2 — Rehan's work) — IN PROGRESS
- `src/components/BuildingPreview.jsx` — Three.js React component
  - Isolated 3D building render on dark background (no map)
  - Responds to: floors, footprintM2, type (5 types), material (4 materials)
  - Procedural window texture (lit/unlit grid, night-city look)
  - Podium for Mixed-Use / Retail types
  - `spin` prop for rotation animation
  - `captureImage()` method returns PNG data URL (for AI context or thumbnails)
  - `onReady` callback fires after first frame
- `building-preview-demo.html` — standalone demo (no bundler), open in browser to test

**Next rendering tasks (from blueprint Hr 4–10):**
- Mapbox GL JS + react-map-gl setup with Toronto bounds + dark style
- 3D building extrusion via `fill-extrusion` layer on the real map
- Click-to-place interaction on the map

### Frontend — NOT STARTED
React + Vite project not initialized yet.

---

## Key decisions made

- **Model server:** Use whatever is already running on the Spark (Qwen via llama.cpp).
  The backend is model-agnostic — just update `NEMORON_URL` and the model name string.
- **No Docker** for the hackathon.
- **Claude Code on DGX Spark:** `npm install -g @anthropic-ai/claude-code` — npm is
  already there. Backend engineer can run Claude directly on the server.
- **Tailscale** was installed on Rehan's Mac for networking.

---

## Repo structure

```
Nvidia-Hackathon/
├── backend/                  # FastAPI server (Role 4)
│   ├── agents/
│   │   ├── impact_agent.py   # NeMoTron impact analysis
│   │   └── chat_agent.py     # Citizen chatbot
│   ├── routers/
│   │   ├── buildings.py      # POST/GET /building(s), GET /impact
│   │   └── chat.py           # WebSocket /chat/{session_id}
│   ├── main.py
│   ├── models.py             # SQLAlchemy ORM (Building, Impact, ChatSession)
│   ├── schemas.py            # Pydantic in/out schemas
│   ├── spatial.py            # PostGIS radius queries
│   ├── database.py           # DB connection + session
│   ├── requirements.txt
│   └── .env.example
├── src/
│   └── components/
│       └── BuildingPreview.jsx   # 3D isolated building renderer (Role 2)
├── building-preview-demo.html    # Standalone test for BuildingPreview
├── BACKEND_ISSUES.txt            # Blockers for the backend engineer
├── CONTEXT.md                    # This file
└── project-blueprint.html        # Full project spec — read this
```

---

## Immediate next steps by role

**Rehan (Rendering):**
1. Init React + Vite project: `npm create vite@latest frontend -- --template react`
2. Install deps: `npm install mapbox-gl react-map-gl three`
3. Set up Mapbox map component with Toronto bounds + dark style
4. Wire `BuildingPreview` into the Builder sidebar
5. Add `fill-extrusion` layer for placing the building on the real map

**Backend engineer:**
1. Read `BACKEND_ISSUES.txt`
2. `cp backend/.env.example backend/.env` and fill in values
3. Fix port conflict (NEMORON_URL → 8001)
4. Run `cat ~/run_quen3.6.sh` on the Spark — use that endpoint
5. Add `DELETE /building/{id}` and startup script

**Data (Omar):**
1. Merge `omar/data` into `main`
2. Write `load_spatial.py` to push parquets → PostGIS tables

**AI/ML:**
1. Confirm model server endpoint + model name
2. Test impact agent prompt with real spatial data
3. Tune prompts for consistent JSON output
