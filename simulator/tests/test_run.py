"""Full runs, always into temp folders (never into simulator/output/)."""
import hashlib
import shutil

import pytest

from simulator.__main__ import main


def hashes(folder):
    return {path.relative_to(folder).as_posix():
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


@pytest.fixture(scope="module")
def output(tmp_path_factory):
    folder = tmp_path_factory.mktemp("first")
    assert main(["run", "--output", str(folder)]) == 0
    return folder


def test_two_runs_are_identical(output, tmp_path):
    assert main(["run", "--output", str(tmp_path)]) == 0
    first = hashes(output)
    assert len(first) == 12  # 8 x files, y, z, labels, manifest
    assert hashes(tmp_path) == first


def test_full_run_passes_validate(output, capsys):
    assert main(["validate", "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    assert "FAIL" not in printed
    assert "19/19 checks passed" in printed


def test_validate_fails_on_wrong_output(output, tmp_path, capsys):
    folder = tmp_path / "broken"
    shutil.copytree(output, folder)
    replace_cell(folder / "x" / "C1_dws.csv", "cluster.dws001_shared_buffer_hit_ratio",
                 tick=10, value="101.00")
    replace_cell(folder / "x" / "C3_ecs_loader.csv", "loader.net_tcp_total",
                 tick=20, value="1")
    replace_cell(folder / "x" / "C4_ecs_bastion.csv", "bastion.cpu_util",
                 tick=1, value="3.123")
    replace_cell(folder / "y_kpis.csv", "health", tick=0, value="12.00")
    replace_cell(folder / "z_kqis.csv", "status", tick=5, value="critical")
    replace_cell(folder / "labels.csv", "end_tick", tick=0, value="330")

    assert main(["validate", "--output", str(folder)]) == 1
    failed = [line for line in capsys.readouterr().out.splitlines()
              if line.startswith("FAIL")]
    for check in ("official_range", "catalog value_range", "decimals", "only on their period",
                  "derived columns", "KPI values and health", "recomputed from y",
                  "status matches", "labels match", "manifest"):
        assert any(check in line for line in failed), check


def test_validate_fails_on_missing_output(tmp_path):
    assert main(["validate", "--output", str(tmp_path)]) == 1


def replace_cell(path, column, tick, value):
    lines = path.read_text(encoding="utf-8").split("\n")
    index = lines[0].split(",").index(column)
    cells = lines[tick + 1].split(",")
    cells[index] = value
    lines[tick + 1] = ",".join(cells)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
