# Deploy runbook: V1 cut-over

Run in PowerShell on the Windows host, from the repo root, in **one window** (it keeps the
variables). Nothing changes on the VMs. The old site is broken between steps 2 and 3.

```powershell
$pg = "C:\Program Files\PostgreSQL\17\bin"; $sql = "-U","postgres","-h","localhost","-d","postgres","-v","ON_ERROR_STOP=1"
```
## 1. Pre-checks
```powershell
git switch rebuild; git pull --ff-only; git status --short                  # must print no file
$bk = "$env:USERPROFILE\platformops_backups"; New-Item -ItemType Directory -Force $bk | Out-Null
$dump = "$bk\platformops_$(Get-Date -Format yyyyMMdd_HHmm).dump"            # never in the repo: it is public
& "$pg\pg_dump.exe" -U postgres -h localhost -Fc -f $dump platformops; $LASTEXITCODE    # 0
& "$pg\pg_restore.exe" --list $dump | Measure-Object -Line                  # not empty
Push-Location simulator; .venv\Scripts\python -m simulator validate; .venv\Scripts\python -m pytest -q; Pop-Location
Push-Location backend; .venv\Scripts\python -m pytest -q; Pop-Location      # all passed, 0 skipped
git fetch; git log --oneline origin/main..origin/rebuild                    # what main receives
git rev-parse --short origin/main origin/rebuild                            # OLD and NEW: write both down
git diff --stat origin/main origin/rebuild -- Jenkinsfile                   # must be empty
```
Run also the Jenkins steps of `CLAUDE.md` section 7. Stop if anything fails.

## 2. Database swap (as postgres)
`ALLOW_CONNECTIONS false` stops the running backend from reconnecting during the rename.
```powershell
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops ALLOW_CONNECTIONS false" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='platformops'" -c "ALTER DATABASE platformops RENAME TO platformops_old"
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops_dev ALLOW_CONNECTIONS false" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='platformops_dev'" -c "ALTER DATABASE platformops_dev RENAME TO platformops"
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops ALLOW_CONNECTIONS true" -c "ALTER DATABASE platformops_old ALLOW_CONNECTIONS true"
& "$pg\psql.exe" @sql -c "SELECT datname, pg_get_userbyid(datdba), datallowconn FROM pg_database WHERE datname LIKE 'platformops%'"
& "$pg\psql.exe" -U postgres -h localhost -d platformops -c "SELECT version_num FROM alembic_version" -c "SELECT username, role FROM users" -c "SELECT count(*) FROM auth_secret"
Push-Location backend; .venv\Scripts\python -m alembic heads; Pop-Location
```
Expected: owner `platformops` and `t` for both; `version_num` = the head (`0002`); your admin
and no test account; 1 secret. Accounts and data moved with the rename: no load is needed.

## 3. Merge and build
```powershell
git switch main; git pull --ff-only
git merge --no-ff rebuild -m "Merge rebuild: PlatformOPS V1"
git push origin main; git rev-parse --short HEAD; git switch rebuild        # MERGE = release name: write it down
```
Then Jenkins (http://192.168.21.132:8080), job `platformops-ci`, **Build Now**. It must end green.

## 4. Verification
- `curl.exe -i http://192.168.21.133:8000/health` gives 200 and `{"status":"ok"}`.
- Open http://192.168.21.134 (Ctrl+F5) and log in with the admin account.
- Overview: global Z, 8 components, 99 alerts and 24 incidents on the whole run.
- Custom range 2026-11-01 04:30 to 05:10 UTC: **C1 is critical** (z about 5.8), others healthy.
- A refresh on a component page stays on that page; the browser console has no error.

## 5. Rollback
```powershell
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops ALLOW_CONNECTIONS false" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='platformops'" -c "ALTER DATABASE platformops RENAME TO platformops_v1"
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops_old ALLOW_CONNECTIONS false" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='platformops_old'" -c "ALTER DATABASE platformops_old RENAME TO platformops"
& "$pg\psql.exe" @sql -c "ALTER DATABASE platformops ALLOW_CONNECTIONS true" -c "ALTER DATABASE platformops_v1 ALLOW_CONNECTIONS true"
git switch main; git pull --ff-only; git revert -m 1 --no-edit MERGE; git push origin main; git switch rebuild
```
Then **Build Now**. `platformops_v1` is the V1 data (rename it to `platformops_dev` if that name is
free). If the old code no longer builds, point the VMs at the old releases (OLD = step 1):
```
ssh devops@192.168.21.133 "sudo ln -sfn /opt/backend/releases/OLD /opt/backend/current && sudo systemctl restart backend"
ssh devops@192.168.21.134 "sudo ln -sfn /var/www/frontend/releases/OLD /var/www/frontend/current && sudo systemctl reload nginx"
```
To deploy V1 again later, first `git revert` the revert commit on main, then merge rebuild.

## 6. After the deploy: local development
`backend/.env.local` must never name `platformops`. Keep `DB_NAME=platformops_dev` (the tests
require that name): after the swap it does not exist, so the tools fail safely until you create it.
```powershell
Select-String '^DB_NAME=' backend\.env.local; "env: $env:DB_NAME"           # platformops_dev, and env empty
& "$pg\psql.exe" @sql -c "CREATE DATABASE platformops_dev OWNER platformops"
Push-Location backend; .venv\Scripts\python -m alembic upgrade head; .venv\Scripts\python tools\load_simulation.py
.venv\Scripts\python tools\create_user.py --username admin --role admin; Pop-Location
```
To change the deployed database on purpose: `$env:DB_NAME="platformops"`, run the tool, check the
"Database:" line it prints, then `Remove-Item Env:DB_NAME`. Drop `platformops_old` only after a long check.
