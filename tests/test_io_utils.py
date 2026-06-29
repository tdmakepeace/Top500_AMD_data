from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from top500list import io_utils


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
