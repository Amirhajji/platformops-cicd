# PlatformOPS: rules for Claude Code

PlatformOPS is an AIOps platform for a **simulated Huawei Cloud system**. The repo contains:

1. a simulator that generates metrics, KPIs and KQIs;
2. a PostgreSQL database that stores them;
3. a FastAPI backend that turns them into insights;
4. a React frontend that displays those insights.

The simulator, the database, the backend and the frontend are being **rebuilt from scratch**. The deployment infrastructure is **frozen**. Nothing on the VMs or in Jenkins may need to change.

---

## 1. Frozen infrastructure (never change, never require a change)

| Machine | IP | Role |
|---|---|---|
| Windows host (VMware host) | 192.168.21.1 | PostgreSQL. Development, the simulator, migrations and data loading all happen here. |
| cicd VM | 192.168.21.132 | Jenkins on 8080, Nexus on 8081, monitoring (Prometheus, Grafana, Blackbox, Loki) |
| backend VM | 192.168.21.133 | FastAPI under systemd, port 8000 |
| frontend VM | 192.168.21.134 | Nginx on port 80, serves static files |

- **Do not edit the `Jenkinsfile`.** Jenkins reads it from this repo (job `platformops-ci`, branch `*/main`, manual "Build Now", no triggers).
- Do not add steps that need something new on any VM. That means no new system packages, services, env vars, ports or Nginx config.

### What Jenkins does (the contract)

**Backend: `cd backend`**
1. `python3 -m venv .venv` with **Python 3.8.10**.
2. `pip install -r requirements.txt`.
3. `python -c "import app.main"` with `CI=true`. **No database is reachable at this point.**
4. `zip -r backend-<sha>.zip app requirements.txt`. **Only `app/` and `requirements.txt` are shipped.**

**Frontend: `cd platformops-frontend`**
1. `npm ci`, with **Node 18.20.8 / npm 10.8.2**.
2. `npm run build`.
3. `test -f dist/index.html`.
4. The contents of `dist/` are zipped.

**Backend VM**
1. Unzip to `/opt/backend/releases/<sha>`.
2. `python3 -m venv venv` (3.8.10), then `pip install -r requirements.txt`.
3. Symlink to `/opt/backend/current`.
4. `systemctl restart backend`.
5. The systemd unit runs:
   ```
   WorkingDirectory=/opt/backend/current
   EnvironmentFile=/opt/backend/shared/.env
   ExecStart=/opt/backend/current/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
6. Jenkins then polls `GET http://192.168.21.133:8000/health` 30 times, 2 s apart. **It must return HTTP 200 within 60 s.**

**Frontend VM**
1. Unzip to `/var/www/frontend/releases/<sha>`.
2. Symlink to `/var/www/frontend/current`.
3. `nginx reload`.
4. Nginx config: `root /var/www/frontend/current; location / { try_files $uri /index.html; }`.
   - **SPA fallback exists**, so BrowserRouter deep links work.
   - **There is no API proxy.** The browser calls the backend directly at `http://192.168.21.133:8000`.

**Monitoring** (Docker on the cicd VM)
- Blackbox probes the backend `/health` and the frontend `/`. Keep both working.
- The other Prometheus jobs are `node_exporters`, `cadvisor` and `pushgateway`.
  - They do **not** scrape the backend app, so no `/metrics` endpoint is required.
  - The `ai-agent` container reads only node_exporter data through Prometheus, so it doesn't depend on the backend API.

**Backend VM disk:** 42 GB free. Each release takes about 130 MB because it includes its own venv.

### Backend environment on the VM (`/opt/backend/shared/.env`, do not edit)

```
APP_ENV=production
APP_NAME=backend-api
HOST=0.0.0.0
PORT=8000
DB_HOST=192.168.21.1
DB_PORT=5432
DB_NAME=platformops
DB_USER=platformops
DB_PASSWORD=platformops
LOG_LEVEL=info
```

- The backend config **must read exactly these variable names**.
- Every other setting (JWT secret, CORS origins, and so on) **must have a working default in code**, because nothing new can be added to this file.
- The database name stays `platformops`. See §5.

---

## 2. Repo layout

```
platformops-cicd/
├── Jenkinsfile              # DO NOT EDIT
├── CLAUDE.md
├── docs/                    # specs: services, metrics, KPI/KQI formulas, scenarios
├── simulator/               # runs on Windows only, never deployed
├── backend/
│   ├── requirements.txt     # deployed
│   ├── app/                 # deployed: everything the running API needs lives here
│   ├── alembic/ + alembic.ini   # NOT deployed: migrations run from Windows
│   ├── tools/               # NOT deployed: data loader, seed scripts (run from Windows)
│   └── tests/               # NOT deployed
└── platformops-frontend/
    ├── package.json
    ├── package-lock.json    # must be committed (npm ci)
    └── src/
```

Nothing under `app/` may import from `alembic/`, `tools/` or `tests/`.

---

## 3. Backend rules (Python 3.8.10)

**Python syntax**
- **Python 3.8 syntax only.** FastAPI and Pydantic evaluate type hints at runtime, so:
  - use `List`, `Dict`, `Tuple`, `Optional` and `Union` from `typing`;
  - never write `list[int]`, `dict[str, X]` or `X | None`;
  - no `match` statements;
  - no 3.9+ string methods (`removeprefix`) and no 3.9+ stdlib APIs (`zoneinfo` and similar).

**Dependencies**
- Pin **exact versions** (`==`) in `requirements.txt`.
- For each package, choose a release whose metadata still allows Python 3.8. Prefer packages that ship wheels for 3.8, because the VM has no build tools to rely on.
- Before committing, verify with a real Python 3.8 venv (see §7).
- Keep the list short: FastAPI, uvicorn, SQLAlchemy, psycopg2-binary, pydantic. Add numpy only if it's truly needed.

**Startup and `/health`**
- **Import must not touch the database.** No engine connection, no queries and no data loading at import time or at startup.
  - Create the engine lazily, or create it without connecting.
  - When `CI=true`, skip DB setup entirely.
- `GET /health` returns HTTP 200 with a JSON body such as `{"status": "ok"}`, without touching the database.
- A separate `GET /health/db` may check the database.

**Configuration**
- One config module, `app/core/config.py`.
- It reads the env var names from §1, with defaults matching the VM values.
- In development, allow an optional local `.env`; it is not shipped and not required.

**CORS** must allow:
- `http://192.168.21.134`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

**Design**
- Every insight endpoint is backed by a formula written in `docs/`.
- No duplicate implementations, and no `* copy.py` files.
- Routes with fixed paths are declared before catch-all `/{param}` routes.

**Logging and tests**
- Log to stdout. journald and Loki pick it up.
- Tests use pytest and run on Windows. They are not run by Jenkins.

---

## 4. Frontend rules (Node 18.20.8, npm 10.8.2)

- Every dev dependency must support Node 18. **Check the `engines` field.**
  - Recent major versions of Vite and some CSS tooling require Node 20+.
  - Pin to versions that run on Node 18.
  - Verify the production build under Node 18 before pushing.
- Commit `package-lock.json`, generated with npm 10.
- `npm run build` must output `dist/index.html`, so keep Vite's default `outDir`.
- API base URL: `import.meta.env.VITE_API_BASE_URL`, with the fallback `http://192.168.21.133:8000`.
  - Commit `.env.production` with `VITE_API_BASE_URL=http://192.168.21.133:8000`, because Jenkins builds with no extra env.
- The app is served at `/` (Vite `base: '/'`). BrowserRouter is fine.

---

## 5. Database (PostgreSQL on the Windows host)

- **PostgreSQL 17** (Windows service `postgresql-x64-17`, binaries in `C:\Program Files\PostgreSQL\17\bin`, not on PATH).
- The backend VM connects to `192.168.21.1:5432` as `platformops/platformops`, database **`platformops`**. Connectivity is verified.
- **Cut-over plan** (on Windows, done once by the user):
  1. `pg_dump -Fc platformops > platformops_before_rebuild.dump`
  2. `ALTER DATABASE platformops RENAME TO platformops_old;`
  3. `CREATE DATABASE platformops OWNER platformops;`
- The schema is owned by Alembic migrations in `backend/alembic/`. **Migrations must fully rebuild the schema from an empty database.** Never hand-patch the live DB.
- Data is loaded by `backend/tools/` scripts from the simulator output, run on Windows.

---

## 6. Simulator rules

- It lives in `simulator/` and runs on Windows only, so any Python version is fine there.
- **Deterministic:** a fixed seed in the config. Same config, same output, byte for byte.
- Every simulated service, metric, unit and range comes from Huawei Cloud official docs (Cloud Eye metrics). Each one is documented in `docs/` with its source link.
- KPIs and KQIs are explicit formulas over metrics, written in `docs/`, and implemented once.
- Incidents are **named scenarios** with a start tick, an end tick, a target and an effect. They are written as ground-truth labels next to the data, so detections can be validated.
- Output is validated before loading: ranges, units, no NaN, no impossible values, scenarios visible.

---

## 7. Local toolchain (Windows) and the pre-push check

The local versions match the VMs exactly, so a build that passes here will pass in Jenkins.

| Tool | Version | Used for |
|---|---|---|
| Python 3.8.10 (`py -3.8`) | same as the VMs | the backend venv. Develop and run the backend on this only. |
| Python 3.12 (`py -3.12` / `python`) | any recent version | the simulator, data loader and Alembic tooling |
| Node 18.20.8 / npm 10.8.2 | same as the Jenkins VM (portable zip in `%LOCALAPPDATA%\Programs\node-v18.20.8-win-x64`, on the user PATH) | the frontend |
| Git 2.56 | | |
| PostgreSQL 17.11 | Windows service | the database |

**Before pushing, run in PowerShell from the repo root:**

```powershell
# backend: same steps as Jenkins
cd backend
py -3.8 -m venv .venv-ci; .\.venv-ci\Scripts\python -m pip install -q -r requirements.txt
$env:CI="true"; .\.venv-ci\Scripts\python -c "import app.main; print('import OK')"; Remove-Item Env:CI
cd ..

# frontend: same steps as Jenkins
cd platformops-frontend
npm ci; npm run build; Test-Path dist\index.html
cd ..
```

Then start the backend with `.venv\Scripts\uvicorn app.main:app --port 8000` and check that `http://localhost:8000/health` returns 200. Check the main endpoints against the local database.

**Safety:**
- If Jenkins fails at build, install or import, it stops **before** Nexus and deploy, so the live site is untouched.
- The real risk is the backend crashing at runtime after a restart. The local run on 3.8.10 covers that.
- Work on the `rebuild` branch. Merge to `main` only when the check passes.
- Deployment happens only when the user clicks "Build Now".
- Old releases remain on the VMs for rollback.
