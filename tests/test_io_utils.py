from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from top500list import io_utils


def test_buildOutputTempPath() -> None:
    output_path = Path("output/amd_servers_report.pdf")
    assert io_utils.buildOutputTempPath(output_path) == Path("output/amd_servers_report_build.pdf")


def test_publishOutputFile_replaces_target(tmp_path: Path) -> None:
    output_path = tmp_path / "amd_servers_report.pdf"
    temp_path = tmp_path / "amd_servers_report_build.pdf"
    temp_path.write_text("fresh pdf", encoding="utf-8")
    output_path.write_text("stale pdf", encoding="utf-8")

    result = io_utils.publishOutputFile(temp_path, output_path)

    assert result == output_path
    assert output_path.read_text(encoding="utf-8") == "fresh pdf"
    assert not temp_path.exists()


def test_publishOutputFile_keeps_build_file_when_target_locked(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "amd_servers_report.pdf"
    temp_path = tmp_path / "amd_servers_report_build.pdf"
    temp_path.write_text("fresh pdf", encoding="utf-8")
    output_path.write_text("locked pdf", encoding="utf-8")

    def raise_permission_error(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "replace", raise_permission_error)

    with pytest.raises(PermissionError, match="amd_servers_report_build.pdf"):
        io_utils.publishOutputFile(temp_path, output_path)

    assert temp_path.read_text(encoding="utf-8") == "fresh pdf"


def test_readTabularFile_uses_xlrd_for_xls(monkeypatch) -> None:
    path = Path("TOP500_201806.xls")
    expected = pd.DataFrame({"Rank": [1]})
    read_excel = MagicMock(return_value=expected)
    monkeypatch.setattr(io_utils.pd, "read_excel", read_excel)

    result = io_utils.readTabularFile(path)

    read_excel.assert_called_once_with(path, engine="xlrd")
    assert len(result) == 1


def test_readTabularFile_uses_openpyxl_for_xlsx(monkeypatch) -> None:
    path = Path("TOP500_202406.xlsx")
    expected = pd.DataFrame({"Rank": [1]})
    read_excel = MagicMock(return_value=expected)
    monkeypatch.setattr(io_utils.pd, "read_excel", read_excel)

    result = io_utils.readTabularFile(path)

    read_excel.assert_called_once_with(path, engine="openpyxl")
    assert len(result) == 1
