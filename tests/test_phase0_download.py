from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from top500list import phase0_download


def test_iterListEditions_returns_june_and_november_within_year_window() -> None:
    editions = phase0_download.iterListEditions(4, today=date(2026, 6, 25))

    assert editions == [
        (2023, 6),
        (2023, 11),
        (2024, 6),
        (2024, 11),
        (2025, 6),
        (2025, 11),
        (2026, 6),
    ]


def test_iterListEditions_includes_november_in_december() -> None:
    editions = phase0_download.iterListEditions(2, today=date(2025, 12, 1))

    assert editions == [(2024, 6), (2024, 11), (2025, 6), (2025, 11)]


def test_buildDefaultExcelUrl_uses_top500_pattern() -> None:
    url = phase0_download.buildDefaultExcelUrl("TOP500", 2026, 6)

    assert url == "https://www.top500.org/lists/top500/2026/06/download/TOP500_202606.xlsx"


def test_buildDefaultExcelUrl_uses_green500_files_pattern() -> None:
    url = phase0_download.buildDefaultExcelUrl("GREEN500", 2026, 6)

    assert url == "https://www.top500.org/files/green500/green500_top_202606.xlsx"


def test_buildLocalFileName_uses_green500_files_pattern() -> None:
    file_name = phase0_download.buildLocalFileName("GREEN500", 2026, 6)

    assert file_name == "green500_top_202606.xlsx"


@patch("top500list.phase0_download._fetchText")
def test_resolveExcelDownloadUrl_green500_uses_files_url(mock_fetch_text: MagicMock) -> None:
    mock_fetch_text.return_value = "<html><body>No downloads here</body></html>"

    url = phase0_download.resolveExcelDownloadUrl("GREEN500", 2026, 6)

    assert url == "https://www.top500.org/files/green500/green500_top_202606.xlsx"


@patch("top500list.phase0_download._fetchText")
def test_resolveExcelDownloadUrl_green500_prefers_page_link(mock_fetch_text: MagicMock) -> None:
    mock_fetch_text.return_value = '<a href="/files/green500/green500_top_202606.xlsx">Green500 Excel</a>'

    url = phase0_download.resolveExcelDownloadUrl("GREEN500", 2026, 6)

    assert url == "https://www.top500.org/files/green500/green500_top_202606.xlsx"


@patch("top500list.phase0_download._fetchText")
def test_resolveExcelDownloadUrl_prefers_page_link(mock_fetch_text: MagicMock) -> None:
    mock_fetch_text.return_value = '<a href="/lists/top500/2026/06/download/TOP500_202606.xlsx">TOP500 List (Excel)</a>'

    url = phase0_download.resolveExcelDownloadUrl("TOP500", 2026, 6)

    assert url == "https://www.top500.org/lists/top500/2026/06/download/TOP500_202606.xlsx"


@patch("top500list.phase0_download._fetchText")
def test_resolveExcelDownloadUrl_falls_back_to_default_name(mock_fetch_text: MagicMock) -> None:
    mock_fetch_text.return_value = "<html><body>No downloads here</body></html>"

    url = phase0_download.resolveExcelDownloadUrl("TOP500", 2026, 6)

    assert url.endswith("/download/TOP500_202606.xlsx")


@patch("top500list.phase0_download.resolveExcelDownloadUrl")
@patch("urllib.request.urlopen")
def test_downloadExcelFile_writes_file(
    mock_urlopen: MagicMock,
    mock_resolve_url: MagicMock,
    tmp_path: Path,
) -> None:
    mock_resolve_url.return_value = "https://www.top500.org/lists/top500/2026/06/download/TOP500_202606.xlsx"
    response = MagicMock()
    response.read.return_value = b"excel-bytes"
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    mock_urlopen.return_value = response

    output_path = phase0_download.downloadExcelFile("TOP500", 2026, 6, tmp_path, force=True)

    assert output_path is not None
    assert output_path.name == "TOP500_202606.xlsx"
    assert output_path.read_bytes() == b"excel-bytes"


@patch("top500list.phase0_download.downloadExcelFile")
def test_downloadListFiles_iterates_editions(mock_download: MagicMock, tmp_path: Path) -> None:
    mock_download.side_effect = lambda list_type, year, month, raw_dir, force=False: (
        raw_dir / phase0_download.buildLocalFileName(list_type, year, month)
    )

    paths = phase0_download.downloadListFiles("TOP500", 2, raw_dir=tmp_path, today=date(2026, 6, 25))

    assert len(paths) == 3
    assert mock_download.call_count == 3


def test_normalizeListType_accepts_case_insensitive_aliases() -> None:
    assert phase0_download.normalizeListType("GREEN500") == "Green500"
    assert phase0_download.normalizeListType("top500") == "TOP500"


def test_cleanDirectoryContents_removes_files_but_keeps_gitkeep(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / ".gitkeep").write_text("", encoding="utf-8")
    (raw_dir / "TOP500_202606.xlsx").write_bytes(b"old")
    (raw_dir / "stale.csv").write_text("a", encoding="utf-8")

    removed, failed = phase0_download.cleanDirectoryContents(raw_dir)

    assert removed == 2
    assert failed == []
    assert (raw_dir / ".gitkeep").exists()
    assert not (raw_dir / "TOP500_202606.xlsx").exists()


def test_cleanPipelineDataDirs_clears_raw_and_working_trees(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    working_csv_dir = tmp_path / "working" / "csv"
    working_amd_per_file_dir = tmp_path / "working" / "amd_per_file"
    working_amd_by_year_dir = tmp_path / "working" / "amd_by_year"
    for directory in (raw_dir, working_csv_dir, working_amd_per_file_dir, working_amd_by_year_dir):
        directory.mkdir(parents=True)
        (directory / "artifact.txt").write_text("x", encoding="utf-8")

    removed = phase0_download.cleanPipelineDataDirs(
        raw_dir=raw_dir,
        working_csv_dir=working_csv_dir,
        working_amd_per_file_dir=working_amd_per_file_dir,
        working_amd_by_year_dir=working_amd_by_year_dir,
    )

    assert removed == 4
    assert list(raw_dir.iterdir()) == []
    assert list(working_csv_dir.iterdir()) == []


@patch(
    "top500list.phase0_download._deletePath",
    side_effect=phase0_download.ListDownloadError("locked"),
)
def test_cleanPipelineDataDirs_raises_when_file_is_locked(
    mock_delete: MagicMock,
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    locked_file = raw_dir / "TOP500_202606.xlsx"
    locked_file.write_bytes(b"locked")

    with pytest.raises(phase0_download.ListDownloadError, match="Cleanup incomplete"):
        phase0_download.cleanPipelineDataDirs(
            raw_dir=raw_dir,
            working_csv_dir=tmp_path / "working" / "csv",
            working_amd_per_file_dir=tmp_path / "working" / "amd_per_file",
            working_amd_by_year_dir=tmp_path / "working" / "amd_by_year",
        )


@patch("top500list.phase0_download.downloadListFiles")
@patch("top500list.phase0_download.cleanPipelineDataDirs")
def test_runPhase0_cleans_before_download(
    mock_clean: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_download.return_value = []

    phase0_download.runPhase0("TOP500", years=4, clean=True)

    mock_clean.assert_called_once()
    mock_download.assert_called_once()


@patch("top500list.phase0_download.downloadListFiles")
@patch("top500list.phase0_download.cleanPipelineDataDirs")
def test_runPhase0_can_skip_clean(
    mock_clean: MagicMock,
    mock_download: MagicMock,
) -> None:
    mock_download.return_value = []

    phase0_download.runPhase0("TOP500", years=4, clean=False)

    mock_clean.assert_not_called()
    mock_download.assert_called_once()


def test_iterListEditions_rejects_invalid_year_count() -> None:
    with pytest.raises(ValueError, match="years must be at least 1"):
        phase0_download.iterListEditions(0)
