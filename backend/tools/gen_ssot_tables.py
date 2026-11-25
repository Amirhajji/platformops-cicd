"""Print the generated tables of docs/PLATFORMOPS_SSOT.md, or rewrite them in the file.

Run from backend/:
    .venv\\Scripts\\python tools\\gen_ssot_tables.py                 # print every table
    .venv\\Scripts\\python tools\\gen_ssot_tables.py kpis routes     # print some of them
    .venv\\Scripts\\python tools\\gen_ssot_tables.py --write         # rewrite the document

Everything is read from the code, the configuration and the simulator output. The table
"database" also reads the database of the DB_* settings, in a read-only transaction; set
DB_NAME to choose it. It never prints a password, a secret or a row of `users`.
With --write, a table that cannot be generated keeps its old text.
"""
import argparse
import ast
import contextlib
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import yaml
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import admin_user, current_user  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.main import app  # noqa: E402
from tools.database import target_engine  # noqa: E402

REPO = BACKEND.parent
SIMULATOR = REPO / "simulator"
CONFIG = SIMULATOR / "config"
OUTPUT = SIMULATOR / "output"
FRONTEND = REPO / "platformops-frontend"
DOCUMENT = REPO / "docs" / "PLATFORMOPS_SSOT.md"

Rows = Iterable[Iterable[Any]]


def table(header: List[str], rows: Rows) -> str:
    def line(cells: Iterable[Any]) -> str:
        return "| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |"
    return "\n".join([line(header), "|" + "---|" * len(header)] + [line(r) for r in rows])


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_config() -> Dict[str, Any]:
    return read_yaml(CONFIG / "run.yaml")


def components() -> List[Dict[str, Any]]:
    return [read_yaml(CONFIG / name) for name in run_config()["components"]]


def kpi_config() -> List[Dict[str, Any]]:
    return read_yaml(CONFIG / "kpis.yaml")["kpis"]


def column_count(component: Dict[str, Any]) -> int:
    return sum(len(component["resources"][metric["level"]])
               for metric in component["metrics"])


# --- simulator -------------------------------------------------------------

def sim_components() -> str:
    kpis_of = Counter(kpi["component"] for kpi in kpi_config())
    rows, totals = [], [0, 0, 0]
    for c in components():
        numbers = [len(c["metrics"]), column_count(c), kpis_of[c["id"]]]
        totals = [a + b for a, b in zip(totals, numbers)]
        namespaces = dict.fromkeys(metric["namespace"] for metric in c["metrics"])
        resources = "; ".join(level + ": " + ", ".join(f"`{n}`" for n in names)
                              for level, names in c["resources"].items())
        rows.append([c["id"], c["name"], " + ".join(namespaces), resources] + numbers)
    rows.append(["**Total**", "", "", ""] + [f"**{n}**" for n in totals])
    return table(["C", "Name", "Namespaces", "Resources by level", "Metrics", "Columns",
                  "KPIs"], rows)


def sim_kinds() -> str:
    kinds: List[Any] = ["random", "derived", "constant", "counter", "flag"]
    periods: List[Any] = [1, 4, 5, 30]
    rows, total = [], Counter()  # type: ignore
    for c in components():
        count: Counter = Counter()
        for metric in c["metrics"]:
            count[metric["kind"]] += 1
            count[metric["period_min"]] += 1
            count["columns", metric["period_min"]] += len(c["resources"][metric["level"]])
        total.update(count)
        rows.append([c["id"]] + [count[k] for k in kinds + periods])
    unknown = {k for k in total if not isinstance(k, tuple)} - set(kinds + periods)
    if unknown:
        raise ValueError(f"unknown kinds or periods: {unknown}")
    rows.append(["**Metrics**"] + [f"**{total[k]}**" for k in kinds + periods])
    rows.append(["Columns by period", "", "", "", "", ""]
                + [total["columns", p] for p in periods])
    return table(["C"] + kinds + [f"{p} min" for p in periods], rows)


def sim_special() -> str:
    """Counters and flags, with their exact values."""
    rows = []
    for c in components():
        for metric in c["metrics"]:
            if metric["kind"] == "counter":
                if "inc_from" in metric:
                    increment = f"current value of `{metric['inc_from']}`"
                else:
                    increment = f"normal {metric['normal_inc']}, bad {metric['bad_inc']}"
                detail = f"start {metric['start']:.10g}; increment: {increment}"
            elif metric["kind"] == "flag":
                detail = (f"{metric['healthy']} (healthy); {metric['unhealthy']} on "
                          f"`{metric['bad_resource']}` in a bad period")
            else:
                continue
            rows.append([c["id"], f"`{metric['id']}`", metric["kind"], detail])
    return table(["C", "Metric", "Kind", "Values"], rows)


def sim_catalog() -> str:
    with (SIMULATOR / "catalog" / "huawei_metrics_catalog.csv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    scope = Counter(row["in_scope"] for row in rows)
    sources = dict.fromkeys((r["component"].split()[0], r["source"]) for r in rows)
    return "\n".join([
        f"The catalog has {len(rows)} rows: {scope['yes']} in scope, {scope['no']} out of "
        "scope (one row can stand for a group of metrics).", "",
        table(["C", "Out of scope", "Reason in the catalog"],
              [[r["component"].split()[0], f"`{r['metric_id']}`", r["note"]]
               for r in rows if r["in_scope"] != "yes"]), "",
        table(["C", "Official source (column `source`)"], sources)])


def kpi_formula(kpi: Dict[str, Any], resources: List[str]) -> str:
    source = kpi["input"]
    if kpi["type"] == "ratio":
        return f"100 × ({source['part']}) / ({source['total']})"
    if kpi["type"] == "value":
        return source
    inner = ", ".join(source) if isinstance(source, list) else source
    over = f" over {len(resources)} × {kpi['level']}" if len(resources) > 1 else ""
    return f"{'mean' if kpi['type'] == 'average' else 'max'}({inner}){over}"


def kpis() -> str:
    by_id = {c["id"]: c for c in components()}
    rows = []
    for k in kpi_config():
        formula = kpi_formula(k, by_id[k["component"]]["resources"][k["level"]])
        rows.append([k["component"], f"`{k['id']}`", k["name"], k["signal"], k["type"],
                     k["level"], f"`{formula}`", f"{k['good']:g}", f"{k['bad']:g}",
                     k["better"]])
    return table(["C", "KPI", "Name", "Signal", "Type", "Level", "y =", "G", "B",
                  "Better"], rows)


def kpi_types() -> str:
    config = kpi_config()
    parts = []
    for name in ("type", "signal"):
        count = Counter(k[name] for k in config).most_common()
        parts.append(f"By {name}: " + ", ".join(f"{n} {value}" for value, n in count) + ".")
    return f"{len(config)} KPIs. " + " ".join(parts)


def bands() -> str:
    return table(["Status", "Low", "High"], [
        [name, low, high] for name, (low, high)
        in read_yaml(CONFIG / "kpis.yaml")["status_bands"].items()])


def incidents() -> str:
    run = run_config()
    start = datetime.strptime(run["start_utc"], "%Y-%m-%dT%H:%M:%SZ")

    def stamp(tick: int) -> str:
        return f"{start + timedelta(seconds=tick * run['tick_seconds']):%Y-%m-%d %H:%M}"
    rows = [[c, f"{i['start_tick']}–{i['end_tick']}", stamp(i["start_tick"]),
             stamp(i["end_tick"]),
             (i["end_tick"] - i["start_tick"] + 1) * run["tick_seconds"] // 60]
            for c, items in run["incidents"].items() for i in items]
    return table(["C", "Ticks (included)", "Start UTC", "End UTC", "Minutes"], rows)


def outputs() -> str:
    manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    rows, total = [], 0
    for name, entry in manifest["files"].items():
        path = OUTPUT / name
        with path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
        size = path.stat().st_size
        total += size
        shown = ", ".join(header[:3]) + ", …" if name.startswith("x/") else ", ".join(header)
        rows.append([f"`{name}`", f"{entry['rows']:,}", len(header), shown,
                     f"{size:,}", f"`{entry['sha256'][:12]}…`"])
    rows.append([f"{len(rows)} files + `manifest.json`", "", "", "", f"**{total:,}**", ""])
    return table(["File", "Rows", "Columns", "Header", "Bytes", "SHA-256"], rows)


def checks() -> str:
    """The CHECKS list of validate.py, read without importing it (it needs Python 3.12)."""
    tree = ast.parse((SIMULATOR / "simulator" / "validate.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "CHECKS":
            pairs: Any = node.value
            return table(["#", "Check", "Function"], [
                [number, pair.elts[0].value, f"`{pair.elts[1].id}`"]
                for number, pair in enumerate(pairs.elts, start=1)])
    raise ValueError("no CHECKS list in validate.py")


# --- database --------------------------------------------------------------

def schema() -> str:
    parts = []
    for item in Base.metadata.sorted_tables:
        rows = []
        for column in item.columns:
            keys = []
            if column.primary_key:
                keys.append("PK")
            keys += [f"FK → {key.target_fullname}" for key in column.foreign_keys]
            if column.unique:
                keys.append("unique")
            if column.index:
                keys.append("index")
            default: Any = column.server_default
            shown = ("serial" if item.autoincrement_column is column else
                     "" if default is None else str(default.arg))
            rows.append([f"`{column.name}`",
                         column.type.compile(dialect=postgresql.dialect()).lower(),
                         "yes" if column.nullable else "no", ", ".join(keys), shown])
        parts += [f"**`{item.name}`**", "",
                  table(["Column", "Type", "Null", "Keys", "Default"], rows)]
        for constraint in sorted(item.constraints, key=lambda c: str(c.name)):
            if hasattr(constraint, "sqltext"):
                parts.append(f"\nCheck `{constraint.name}`: `{constraint.sqltext}`")
        parts.append("")
    return "\n".join(parts).rstrip()


COUNT_SCORES = """
    select k.scope, count(*) filter (where status = 'healthy'),
           count(*) filter (where status = 'degraded'),
           count(*) filter (where status = 'critical'), min(z), avg(z),
           avg(z) filter (where s.id is not null), avg(z) filter (where s.id is null)
    from kqi_points k left join simulated_incidents s
      on s.component_id = k.scope and k.tick between s.start_tick and s.end_tick
    group by k.scope order by k.scope"""
MATCHES = """
    select i.component_id, s.start_tick, s.end_tick, i.start_tick, i.end_tick,
           i.end_tick - s.end_tick, i.alert_count, i.min_z
    from incidents i join simulated_incidents s
      on s.component_id = i.component_id
     and i.start_tick <= s.end_tick and s.start_tick <= i.end_tick
    order by 1, 2"""


def database() -> str:
    with contextlib.redirect_stdout(sys.stderr):
        engine = target_engine()
    with engine.connect().execution_options(postgresql_readonly=True) as connection:
        def one(query: str) -> Any:
            return connection.execute(text(query)).scalar()

        def many(query: str) -> List[Any]:
            return list(connection.execute(text(query)))
        sizes = many("select relname, pg_total_relation_size(relid) "
                     "from pg_stat_user_tables order by relname")
        counts = [[f"`{name}`", f"{one('select count(*) from ' + name):,}", f"{size:,}"]
                  for name, size in sizes]
        indexes = many("select indexname, tablename, indexdef from pg_indexes "
                       "where schemaname = 'public' order by tablename, indexname")
        scores = many(COUNT_SCORES)
        matches = many(MATCHES)
        head = (f"Read from database `{one('select current_database()')}` (PostgreSQL "
                f"{one('show server_version')}), Alembic version "
                f"`{one('select version_num from alembic_version')}`, size "
                f"{one('select pg_database_size(current_database())'):,} bytes.")

    def number(value: Optional[float]) -> str:
        return "" if value is None else f"{value:.2f}"
    index_rows = []
    for name, owner, definition in indexes:
        unique = "unique " if " UNIQUE " in definition else ""
        index_rows.append([f"`{name}`", f"`{owner}`",
                           unique + definition[definition.index("("):]])
    return "\n".join([
        head, "", table(["Table", "Rows (count)", "Bytes with indexes"], counts), "",
        "Indexes:", "", table(["Index", "Table", "Columns"], index_rows), "",
        "Scores: number of ticks by status. \"In\" = inside a simulated incident.", "",
        table(["Scope", "healthy", "degraded", "critical", "min z", "mean z", "mean z in",
               "mean z out"], [list(r[:4]) + [number(v) for v in r[4:]] for r in scores]),
        "", "Detected incidents, with the simulated incident that each one overlaps:", "",
        table(["C", "Simulated ticks", "Detected ticks", "End lag (ticks)", "Alerts",
               "Min z"],
              [[c, f"{a}–{b}", f"{d}–{e}", lag, alerts, number(z)]
               for c, a, b, d, e, lag, alerts, z in matches])])


# --- backend ---------------------------------------------------------------

def _calls(dependant: Any) -> List[Any]:
    return [dependant.call] + [call for sub in dependant.dependencies for call in _calls(sub)]


def _type(spec: Dict[str, Any]) -> str:
    if "$ref" in spec:
        return spec["$ref"].rsplit("/", 1)[1]
    if "anyOf" in spec:
        return " or ".join(_type(part) for part in spec["anyOf"])
    if spec.get("type") == "array":
        return f"list of {_type(spec['items'])}"
    if "enum" in spec:
        return " / ".join(f"`{value}`" for value in spec["enum"])
    return spec.get("format") or spec.get("type") or "any"


def _limits(spec: Dict[str, Any]) -> str:
    merged = dict(spec)
    for part in spec.get("anyOf", []):
        merged.update(part)
    names = ("minLength", "maxLength", "minimum", "maximum", "pattern")
    return ", ".join(f"{n} `{merged[n]}`" for n in names if n in merged)


def _schema_name(content: Dict[str, Any]) -> str:
    return _type(content["application/json"]["schema"]) if content else ""


def routes() -> str:
    paths = app.openapi()["paths"]
    rows = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        calls = _calls(route.dependant)
        role = ("admin" if admin_user in calls else
                "any user" if current_user in calls else "no token")
        for method in sorted(route.methods):
            spec = paths[route.path][method.lower()]
            parameters = []
            for p in spec.get("parameters", []):
                details = [_type(p["schema"])] + (["required"] if p.get("required") else [])
                limits = _limits(p["schema"])
                parameters.append(f"{p['in']} `{p['name']}`: "
                                  + ", ".join(details + ([limits] if limits else [])))
            body = _schema_name(spec.get("requestBody", {}).get("content", {}))
            if body:
                parameters.append(f"body: {body}")
            status = next(code for code in spec["responses"] if code.startswith("2"))
            answer = _schema_name(spec["responses"][status].get("content", {}))
            rows.append([method, f"`{route.path}`", role, "<br>".join(parameters),
                         status, answer or "no body"])
    api = [r for r in rows if r[1].startswith("`/api/")]
    other = [getattr(r, "path", "") for r in app.routes if not isinstance(r, APIRoute)]
    return "\n".join([
        f"{len(api)} routes under `/api` and {len(rows) - len(api)} other route of the app. "
        f"FastAPI adds, without a token: {', '.join(f'`{p}`' for p in other)}.", "",
        table(["Method", "Path", "Role", "Parameters", "Success", "Response"], rows)])


def shapes() -> str:
    rows = []
    for name, spec in app.openapi()["components"]["schemas"].items():
        if "ValidationError" in name:
            continue
        fields = []
        for field, detail in spec["properties"].items():
            limits = _limits(detail)
            fields.append(f"`{field}`: {_type(detail)}" + (f" ({limits})" if limits else ""))
        rows.append([name, "<br>".join(fields)])
    return table(["Model", "Fields"], rows)


def backend_deps() -> str:
    rows = []
    for name in ("requirements.txt", "requirements-dev.txt"):
        for line in (BACKEND / name).read_text(encoding="utf-8").splitlines():
            package, separator, version = line.partition("==")
            if separator:
                rows.append([package, version, f"`backend/{name}`"])
    return table(["Package", "Pinned version", "File"], rows)


# --- frontend --------------------------------------------------------------

def frontend_deps() -> str:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    locked = json.loads((FRONTEND / "package-lock.json").read_text(encoding="utf-8"))
    rows = []
    for group in ("dependencies", "devDependencies"):
        for name, version in package[group].items():
            entry = locked["packages"]["node_modules/" + name]
            rows.append([name, version, entry["version"],
                         entry.get("engines", {}).get("node", "not declared"), group])
    return table(["Package", "package.json", "Locked", "`engines.node`", "Group"], rows)


def frontend_routes() -> str:
    source = (FRONTEND / "src" / "main.tsx").read_text(encoding="utf-8")
    found = re.findall(r'<Route (?:path="([^"]+)"|(index)) element=\{<(.+?) ?/>\} ?/>',
                       source)
    return table(["Route", "Element"],
                 [[f"`{path or index}`", f"`{element}`"] for path, index, element in found])


def frontend_calls() -> str:
    client = (FRONTEND / "src" / "api.ts").read_text(encoding="utf-8")
    body = client[client.index("export const api = {"):]
    endpoints: Dict[str, str] = {}
    for block in re.split(r"\n  (?=\w+: \()", body)[1:]:
        name = block.split(":", 1)[0]
        url = re.search(r"['`](/api/[^'`]*)['`]", block)
        method = re.search(r"\('(GET|POST|DELETE)'", block)
        if url is None:
            raise ValueError(f"api.ts: no URL for {name}")
        clean = re.sub(r"\$\{(?:encodeURIComponent\()?(\w+)\)?\}", r"{\1}", url.group(1))
        endpoints[name] = f"{method.group(1) if method else 'GET'} {clean}"
    rows = []
    for path in sorted((FRONTEND / "src").rglob("*.ts*")):
        used = dict.fromkeys(re.findall(r"\bapi\.(\w+)\(", path.read_text(encoding="utf-8")))
        if used:
            rows.append([f"`{path.relative_to(FRONTEND).as_posix()}`",
                         "<br>".join(f"`{endpoints[name]}`" for name in used)])
    return table(["File", "Endpoints called"], rows)


# --- repository ------------------------------------------------------------

def files() -> str:
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files"], check=True,
                            stdout=subprocess.PIPE).stdout.decode().splitlines()
    rows = []
    for group in ("simulator/simulator", "simulator/tests", "simulator/config",
                  "backend/app", "backend/alembic", "backend/tools", "backend/tests",
                  "platformops-frontend/src"):
        own = [name for name in listed if name.startswith(group + "/")]
        lines = sum((REPO / name).read_bytes().count(b"\n") for name in own)
        rows.append([f"`{group}/`", len(own), f"{lines:,}"])
    return table(["Folder", "Tracked files", "Lines"], rows)


def tests() -> str:
    rows = []
    for name, python in (("backend", sys.executable),
                         ("simulator", str(SIMULATOR / ".venv/Scripts/python.exe"))):
        out = subprocess.run([python, "-m", "pytest", "--collect-only", "-q"],
                             cwd=str(REPO / name), check=True,
                             stdout=subprocess.PIPE).stdout.decode(errors="replace")
        count = Counter(line.split("::")[0] for line in out.splitlines() if "::" in line)
        rows += [[f"`{name}/{path}`", number] for path, number in sorted(count.items())]
        rows.append([f"**{name} total**", f"**{sum(count.values())}**"])
    return table(["File", "Tests collected"], rows)


def stages() -> str:
    source = (REPO / "Jenkinsfile").read_text(encoding="utf-8")
    return table(["#", "Stage"], enumerate(re.findall(r"stage\('([^']+)'\)", source), 1))


SECTIONS: Dict[str, Callable[[], str]] = {
    "sim-components": sim_components, "sim-kinds": sim_kinds, "sim-special": sim_special,
    "sim-catalog": sim_catalog, "kpis": kpis, "kpi-types": kpi_types, "bands": bands,
    "incidents": incidents, "outputs": outputs, "checks": checks, "schema": schema,
    "database": database, "routes": routes, "shapes": shapes, "backend-deps": backend_deps,
    "frontend-deps": frontend_deps, "frontend-routes": frontend_routes,
    "frontend-calls": frontend_calls, "files": files, "tests": tests, "stages": stages,
}


def generate(name: str) -> Optional[str]:
    try:
        return SECTIONS[name]()
    except (Exception, SystemExit) as error:  # for example, no database today
        print(f"{name}: not generated: {type(error).__name__}", file=sys.stderr)
        return None


def rewrite(names: List[str]) -> int:
    content = DOCUMENT.read_text(encoding="utf-8")
    failed = 0
    for name in names:
        begin, end = f"<!-- BEGIN GENERATED: {name} -->", f"<!-- END GENERATED: {name} -->"
        if begin not in content or end not in content:
            print(f"{name}: no markers in {DOCUMENT.name}", file=sys.stderr)
            failed += 1
            continue
        body = generate(name)
        if body is None:
            failed += 1
            continue
        head, rest = content.split(begin, 1)
        content = f"{head}{begin}\n\n{body}\n\n{end}{rest.split(end, 1)[1]}"
    with DOCUMENT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print(f"{len(names) - failed} of {len(names)} tables written to {DOCUMENT.name}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("sections", nargs="*", metavar="section",
                        help=f"default: all ({', '.join(SECTIONS)})")
    parser.add_argument("--write", action="store_true", help="rewrite the document")
    arguments = parser.parse_args()
    unknown = set(arguments.sections) - set(SECTIONS)
    if unknown:
        parser.error(f"unknown section: {', '.join(sorted(unknown))}")
    names = arguments.sections or list(SECTIONS)
    if arguments.write:
        return rewrite(names)
    failed = 0
    for name in names:
        body = generate(name)
        failed += body is None
        sys.stdout.buffer.write(f"## {name}\n\n{body or 'not generated'}\n\n".encode())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
